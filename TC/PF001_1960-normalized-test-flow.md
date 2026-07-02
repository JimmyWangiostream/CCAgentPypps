---
title: PF001_1960_D_BKOPS_Refresh_Test-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf001_1960, scsi-cmd, refresh, bkops]
description: >
  驗證 UFS 3.0+ Refresh 操作在各種 LUN 配置、Auto Standby 模式
  及 Background Operations 啟用/停用組合下的行為。透過觸發 Refresh
  後監控 dRefreshTotalCount 變化來確認 Refresh 確實執行。
sources:
  - JIRA: PF001_1960 (SYSTCUFS-2268)
  - UFS Spec: JESD220H Section 14.1 (Descriptors), Section 14.2 (Flags), Section 14.3 (Attributes)
---

# PF001_1960 — D BKOPS Refresh Test

## 測試架構（Tree Diagram）

```
PF001_1960 Test Flow
│
├── Phase 0: Pre-condition Checks
│   ├── Step 0.1: Gate — UFS Spec Version >= 3.0
│   ├── Step 0.2: READ DESCRIPTOR (Device) — 檢查 bUFSFeaturesSupport Refresh bit
│   ├── Step 0.3: READ ATTRIBUTE (bRefreshStatus) — Refresh 前置條件確認
│   └── Step 0.4: Gate — Disable MIX mode (IC=8329/8363)
│
└── Loop (LUN Config Case 1~3)
    ├── Phase 1: LUN Configuration
    │   └── Step 1.1: WRITE DESCRIPTOR (Configuration) — 配置 LUN → Expected: QUERY RESPONSE Success
    │
    └── Loop (Auto Standby Case 1~3)
        ├── Phase 2: Auto Standby Configuration
        │   └── Step 2.1: HW Config — 設定 Auto Standby
        │
        └── Loop (fBackgroundOpsEn: Enable / Disable)
            ├── Phase 3: Refresh Setup
            │   ├── Step 3.1: SET FLAG / CLEAR FLAG (fBackgroundOpsEn) — 啟用/停用 BKOPS → Expected: QUERY RESPONSE Success
            │   ├── Step 3.2: WRITE ATTRIBUTE (bRefreshUnit) — 設為 WHOLE_DEVICE → Expected: QUERY RESPONSE Success
            │   ├── Step 3.3: WRITE ATTRIBUTE (bRefreshMethod) — Rand(Manual-Force / Manual-Selective) → Expected: QUERY RESPONSE Success
            │   ├── Step 3.4: UNMAP — 清除所有 LUN 資料 → Expected: GOOD Status
            │   ├── Step 3.5: SET FLAG (fPurgeEnable) — 觸發 Purge → Expected: QUERY RESPONSE Success
            │   └── Step 3.6: READ ATTRIBUTE (bBackgroundOpStatus) — 確認 Purge 完成
            │
            ├── Phase 4: Pre-Refresh Random Write
            │   ├── Step 4.1: WRITE(10) — 隨機寫入測試資料 → Expected: GOOD Status
            │   └── Step 4.2: READ DESCRIPTOR (Device Health) — 讀取 dRefreshTotalCount (pre) → Expected: QUERY RESPONSE Success
            │
            ├── Phase 5: Refresh Execution
            │   ├── Step 5.1: SET FLAG (fRefreshEnable) — 觸發 Refresh → Expected: QUERY RESPONSE Success
            │   └── Step 5.2: READ ATTRIBUTE (bRefreshStatus) — Poll 直到完成 → Expected: bRefreshStatus == 0x03 (Completed) or 0x00 (Idle)
            │
            └── Phase 6: Post-Refresh Verification
                ├── Step 6.1: READ DESCRIPTOR (Device Health) — 讀取 dRefreshTotalCount (post) → Expected: QUERY RESPONSE Success
                ├── Step 6.2: Compare — 驗證 dRefreshTotalCount 增加 → Expected: dRefreshTotalCount > original value
                └── Step 6.3: CLEAR FLAG (fRefreshEnable) — 清除 Refresh Enable → Expected: QUERY RESPONSE Success
```

---

## Phase 0 — Pre-condition Checks

