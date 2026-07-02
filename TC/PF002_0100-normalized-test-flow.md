---
title: PF002_0100_Read_Boot_After_BKOPS-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_0100, scsi-cmd, bkoops, boot, purge, reset]
description: >
  驗證在 BKOPS（Background Operations）執行期間與完成後，透過 HW_RESET / RST_n /
  EndPoint Reset / UniPro Reset 重設裝置，Boot LUN 資料仍能正確讀取。涵蓋三種背景
  寫入情境（初始 Purge、Sequential Write、Sequential + Random Write）後進行 Boot
  Read 驗證。
sources:
  - JIRA: PF002_0100 (SYSTCUFS-2)
  - UFS Spec: JESD220H Section 10.7.8–10.7.9 (Query), Section 11 (Purge, BKOPS), Section 13 (Boot)
---

# PF002_0100 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證裝置在經歷大量寫入觸發 BKOPS 後，透過不同 Reset 類型重設裝置，Boot LUN A
的資料仍可被正確讀取。Pattern 先透過 Purge 清除裝置，再以 Sequential / Random
Write 建立不同的背景忙碌情境（Scenario B / Scenario C），最後在 BKOPS 執行中
進行 Reset 並驗證 Boot Data 的正確性。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| 1 | Erase(Unmap) all enabled LUN | Step 1.1 |
| 2 | Set Purge enable flag | Step 1.2 |
| 3 | Polling Purge attribute until status = COMPLETE_SUCCESS | Step 1.3 |
| 4 | Erase(Unmap) all enabled LUN | Step 2.1 |
| 5 | Set Purge enable flag | Step 2.2 |
| 6 | Polling Purge attribute until status = COMPLETE_SUCCESS | Step 2.3 |
| 7 | Sequential Write all enabled LUN, make device busy | Step 2.4 |
| 8 | Erase(Unmap) all enabled LUN | Step 3.1 |
| 9 | Set Purge enable flag | Step 3.2 |
| 10 | Polling Purge attribute until status = COMPLETE_SUCCESS | Step 3.3 |
| 11 | Sequential Write all enabled LUN, make device busy | Step 3.4 |
| 12 | Random Write 10% of device capacity | Step 3.5 |
| 13 | Write data to all LBAs and all LUNs | Step 4.1 |
| 14 | map Boot LUN A | Step 4.2 |
| 15 | Random write until bBackgroundOpStatus > 1 | Step 4.3 |
| 16 | Enable BKOPS and Wait 800ms ~ 2s into suspend mode | Step 4.4 + 4.5 |
| 17 | Send HW_RESET / RST_n / ENDPOINT_RESET / UNIPRO_RESET to read boot data | Step 4.6 + 4.7 |
| 18 | Loop 3~5 [Detailed Test Steps] | Loop (3~5) wrapper |
| 19 | Write data to all LBAs and all LUNs | Step 5.1 |
| 20 | map Boot LUN A | Step 5.2 |
| 21 | Random write until bBackgroundOpStatus > 1 | Step 5.3 |
| 22 | Enable BKOPS and Wait 800ms ~ 2s into suspend mode | Step 5.4 + 5.5 |
| 23 | Send HW_RESET / RST_n / ENDPOINT_RESET / UNIPRO_RESET to read boot data | Step 5.6 + 5.7 |
| 24 | Loop 3~5 | Loop (3~5) wrapper |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF002_0100 Test Flow
│
├── Phase 0: 前置檢查
│   └── Step 0.1: 裝置相容性檢查
│
├── Phase 1: 初始 Purge（Round 1）─ JIRA Steps 1~3
│   ├── Step 1.1: UNMAP — Erase all enabled LUNs
│   ├── Step 1.2: SET FLAG (fPurgeEnable) — 啟用 Purge
│   └── Step 1.3: READ ATTRIBUTE (bPurgeStatus) — 輪詢確認 Purge 完成 → Expected: bPurgeStatus == 0x03 (COMPLETE_SUCCESS)
│
├── Phase 2: Purge + Sequential Write（Scenario B）─ JIRA Steps 4~7
│   ├── Step 2.1: UNMAP — Erase all enabled LUNs
│   ├── Step 2.2: SET FLAG (fPurgeEnable) — 啟用 Purge
│   ├── Step 2.3: READ ATTRIBUTE (bPurgeStatus) — 輪詢確認 Purge 完成 → Expected: bPurgeStatus == 0x03 (COMPLETE_SUCCESS)
│   └── Step 2.4: WRITE(10) — Sequential write all enabled LUNs
│
├── Phase 3: Purge + Sequential + Random Write（Scenario C）─ JIRA Steps 8~12
│   ├── Step 3.1: UNMAP — Erase all enabled LUNs
│   ├── Step 3.2: SET FLAG (fPurgeEnable) — 啟用 Purge
│   ├── Step 3.3: READ ATTRIBUTE (bPurgeStatus) — 輪詢確認 Purge 完成 → Expected: bPurgeStatus == 0x03 (COMPLETE_SUCCESS)
│   ├── Step 3.4: WRITE(10) — Sequential write all enabled LUNs
│   └── Step 3.5: WRITE(10) — Random write 10% device capacity
│
└── Loop (3~5 iterations)
    ├── Phase 4: Boot Read After BKOPS（Round 1）─ JIRA Steps 13~17
    │   ├── Step 4.1: WRITE(10) — Write data to all LBAs, all LUNs
    │   ├── Step 4.2: WRITE ATTRIBUTE (bBootLunEn) — Map Boot LUN A
    │   ├── Step 4.3: WRITE(10) — Random write (4K~4M) until bBackgroundOpStatus > 1
    │   ├── Step 4.4: SET FLAG (fBackgroundOpsEn) — Enable BKOPS
    │   ├── Step 4.5: Delay 800ms ~ 2s — 等待進入 Suspend Mode
    │   ├── Step 4.6: Reset (HW_RESET / RST_n / EndPoint / UniPro) — 重設裝置 → Expected: Reset device success
    │   └── Step 4.7: READ(10) — Read boot data from Boot W-LUN
    │
    └── Phase 5: Boot Read After BKOPS（Round 2）─ JIRA Steps 19~23
        ├── Step 5.1: WRITE(10) — Write data to all LBAs, all LUNs
        ├── Step 5.2: WRITE ATTRIBUTE (bBootLunEn) — Map Boot LUN A
        ├── Step 5.3: WRITE(10) — Random write (4K~4M) until bBackgroundOpStatus > 1
        ├── Step 5.4: SET FLAG (fBackgroundOpsEn) — Enable BKOPS
        ├── Step 5.5: Delay 800ms ~ 2s — 等待進入 Suspend Mode
        ├── Step 5.6: Reset (HW_RESET / RST_n / EndPoint / UniPro) — 重設裝置 → Expected: Reset device success
        └── Step 5.7: READ(10) — Read boot data from Boot W-LUN