### Step 0.1: Gate — UFS Spec Version Check

**目的**: 確認 UFS 規格版本 >= 3.0，因為 Refresh 操作為 UFS 3.0+ 功能。

**Check**: 透過 READ DESCRIPTOR (Device Descriptor, IDN=0x00) 讀取 wSpecVersion（byte offset 16~17），確認其值 >= 0x0300。

**若不支援**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

**UFS SPEC Reference**: JESD220H Section 14.1.4.3 (Device Descriptor, wSpecVersion)

---

### Step 0.2: READ DESCRIPTOR (Device) — 檢查 bUFSFeaturesSupport Refresh

**UFS QUERY**: `READ DESCRIPTOR (0x07)` — Device Descriptor (IDN=0x00)

**目的**: 確認裝置的 bUFSFeaturesSupport 欄位中 Refresh Operation bit 已設置，代表裝置支援 Refresh 操作。

| Field | Value |
|-------|-------|
| Query Opcode | 0x07 (READ DESCRIPTOR) |
| Descriptor IDN | 0x00 (Device Descriptor) |
| Index | 0x00 |
| Selector | 0x00 |
| Length | Descriptor length (bLength) |
| Check Field | bUFSFeaturesSupport (byte offset 31) |
| Check Bit | Bit 5 (Refresh Operation Support, mask 0x20) |

**若不支援**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

**UFS SPEC Reference**: JESD220H Section 14.1.4.3 (Device Descriptor, bUFSFeaturesSupport)

---

### Step 0.3: READ ATTRIBUTE (bRefreshStatus) — Refresh 前置條件確認

**UFS QUERY**: `READ ATTRIBUTE (0x03)` — bRefreshStatus (IDN=0x2C)

**目的**: 確保進入 Pattern 前無上一次未完成的 Refresh 操作。若 bRefreshStatus 非 Idle (0x00)，先 CLEAR FLAG(fRefreshEnable) 並等待其回到 Idle。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| Attribute IDN | 0x2C (bRefreshStatus) |
| Index | 0x00 |
| Selector | 0x00 |

**Branch Logic**:
- 若 bRefreshStatus == 0x01 (InProgress): CLEAR FLAG(fRefreshEnable, IDN=0x07)，等待 bRefreshStatus 回到 0x00 (Idle) 或 0x03 (Success)
- 若 bRefreshStatus == 0x00 (Idle) 或 0x03 (Success): 直接進入下一步

**UFS SPEC Reference**: JESD220H Section 14.3 (bRefreshStatus Attribute)

---

### Step 0.4: Gate — Disable MIX Mode (IC=8329/8363)

**目的**: 針對特定 IC 型號 (8329/8363) 關閉 MIX mode，避免影響 Refresh 測試結果。

**Check**: 若 IC 為 8329 或 8363，設定 HW register 關閉 MIX mode。

| Field | Value |
|-------|-------|
| HW Register[0xB13] | 0x00 (Disable MIX mode) |
| HW Register[0xB14] | 0x00 (Disable MIX mode) |

**Branch Logic**: 僅在 IC=8329 或 IC=8363 時執行，其他 IC 跳過。

**UFS SPEC Reference**: Vendor-specific HW configuration（非 UFS SPEC 定義）

---

## Loop — LUN Config Case 1~3

外層迴圈：針對 3 種 LUN 配置依序執行。

**Case 1**: (MaxNumberLU - 2) 個 LUN，memory type = EM1，AU 分配扣除 boot LU limit，含 2 個 boot LU。
**Case 2**: 全部 32 個 LUN，memory type = Normal，AU = total AU / 32，無 boot LU。
**Case 3**: 全部 32 個 LUN，memory type = Normal，AU = total AU / 32，無 boot LU，啟用 Shared WriteBooster（需先檢查 WB 支援）。

---

## Phase 1 — LUN Configuration

### Step 1.1: WRITE DESCRIPTOR (Configuration) — 配置 LUN

**UFS QUERY**: `WRITE DESCRIPTOR (0x08)` — Configuration Descriptor (IDN=0x01)

**目的**: 根據當前 Case 配置 LUN 數量、Memory Type 及 Allocation Unit 大小。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| Descriptor IDN | 0x01 (Configuration Descriptor) |
| Index | 0x00 |
| Selector | 0x00 |
| Length | Configuration Descriptor length |

**Branch Logic** (per Case):

Case 1:
- Number of LUNs: MaxNumberLU - 2
- Memory Type: 0x01 (EM1 / Enhanced Memory Type 1)
- Boot LUNs: 2, AU = boot AU limit
- Data LUNs AU: (total AU - boot AU limit) / (MaxNumberLU - 2)

Case 2:
- Number of LUNs: 32 (use all available LUNs)
- Memory Type: 0x00 (Normal)
- AU per LUN: total AU / 32
- Boot LUNs: 0

Case 3:
- Number of LUNs: 32
- Memory Type: 0x00 (Normal)
- AU per LUN: total AU / 32
- Boot LUNs: 0
- **額外設定**: bWriteBoosterBufferType = 0x00 (Shared), dNumSharedWriteBoosterBufferAllocUnits = dWriteBoosterBufferMaxNAllocUnits
- **前置檢查**: 確認裝置支援 WriteBooster（讀取 Device Descriptor 確認 bWriteBoosterBufferType 支援）
- 若不支援 WriteBooster：Pattern 判定為 PASS（非 NOT SUPPORTED），跳過 Case 3
- 若支援：完成 WB 配置後 SET FLAG(fWriteBoosterEn, IDN=0x0E) 啟用 WB

**Expected**: QUERY RESPONSE Success（JIRA step 5）

**UFS SPEC Reference**: JESD220H Section 14.1.4.2 (Configuration Descriptor), Section 14.2 (Flags)

---

## Loop — Auto Standby Case 1~3

中層迴圈：針對 3 種 Auto Standby 模式依序執行。

**Case 1**: Enable Auto Standby
**Case 2**: Disable Auto Standby
**Case 3**: Enable Auto Standby（配合 Hibernate 流程輪詢 bRefreshStatus）

---

## Phase 2 — Auto Standby Configuration

### Step 2.1: HW Config — 設定 Auto Standby

**目的**: 根據當前 Case 啟用或停用 Auto Standby 功能。

| Field | Value |
|-------|-------|
| HW Register[0xA07] | Case 1: 0x3B (Enable) / Case 2: 0x00 (Disable) / Case 3: 0x3B (Enable) |

**Branch Logic**:
- Case 1 (Enable): 設定 HW Register[0xA07] = 0x3B
- Case 2 (Disable): 設定 HW Register[0xA07] = 0x00
- Case 3 (Enable + Hibernate): 設定 HW Register[0xA07] = 0x3B，後續 Step 5.2 使用 Hibernate 輪詢模式

**UFS SPEC Reference**: Vendor-specific HW configuration（非 UFS SPEC 定義）

---

## Loop — fBackgroundOpsEn: Enable / Disable

內層迴圈：分別以 fBackgroundOpsEn 啟用與停用狀態執行測試。

**Iteration 1**: Enable fBackgroundOpsEn（SET FLAG）
**Iteration 2**: Disable fBackgroundOpsEn（CLEAR FLAG）

---

## Phase 3 — Refresh Setup

### Step 3.1: SET FLAG / CLEAR FLAG (fBackgroundOpsEn) — 設定 BKOPS 狀態

**UFS QUERY**: `SET FLAG (0x02)` or `CLEAR FLAG (0x05)` — fBackgroundOpsEn (IDN=0x03)

**目的**: 根據迴圈 iteration 啟用或停用 Background Operations。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) or 0x05 (CLEAR FLAG) |
| Flag IDN | 0x03 (fBackgroundOpsEn) |

**Branch Logic**:
- Iteration 1 (Enable): SET FLAG (0x02), fBackgroundOpsEn (0x03)
- Iteration 2 (Disable): CLEAR FLAG (0x05), fBackgroundOpsEn (0x03)

**Expected**: QUERY RESPONSE Success（JIRA step 7）

**UFS SPEC Reference**: JESD220H Section 14.2 (Flags, fBackgroundOpsEn)