```

---

## Phase 0 — 前置檢查

### Step 0.1: 裝置相容性檢查

**目的**: 確認當前裝置 IC / NAND / Vendor 組合為支援的配置，若不支援則終止測試。

**Check**: 依 JIRA Pattern 定義的支援 IC / NAND / Vendor 組合。

**若不支援**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

---

## Phase 1 — 初始 Purge（Round 1）

### Step 1.1: Erase All Enabled LUNs

**SCSI CMD**: `UNMAP (42h)`

**目的**: 清除所有已啟用 LUN 的資料，為 Purge 操作準備乾淨狀態。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | All enabled LUNs |
| UNMAP LBA Range | LBA=0, Block Count=Full LUN Capacity |
| ANCHOR | 0 (default) |

**UFS SPEC Reference**: JESD220H Section 11.6.5 (UNMAP)

---

### Step 1.2: Set Purge Enable Flag

**UFS QUERY**: `SET FLAG (fPurgeEnable, IDN 0x06)`

**目的**: 啟用 Purge 操作，觸發裝置清除所有資料。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x06 (fPurgeEnable) |
| Value | 0x01 (Enable) |

**UFS SPEC Reference**: JESD220H Section 11.6.7 (Purge Operation)

---

### Step 1.3: Polling Purge Status Until Complete

**UFS QUERY**: `READ ATTRIBUTE (bPurgeStatus, IDN 0x06)`

**目的**: 輪詢 bPurgeStatus 屬性，確認 Purge 操作已完成。若超過 600 次輪詢（約 10 分鐘）仍未完成，判定測試失敗。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| bAttrIDN | 0x06 (bPurgeStatus) |
| Polling Interval | ~1 second |
| Timeout | 600 polls (~10 min) |

**Expected**: bPurgeStatus == 0x03 (COMPLETE_SUCCESS)。

**UFS SPEC Reference**: JESD220H Section 11.6.7 (Purge Operation)

---

## Phase 2 — Purge + Sequential Write（Scenario B 建立）

Scenario B: 針對已寫入資料的裝置，裝置忙碌進行 BKOPS/GC 的使用情境。先 Purge
清除後再 Sequential Write 全 LUN 建立背景寫入狀態。

### Step 2.1: Erase All Enabled LUNs

**SCSI CMD**: `UNMAP (42h)`

**目的**: 清除所有已啟用 LUN 的資料。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | All enabled LUNs |
| UNMAP LBA Range | LBA=0, Block Count=Full LUN Capacity |
| ANCHOR | 0 (default) |

**UFS SPEC Reference**: JESD220H Section 11.6.5 (UNMAP)

---

### Step 2.2: Set Purge Enable Flag

**UFS QUERY**: `SET FLAG (fPurgeEnable, IDN 0x06)`

**目的**: 啟用 Purge 操作。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x06 (fPurgeEnable) |
| Value | 0x01 (Enable) |

**UFS SPEC Reference**: JESD220H Section 11.6.7 (Purge Operation)

---

### Step 2.3: Polling Purge Status Until Complete

**UFS QUERY**: `READ ATTRIBUTE (bPurgeStatus, IDN 0x06)`

**目的**: 輪詢確認 Purge 完成。逾時判定失敗。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| bAttrIDN | 0x06 (bPurgeStatus) |
| Polling Interval | ~1 second |
| Timeout | 600 polls (~10 min) |

**Expected**: bPurgeStatus == 0x03 (COMPLETE_SUCCESS)。

**UFS SPEC Reference**: JESD220H Section 11.6.7 (Purge Operation)

---

### Step 2.4: Sequential Write All Enabled LUNs

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對所有已啟用 LUN 進行 Sequential Write，使裝置進入忙碌狀態（BKOPS/GC）。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | All enabled LUNs |
| LBA | 0x00000000 (starting from 0) |
| Transfer Length | Full LUN Capacity |
| Data Pattern | Sequential increment data |

**UFS SPEC Reference**: JESD220H Section 10.12 (WRITE(10))

---

## Phase 3 — Purge + Sequential + Random Write（Scenario C 建立）

Scenario C: 針對已寫入資料的裝置，讓資料更分散於不同 Block 的使用情境。先
Purge 清除後，Sequential Write + Random Write 10% 容量建立分散的背景寫入狀態。

### Step 3.1: Erase All Enabled LUNs

**SCSI CMD**: `UNMAP (42h)`

**目的**: 清除所有已啟用 LUN 的資料。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | All enabled LUNs |
| UNMAP LBA Range | LBA=0, Block Count=Full LUN Capacity |
| ANCHOR | 0 (default) |

**UFS SPEC Reference**: JESD220H Section 11.6.5 (UNMAP)

---

### Step 3.2: Set Purge Enable Flag

**UFS QUERY**: `SET FLAG (fPurgeEnable, IDN 0x06)`

**目的**: 啟用 Purge 操作。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x06 (fPurgeEnable) |
| Value | 0x01 (Enable) |

**UFS SPEC Reference**: JESD220H Section 11.6.7 (Purge Operation)

---

### Step 3.3: Polling Purge Status Until Complete

**UFS QUERY**: `READ ATTRIBUTE (bPurgeStatus, IDN 0x06)`

**目的**: 輪詢確認 Purge 完成。逾時判定失敗。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| bAttrIDN | 0x06 (bPurgeStatus) |
| Polling Interval | ~1 second |
| Timeout | 600 polls (~10 min) |

**Expected**: bPurgeStatus == 0x03 (COMPLETE_SUCCESS)。

**UFS SPEC Reference**: JESD220H Section 11.6.7 (Purge Operation)

---

### Step 3.4: Sequential Write All Enabled LUNs

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對所有已啟用 LUN 進行 Sequential Write。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | All enabled LUNs |
| LBA | 0x00000000 (starting from 0) |
| Transfer Length | Full LUN Capacity |
| Data Pattern | Sequential increment data |

**UFS SPEC Reference**: JESD220H Section 10.12 (WRITE(10))

---

### Step 3.5: Random Write 10% Device Capacity

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對裝置進行 Random Write，寫入量為總容量的 10%，使資料更分散於不同
Block，加劇 BKOPS/GC 負擔。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | All enabled LUNs |
| LBA | Random (uniform distribution across each LUN) |
| Transfer Length | Random 4K ~ 4M per write, total ≈ 10% device capacity |
| Data Pattern | Random data |

**UFS SPEC Reference**: JESD220H Section 10.12 (WRITE(10))

---

## Loop (3~5 Iterations) — Boot Read After BKOPS

以下 Phase 4 與 Phase 5 各封裝於 3~5 次迭代的 Loop 內，代表兩輪 Boot Read
驗證。每輪迴圈內完整執行：寫入 → Boot LUN 設定 → 觸發 BKOPS → Reset →
讀取 Boot Data。

---

## Phase 4 — Boot Read After BKOPS（Round 1）

### Step 4.1: Write Data to All LBAs, All LUNs

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 將測試資料寫入所有 LUN 的全部 LBA，建立可供後續驗證的資料基底。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | All enabled LUNs |
| LBA | Full LBA range per LUN |
| Transfer Length | Full LUN Capacity |
| Data Pattern | Known test pattern (for later verification) |

**UFS SPEC Reference**: JESD220H Section 10.12 (WRITE(10))

---

### Step 4.2: Map Boot LUN A

**UFS QUERY**: `WRITE ATTRIBUTE (bBootLunEn, IDN 0x00)`

**目的**: 設定 Boot LUN A 為啟用，使 Reset 後裝置可從 Boot W-LUN 讀取 Boot
Data。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| bAttrIDN | 0x00 (bBootLunEn) |
| Value | 0x01 (Boot LUN A enabled) |

**UFS SPEC Reference**: JESD220H Section 13 (Boot), Section 14.3 (bBootLunEn)

---

### Step 4.3: Random Write Until BKOPS Critical (bBackgroundOpStatus > 1)

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 以 Random Write（4K~4M）持續寫入裝置，直到 bBackgroundOpStatus 超過
1（即 BKOPS 進入非 Idle 狀態），確保裝置正在進行 Background Operations。

**Branch Logic**:
- 每次 WRITE(10) 後讀取 bBackgroundOpStatus（READ ATTRIBUTE, IDN 0x14）
- 若 bBackgroundOpStatus ≤ 1 → 繼續寫入
- 若 bBackgroundOpStatus > 1 → 停止寫入，進入下一步

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | All enabled LUNs |
| LBA | Random |
| Transfer Length | Random 4K ~ 4M |
| Data Pattern | Random data |

**UFS SPEC Reference**: JESD220H Section 10.12 (WRITE(10)), Section 14.3 (bBackgroundOpStatus)

---

### Step 4.4: Enable BKOPS

**UFS QUERY**: `SET FLAG (fBackgroundOpsEn, IDN 0x03)`

**目的**: 啟用 Background Operations，讓裝置在 Idle 時自動執行 BKOPS。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x03 (fBackgroundOpsEn) |
| Value | 0x01 (Enable) |

**UFS SPEC Reference**: JESD220H Section 11.4 (Background Operations), Section 14.2 (fBackgroundOpsEn)

---

### Step 4.5: Delay 800ms ~ 2s（Wait Suspend Mode）

**目的**: 等待裝置在啟用 BKOPS 後約 800ms ~ 2s 進入 Suspend Mode，使 BKOPS
在背景執行。

| Field | Value |
|-------|-------|
| Delay Time | 800ms ~ 2s |
| Wait Condition | Device enters Suspend Mode |

**Note**: 此步驟非 SCSI CMD 亦非 UFS Query，為測試流程中的等待操作。

---

### Step 4.6: Reset Device

**UFS Reset**: `HW_RESET / RST_n / EndPoint Reset / UniPro Reset`

**目的**: 在 BKOPS 執行期間對裝置進行 Reset，驗證 Reset 後裝置能正常恢復。

| Field | Value |
|-------|-------|
| Reset Type | HW_RESET 或 RST_n 或 EndPoint Reset 或 UniPro Reset |
| Post-Reset | Wait for fDeviceInit == 0 |

**Expected**: Reset device success。

**UFS SPEC Reference**: JESD220H Section 10.7.7 (Reset)

---

### Step 4.7: Read Boot Data

**SCSI CMD**: `READ(10) (28h)`

**目的**: Reset 後從 Boot W-LUN A 讀取 Boot Data，驗證資料在 BKOPS 與 Reset
後仍可被正確存取。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot W-LUN (依 bBootLunEn 設定) |
| LBA | Boot LUN A starting address |
| Transfer Length | Boot data size |

**UFS SPEC Reference**: JESD220H Section 10.11 (READ(10)), Section 13 (Boot)

---

## Phase 5 — Boot Read After BKOPS（Round 2）

### Step 5.1: Write Data to All LBAs, All LUNs

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 第二輪測試：將測試資料寫入所有 LUN 的全部 LBA。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | All enabled LUNs |
| LBA | Full LBA range per LUN |
| Transfer Length | Full LUN Capacity |
| Data Pattern | Known test pattern |

**UFS SPEC Reference**: JESD220H Section 10.12 (WRITE(10))

---

### Step 5.2: Map Boot LUN A

**UFS QUERY**: `WRITE ATTRIBUTE (bBootLunEn, IDN 0x00)`

**目的**: 設定 Boot LUN A 為啟用。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| bAttrIDN | 0x00 (bBootLunEn) |
| Value | 0x01 (Boot LUN A enabled) |

**UFS SPEC Reference**: JESD220H Section 13 (Boot), Section 14.3 (bBootLunEn)

---

### Step 5.3: Random Write Until BKOPS Critical (bBackgroundOpStatus > 1)

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: Random Write 直到 bBackgroundOpStatus > 1。

**Branch Logic**:
- 每次 WRITE(10) 後讀取 bBackgroundOpStatus（READ ATTRIBUTE, IDN 0x14）
- 若 bBackgroundOpStatus ≤ 1 → 繼續寫入
- 若 bBackgroundOpStatus > 1 → 停止寫入

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | All enabled LUNs |
| LBA | Random |
| Transfer Length | Random 4K ~ 4M |
| Data Pattern | Random data |

**UFS SPEC Reference**: JESD220H Section 10.12 (WRITE(10)), Section 14.3 (bBackgroundOpStatus)

---

### Step 5.4: Enable BKOPS

**UFS QUERY**: `SET FLAG (fBackgroundOpsEn, IDN 0x03)`

**目的**: 啟用 Background Operations。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x03 (fBackgroundOpsEn) |
| Value | 0x01 (Enable) |

**UFS SPEC Reference**: JESD220H Section 11.4 (Background Operations), Section 14.2 (fBackgroundOpsEn)

---

### Step 5.5: Delay 800ms ~ 2s（Wait Suspend Mode）

**目的**: 等待裝置進入 Suspend Mode。

| Field | Value |
|-------|-------|
| Delay Time | 800ms ~ 2s |
| Wait Condition | Device enters Suspend Mode |

**Note**: 非 SCSI CMD / UFS Query，為測試流程等待操作。

---

### Step 5.6: Reset Device

**UFS Reset**: `HW_RESET / RST_n / EndPoint Reset / UniPro Reset`

**目的**: 在 BKOPS 執行期間對裝置進行 Reset。

| Field | Value |
|-------|-------|
| Reset Type | HW_RESET 或 RST_n 或 EndPoint Reset 或 UniPro Reset |
| Post-Reset | Wait for fDeviceInit == 0 |

**Expected**: Reset device success。

**UFS SPEC Reference**: JESD220H Section 10.7.7 (Reset)

---

### Step 5.7: Read Boot Data

**SCSI CMD**: `READ(10) (28h)`

**目的**: Reset 後從 Boot W-LUN A 讀取 Boot Data。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot W-LUN (依 bBootLunEn 設定) |
| LBA | Boot LUN A starting address |
| Transfer Length | Boot data size |

**UFS SPEC Reference**: JESD220H Section 10.11 (READ(10)), Section 13 (Boot)

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x02 | SET FLAG | 設定 fPurgeEnable (0x06)、fBackgroundOpsEn (0x03) |
| 0x03 | READ ATTRIBUTE | 讀取 bPurgeStatus (0x06)、bBackgroundOpStatus (0x14) |
| 0x04 | WRITE ATTRIBUTE | 寫入 bBootLunEn (0x00) |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x03 | fBackgroundOpsEn | Volatile (Set/Clear) | 啟用 Background Operations |
| 0x06 | fPurgeEnable | Volatile (Set/Clear) | 啟用 Purge 操作 |

### Attribute IDN

| IDN | 名稱 | Size | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|:---|
| 0x00 | bBootLunEn | 1 | Read-Write | 設定 Boot LUN A 為啟用 |
| 0x06 | bPurgeStatus | 1 | Read-Only | 輪詢確認 Purge 完成狀態 |
| 0x14 | bBackgroundOpStatus | 1 | Read-Only | 檢查 BKOPS 是否進入非 Idle 狀態 |

> **Note**: bPurgeStatus (Attribute IDN 0x06) 與 fPurgeEnable (Flag IDN 0x06)
> 共用相同的 IDN 數值，但透過不同的 Query Opcode 區分存取類型：
> READ ATTRIBUTE (0x03) → bPurgeStatus，SET FLAG (0x02) → fPurgeEnable。

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | 讀取 Boot Data (Boot W-LUN) |
| 0x2A | WRITE(10) | 10 | Sequential / Random Write, 觸發 BKOPS |
| 0x42 | UNMAP | 10 | Erase all enabled LUNs (Purge 前置) |

---

## 附錄 C — 本 Pattern 使用的 Reset 類型

| Reset 類型 | 說明 | SPEC Reference |
|:---|:---|:---|
| HW_RESET | 硬體重設（RST_n 訊號） | JESD220H Section 10.7.7 |
| RST_n | 硬體 Reset 腳位 | JESD220H Section 10.7.7 |
| EndPoint Reset | UFS EndPoint 重設（透過 DME） | JESD220H Section 10.7.7 |
| UniPro Reset | UniPro 層重設 | JESD220H Section 10.7.7 |

---

## 自我驗證

- Tree Diagram leaf steps: **27**（Phase 0: 1 (0.1), Phase 1: 3 (1.1~1.3), Phase 2: 4 (2.1~2.4), Phase 3: 5 (3.1~3.5), Loop → Phase 4: 7 (4.1~4.7), Loop → Phase 5: 7 (5.1~5.7) → Total: 27）
- `### Step` sections: **27** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（共 5 個 Expected：Step 1.3, 2.3, 3.3 來自 JIRA "COMPLETE_SUCCESS"；Step 4.6, 5.6 Reset 遵循 memory 慣例格式）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文或 user memory 慣例）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