---

### Step 3.2: WRITE ATTRIBUTE (bRefreshUnit) — 設為 WHOLE_DEVICE

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bRefreshUnit (IDN=0x2E)

**目的**: 設定 Refresh 範圍為整個裝置（WHOLE_DEVICE）。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| Attribute IDN | 0x2E (bRefreshUnit) |
| Index | 0x00 |
| Selector | 0x00 |
| Value | 0x01 (WHOLE_DEVICE) |

**Expected**: QUERY RESPONSE Success（JIRA step 8）

**UFS SPEC Reference**: JESD220H Section 14.3 (bRefreshUnit Attribute)

---

### Step 3.3: WRITE ATTRIBUTE (bRefreshMethod) — 隨機選擇 Refresh 方法

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bRefreshMethod (IDN=0x2F)

**目的**: 隨機選擇 Refresh 執行方法。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| Attribute IDN | 0x2F (bRefreshMethod) |
| Index | 0x00 |
| Selector | 0x00 |
| Value | Rand(1, 2) — 0x01: Manual-Force / 0x02: Manual-Selective |

**Branch Logic** (per JIRA random):
- Case 1 (50%): bRefreshMethod = 0x01 (Manual-Force)
- Case 2 (50%): bRefreshMethod = 0x02 (Manual-Selective)

**Expected**: QUERY RESPONSE Success（JIRA step 9）

**UFS SPEC Reference**: JESD220H Section 14.3 (bRefreshMethod Attribute)

---

### Step 3.4: UNMAP — 清除所有 LUN 資料

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 清除所有 Logical Unit 上的資料，為 Refresh 操作準備乾淨的 NAND 狀態。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | All configured LUNs |
| UNMAP Block Descriptor Data Length | Depends on LUN count × 16 |
| UNMAP Block Descriptor[0] | LBA=0, Logical Block Count=LU capacity |
| ... | (one descriptor per LUN) |

**Expected**: GOOD Status（JIRA step 10）

**UFS SPEC Reference**: JESD220H Section 11.8 (UNMAP command), SBC-4

---

### Step 3.5: SET FLAG (fPurgeEnable) — 觸發 Purge

**UFS QUERY**: `SET FLAG (0x02)` — fPurgeEnable (IDN=0x06)

**目的**: 觸發 Purge 操作，實際清除 UNMAP 釋放的 NAND 區塊。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| Flag IDN | 0x06 (fPurgeEnable) |

**Expected**: QUERY RESPONSE Success（JIRA step 10）

**UFS SPEC Reference**: JESD220H Section 14.2 (Flags, fPurgeEnable)

---

### Step 3.6: READ ATTRIBUTE (bBackgroundOpStatus) — 確認 Purge 完成

**UFS QUERY**: `READ ATTRIBUTE (0x03)` — bBackgroundOpStatus (IDN=0x14)

**目的**: 輪詢 bBackgroundOpStatus 確認 Purge 操作已完成，確保後續寫入測試的資料完整性。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| Attribute IDN | 0x14 (bBackgroundOpStatus) |
| Index | 0x00 |
| Selector | 0x00 |

**Poll Logic**: 定期讀取直到 bBackgroundOpStatus 表示無進行中的背景操作（通常為 0x00）。

**UFS SPEC Reference**: JESD220H Section 14.3 (bBackgroundOpStatus Attribute)

---

## Phase 4 — Pre-Refresh Random Write

### Step 4.1: WRITE(10) — 隨機寫入測試資料

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 在 Refresh 操作前寫入測試資料，使 NAND 有資料需要 Refresh。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | Random(0, MaxNumberLU) — 每筆寫入重新選擇 LUN |
| LBA | Random(0, LU_Capacity - ChunkSize) — 避免超出範圍 |
| Transfer Length | 65535 blocks (Write10 max) |
| FUA | 0 (不強制寫入媒體) |
| Total Write Size | Case 1/2: 50 GB / Case 3: dWriteBoosterBufferMaxNAllocUnits × AU size (bytes) |

**Branch Logic** (per Case):
- Case 1 & 2: 總寫入 50 GB
- Case 3: 總寫入 = dWriteBoosterBufferMaxNAllocUnits × AU size（將 AU count 轉換為 bytes）

**Expected**: GOOD Status（JIRA step 11）

**UFS SPEC Reference**: JESD220H Section 11.4 (WRITE(10) command), SBC-4

---

### Step 4.2: READ DESCRIPTOR (Device Health) — 讀取 dRefreshTotalCount (pre)

**UFS QUERY**: `READ DESCRIPTOR (0x07)` — Device Health Descriptor (IDN=0x09)

**目的**: 在觸發 Refresh 前，記錄當前的 dRefreshTotalCount 值作為基準。

| Field | Value |
|-------|-------|
| Query Opcode | 0x07 (READ DESCRIPTOR) |
| Descriptor IDN | 0x09 (Device Health Descriptor) |
| Index | 0x00 |
| Selector | 0x00 |
| Length | 0x2D (45 bytes, covers bLength through dRefreshTotalCount) |
| Target Field | dRefreshTotalCount (byte offset 37~40, 4 bytes, little-endian) |

**Expected**: QUERY RESPONSE Success（JIRA step 12）

**UFS SPEC Reference**: JESD220H Section 14.1.4.5 (Device Health Descriptor, dRefreshTotalCount)

---

## Phase 5 — Refresh Execution

### Step 5.1: SET FLAG (fRefreshEnable) — 觸發 Refresh

**UFS QUERY**: `SET FLAG (0x02)` — fRefreshEnable (IDN=0x07)

**目的**: 設定 fRefreshEnable flag 觸發 Refresh 操作。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| Flag IDN | 0x07 (fRefreshEnable) |

**Expected**: QUERY RESPONSE Success（JIRA step 13）

**UFS SPEC Reference**: JESD220H Section 14.2 (Flags, fRefreshEnable)

---

### Step 5.2: READ ATTRIBUTE (bRefreshStatus) — Poll Refresh 完成

**UFS QUERY**: `READ ATTRIBUTE (0x03)` — bRefreshStatus (IDN=0x2C)

**目的**: 輪詢 bRefreshStatus 直到 Refresh 操作完成（Success = 0x03）或回到 Idle（0x00）。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| Attribute IDN | 0x2C (bRefreshStatus) |
| Index | 0x00 |
| Selector | 0x00 |

**Branch Logic** (per Auto Standby Case):

Case 1 & 2:
- 每 1 分鐘讀取 bRefreshStatus
- 直到 bRefreshStatus == 0x03 (Completed) 或 0x00 (Idle)

Case 3 (Hibernate):
- Enter Hibernate (via START STOP UNIT, POWER CONDITION=0x03)
- Idle 1 分鐘
- Exit Hibernate (via START STOP UNIT, POWER CONDITION=0x01)
- 讀取 bRefreshStatus
- 若尚未 0x03 或 0x00，重複 Enter Hibernate → Idle → Exit Hibernate → Read 循環

**Expected**: bRefreshStatus == 0x03 (Completed) or 0x00 (Idle)（JIRA step 14）

**bRefreshStatus Values**:
| Value | State |
|-------|-------|
| 0x00 | Idle |
| 0x01 | Refresh In Progress |
| 0x02 | Refresh Stopped |
| 0x03 | Refresh Completed Successfully |

**UFS SPEC Reference**: JESD220H Section 14.3 (bRefreshStatus Attribute)

---

## Phase 6 — Post-Refresh Verification

### Step 6.1: READ DESCRIPTOR (Device Health) — 讀取 dRefreshTotalCount (post)

**UFS QUERY**: `READ DESCRIPTOR (0x07)` — Device Health Descriptor (IDN=0x09)

**目的**: Refresh 完成後再次讀取 dRefreshTotalCount，用於與 pre 值比較。

| Field | Value |
|-------|-------|
| Query Opcode | 0x07 (READ DESCRIPTOR) |
| Descriptor IDN | 0x09 (Device Health Descriptor) |
| Index | 0x00 |
| Selector | 0x00 |
| Length | 0x2D (45 bytes) |
| Target Field | dRefreshTotalCount (byte offset 37~40, 4 bytes, little-endian) |

**Expected**: QUERY RESPONSE Success（JIRA step 15）

**UFS SPEC Reference**: JESD220H Section 14.1.4.5 (Device Health Descriptor)

---

### Step 6.2: Compare — 驗證 dRefreshTotalCount 增加

**Host-side Verification** — 非 SCSI CMD 或 UFS Query

**目的**: 比較 Refresh 前後的 dRefreshTotalCount 值，確認 Refresh 操作確實被執行且計數增加。

| Field | Value |
|-------|-------|
| Pre-Refresh Value | Step 4.2 讀取的 dRefreshTotalCount |
| Post-Refresh Value | Step 6.1 讀取的 dRefreshTotalCount |
| Condition | Post > Pre |

**Expected**: dRefreshTotalCount > original value（JIRA step 16）

**UFS SPEC Reference**: JESD220H Section 14.1.4.5 (Device Health Descriptor, dRefreshTotalCount)

---

### Step 6.3: CLEAR FLAG (fRefreshEnable) — 清除 Refresh Enable

**UFS QUERY**: `CLEAR FLAG (0x05)` — fRefreshEnable (IDN=0x07)

**目的**: 清除 fRefreshEnable flag，避免影響下一次迭代的 Refresh 觸發。

| Field | Value |
|-------|-------|
| Query Opcode | 0x05 (CLEAR FLAG) |
| Flag IDN | 0x07 (fRefreshEnable) |

**Expected**: QUERY RESPONSE Success（JIRA step 17）

**UFS SPEC Reference**: JESD220H Section 14.2 (Flags, fRefreshEnable)

---

## 附錄 A — UFS Query IDN 對照表

### Flags (bFlagIDN)

| IDN | Name | Access | 使用於 |
|:---|:---|:---|:---|
| 0x03 | fBackgroundOpsEn | Volatile (Set/Clear) | Step 3.1 |
| 0x06 | fPurgeEnable | Volatile (Set) | Step 3.5 |
| 0x07 | fRefreshEnable | Volatile (Set/Clear) | Step 0.3, Step 5.1, Step 6.3 |
| 0x0E | fWriteBoosterEn | Volatile (Set) | Step 1.1 (Case 3 only) |

### Attributes (bAttrIDN)

| IDN | Name | Size | Access | 使用於 |
|:---|:---|:---|:---|:---|
| 0x14 | bBackgroundOpStatus | 1 | Read-Only | Step 3.6 |
| 0x2C | bRefreshStatus | 1 | Read-Only | Step 0.3, Step 5.2 |
| 0x2E | bRefreshUnit | 1 | Read-Write | Step 3.2 |
| 0x2F | bRefreshMethod | 1 | Read-Write | Step 3.3 |

### Descriptors (bDescriptorIDN)

| IDN | Name | 使用於 |
|:---|:---|:---|
| 0x00 | Device Descriptor | Step 0.1, Step 0.2 |
| 0x01 | Configuration Descriptor | Step 1.1 |
| 0x09 | Device Health Descriptor | Step 4.2, Step 6.1 |

---

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | 使用於 |
|:---|:---|:---|:---|
| 0x2A | WRITE(10) | 10 | Step 4.1 — 隨機寫入測試資料 |
| 0x42 | UNMAP | 10 | Step 3.4 — 清除 LUN 資料 |

---

## 自我驗證

- Tree Diagram leaf steps: **19**
  Phase 0: 4 (0.1~0.4), Phase 1: 1 (1.1), Phase 2: 1 (2.1), Phase 3: 6 (3.1~3.6), Phase 4: 2 (4.1~4.2), Phase 5: 2 (5.1~5.2), Phase 6: 3 (6.1~6.3) → Total: 19
- `### Step` sections: **19** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（13 個 step 有 Expected: 1.1, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2, 6.3）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文 "expect device response success" / "Polling until 03h or 0h" / "check dRefreshTotalCount increase"）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
- UNMAP + Purge 已正確拆分為三個獨立 Step（3.4: UNMAP, 3.5: SET FLAG fPurgeEnable, 3.6: READ bBackgroundOpStatus）✓
