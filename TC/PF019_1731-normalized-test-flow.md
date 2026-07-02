---
title: PF019_1731_AdvancePin_POR_SPOR-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf019_1731, scsi-cmd, advance-pin, por, spor, pin-data]
description: >
  驗證 Advance Pin Mode 在 POR / SPOR 後 Pin Data 保留行為。透過 Context ID = 0x18
  寫入 pin data 後執行 POR/SPOR Reset，再以 WRITE BUFFER / READ BUFFER 檢查
  pin data bitmap 是否完整保留（0xFFFF_FFFF）。測試涵蓋 4 個 LUN（LUN0 Normal,
  LUN8/LUN16/LUN24 Enhanced）並在 burn-in 迴圈中重複執行。
sources:
  - JIRA: PF019_1731 (SYSTCUFS-1976)
  - UFS Spec: JESD220H Sections 10.7.3, 10.7.4, 10.7.9, 14.2, 14.3
---

# PF019_1731 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置在 Advance Pin Mode 下，以 Context ID = 0x18（pin data）寫入資料後，
經歷 POR / SPOR Reset，pin data bitmap 是否能完整保留（0xFFFF_FFFF）。
測試於 burn-in 迴圈中對 LUN0 / LUN8 / LUN16 / LUN24 重複執行 Erase → Write → Reset → Verify 流程。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | Check IC + NAND is 8361 WDS OPPO | Phase 0 Step 0.1（硬體相容性檢查） |
| Step 2 | Read attribute 0xE0 dVendorFeatureSupport bit6 | Phase 0 Step 0.2（Advance Pin Mode 支援檢查） |
| Step 3 | Config TLC LUN and SLC LUN（LUN0/8/16/24） | Phase 1 Step 1.1~1.4（LUN 配置） |
| Step 4 | Config 4G WriteBooster + Enable | Phase 2 Step 2.1~2.2（WB 配置與啟用） |
| Step 5 | Erase purge all card | Phase 3 Step 3.1~3.3（UNMAP + Purge） |
| Step 6 | Sequential write to LUN0/8/16/24 FUA=1, Context id=18h | Phase 4 Step 4.1~4.4（Sequential Write） |
| Step 7 | Insert POR/SPOR case | Phase 5 Step 5.1~5.2（POR + SPOR Reset） |
| Step 8 | Send write buffer cmd Mode=2 Buffer ID=3 | Phase 6 Step 6.1（WRITE BUFFER） |
| Step 9 | Send read buffer cmd Mode=2 Buffer ID=4, check bitmap=0xFFFF_FFFF | Phase 6 Step 6.2（READ BUFFER + Verify） |
| Step 10 | Loop step 5~step 9 for every enabled LUN and startLBA | Loop（Phase 3~6 迴圈） |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF019_1731 Test Flow
│
├── Phase 0: 裝置相容性與功能檢查（Pre-condition Gate）
│   ├── Step 0.1: 硬體相容性檢查 — IC=8361, NAND=WDS, Vendor=OPPO
│   └── Step 0.2: UFS QUERY READ ATTRIBUTE — 讀取 dVendorFeatureSupport (0xE0) bit6 檢查 Advance Pin Mode
│
├── Phase 1: LUN 配置（Configuration）
│   ├── Step 1.1: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0 (Normal Memory, capacity=total AU/3) → Expected: QUERY RESPONSE Success
│   ├── Step 1.2: UFS QUERY WRITE DESCRIPTOR — 配置 LUN8 (Enhanced Memory, BootLunA) → Expected: QUERY RESPONSE Success
│   ├── Step 1.3: UFS QUERY WRITE DESCRIPTOR — 配置 LUN16 (Enhanced Memory, BootLunB) → Expected: QUERY RESPONSE Success
│   └── Step 1.4: UFS QUERY WRITE DESCRIPTOR — 配置 LUN24 (Enhanced Memory, capacity=total AU/3) → Expected: QUERY RESPONSE Success
│
├── Phase 2: WriteBooster 配置與啟用
│   ├── Step 2.1: UFS QUERY WRITE DESCRIPTOR — 配置 4G WriteBooster Buffer → Expected: QUERY RESPONSE Success
│   └── Step 2.2: UFS QUERY SET FLAG — 啟用 WriteBooster (fWriteBoosterEn, 0x0E) → Expected: QUERY RESPONSE Success
│
└── Loop (burn_in_loop 次，for every enabled LUN and startLBA1/startLBA2)
    │
    ├── Phase 3: Erase + Purge
    │   ├── Step 3.1: UNMAP(10) — 全卡 Unmap 清除 → Expected: GOOD Status
    │   ├── Step 3.2: UFS QUERY SET FLAG — 觸發 Purge (fPurgeEnable, 0x06) → Expected: QUERY RESPONSE Success
    │   └── Step 3.3: UFS QUERY READ ATTRIBUTE — 輪詢 bPurgeStatus 確認 Purge 完成
    │
    ├── Phase 4: Pin Data Sequential Write
    │   ├── Step 4.1: WRITE(16) — LUN0 Sequential Write, FUA=1, Context ID=18h → Expected: GOOD Status
    │   ├── Step 4.2: WRITE(16) — LUN8 Sequential Write, FUA=1, Context ID=18h → Expected: GOOD Status
    │   ├── Step 4.3: WRITE(16) — LUN16 Sequential Write, FUA=1, Context ID=18h → Expected: GOOD Status
    │   └── Step 4.4: WRITE(16) — LUN24 Sequential Write, FUA=1, Context ID=18h → Expected: GOOD Status
    │
    ├── Phase 5: POR / SPOR Reset
    │   ├── Step 5.1: POR Reset — 執行 POR（Power Cycle / RST_n / EndPoint / UniPro 擇一）
    │   └── Step 5.2: SPOR Reset — 執行 SPOR（Power Cycle / RST_n / EndPoint / UniPro 擇一）
    │
    └── Phase 6: Pin Data Bitmap 驗證
        ├── Step 6.1: WRITE BUFFER — Mode=2, Buffer ID=3, 寫入 Pin Data Bitmap 查詢參數 → Expected: GOOD Status
        └── Step 6.2: READ BUFFER — Mode=2, Buffer ID=4, 讀取並驗證 Pin Data Bitmap → Expected: GOOD Status, pin data bitmap == 0xFFFF_FFFF
```

---

## Phase 0 — 裝置相容性與功能檢查

### Step 0.1: 硬體相容性檢查

**目的**: 確認 IC / NAND / Vendor 組合為支援的配置。

**Check**: IC=8361, NAND=WDS, Vendor=OPPO

**若不支援**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

**UFS SPEC Reference**: N/A（vendor-specific hardware check）

---

### Step 0.2: Advance Pin Mode 支援檢查

**UFS QUERY**: `READ ATTRIBUTE (dVendorFeatureSupport, IDN 0xE0)`

**目的**: 檢查裝置是否支援 Advance Pin Mode（讀取 dVendorFeatureSupport bit6）。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| bAttrIDN | 0xE0 (dVendorFeatureSupport) |
| Expected check | bit6 == 1 (Advance Pin Mode supported) |

**bit6 == 0 時**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

**UFS SPEC Reference**: N/A（vendor-specific attribute，不在 JESD220H 定義範圍內）

---

## Phase 1 — LUN 配置

### Step 1.1: 配置 LUN0（Normal Memory）

**UFS QUERY**: `WRITE DESCRIPTOR (Configuration Descriptor, IDN 0x01)`

**目的**: 將 LUN0 設定為 Normal Memory Type，容量為總 AU 的 1/3。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |
| LUN Number | 0x00 (LUN0) |
| bMemoryType | 0x00 (Normal Memory) |
| dNumAllocUnits | total_AU / 3 |

**Expected**: `QUERY RESPONSE Success`（JIRA Step 3: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.9 (WRITE DESCRIPTOR), Section 14.2 (Configuration Descriptor, Unit Descriptor)

---

### Step 1.2: 配置 LUN8（Enhanced Memory, BootLunA）

**UFS QUERY**: `WRITE DESCRIPTOR (Configuration Descriptor, IDN 0x01)`

**目的**: 將 LUN8 設定為 Enhanced Memory Type，並指定為 Boot LU A。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |
| LUN Number | 0x08 (LUN8) |
| bMemoryType | 0x02 (Enhanced Memory) |
| bBootLunID | 0x00 (Boot LU A) |

**Expected**: `QUERY RESPONSE Success`（JIRA Step 3: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.9 (WRITE DESCRIPTOR), Section 14.2 (Configuration Descriptor, Unit Descriptor)

---

### Step 1.3: 配置 LUN16（Enhanced Memory, BootLunB）

**UFS QUERY**: `WRITE DESCRIPTOR (Configuration Descriptor, IDN 0x01)`

**目的**: 將 LUN16 設定為 Enhanced Memory Type，並指定為 Boot LU B。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |
| LUN Number | 0x10 (LUN16) |
| bMemoryType | 0x02 (Enhanced Memory) |
| bBootLunID | 0x01 (Boot LU B) |

**Expected**: `QUERY RESPONSE Success`（JIRA Step 3: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.9 (WRITE DESCRIPTOR), Section 14.2 (Configuration Descriptor, Unit Descriptor)

---

### Step 1.4: 配置 LUN24（Enhanced Memory）

**UFS QUERY**: `WRITE DESCRIPTOR (Configuration Descriptor, IDN 0x01)`

**目的**: 將 LUN24 設定為 Enhanced Memory Type，容量為總 AU 的 1/3。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |
| LUN Number | 0x18 (LUN24) |
| bMemoryType | 0x02 (Enhanced Memory) |
| dNumAllocUnits | total_AU / 3 |

**Expected**: `QUERY RESPONSE Success`（JIRA Step 3: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.9 (WRITE DESCRIPTOR), Section 14.2 (Configuration Descriptor, Unit Descriptor)

---

## Phase 2 — WriteBooster 配置與啟用

### Step 2.1: 配置 4G WriteBooster Buffer

**UFS QUERY**: `WRITE DESCRIPTOR (Configuration Descriptor, IDN 0x01)`

**目的**: 配置 4G WriteBooster Buffer 大小與類型。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |
| bWriteBoosterBufferType | 0x00 (Shared) or 0x01 (Dedicated) |
| dWriteBoosterBufferSize | 4G equivalent allocation units |

**Expected**: `QUERY RESPONSE Success`（JIRA Step 4: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.9 (WRITE DESCRIPTOR), Section 14.2 (Configuration Descriptor, WriteBooster fields)

---

### Step 2.2: 啟用 WriteBooster

**UFS QUERY**: `SET FLAG (fWriteBoosterEn, IDN 0x0E)`

**目的**: 啟用 WriteBooster 功能。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x0E (fWriteBoosterEn) |
| Flag Value | 1 (Enable) |

**Expected**: `QUERY RESPONSE Success`（JIRA Step 4: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.8.2 (SET FLAG), Section 14.2 (Flags)

---

## Phase 3 — Erase + Purge

### Step 3.1: UNMAP 全卡清除

**SCSI CMD**: `UNMAP (42h)`

**目的**: 對所有 LUN 執行 UNMAP 以清除既有資料，為 Purge 做準備。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | LUN0, LUN8, LUN16, LUN24 |
| ANCHOR | 0 (Non-Anchor) |
| UNMAP LBA List | Full LUN range (LBA 0 to capacity-1) |

**Expected**: `GOOD Status`（JIRA Step 5: "expect device response success"）

**UFS SPEC Reference**: SBC-4 Section 5.32 (UNMAP), JESD220H Section 10.7.1 (SCSI Command)

---

### Step 3.2: 觸發 Purge

**UFS QUERY**: `SET FLAG (fPurgeEnable, IDN 0x06)`

**目的**: 觸發 Purge 操作以實體清除 UNMAP 釋放的空間。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x06 (fPurgeEnable) |
| Flag Value | 1 (Enable) |

**Expected**: `QUERY RESPONSE Success`（JIRA Step 5: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.8.2 (SET FLAG), Section 14.2 (Flags)

---

### Step 3.3: 確認 Purge 完成

**UFS QUERY**: `READ ATTRIBUTE (bPurgeStatus, IDN 0x14)`

**目的**: 輪詢 bPurgeStatus 確認 Purge 操作已完成後再繼續。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| bAttrIDN | 0x14 (bBackgroundOpStatus / bPurgeStatus) |
| Poll until | Purge complete (0x00 = Idle) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.3 (READ ATTRIBUTE), Section 14.3 (Attributes)

---

## Phase 4 — Pin Data Sequential Write

### Step 4.1: LUN0 Sequential Write（Pin Data, FUA=1）

**SCSI CMD**: `WRITE(16) (8Ah)`

**目的**: 對 LUN0 進行 Sequential Write，使用 Context ID = 0x18（pin data），FUA=1 確保資料直寫 NAND。

| Field | Value |
|-------|-------|
| Opcode | 0x8A |
| LUN | 0x00 (LUN0) |
| FUA | 1 (Force Unit Access) |
| Context ID (UPIU) | 0x18 (Pin Data) |
| Transfer Length | random(512K, 2M) |
| Start LBA | startLBA1 = 0, startLBA2 = (LU capacity - 1 - total_size) |
| Chunk Size | random(4K, 64K) |

**Expected**: `GOOD Status`（JIRA Step 6: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.1 (SCSI Command via UPIU), SBC-4 Section 5.32 (WRITE(16))

---

### Step 4.2: LUN8 Sequential Write（Pin Data, FUA=1）

**SCSI CMD**: `WRITE(16) (8Ah)`

**目的**: 對 LUN8 進行 Sequential Write，使用 Context ID = 0x18（pin data），FUA=1。

| Field | Value |
|-------|-------|
| Opcode | 0x8A |
| LUN | 0x08 (LUN8) |
| FUA | 1 (Force Unit Access) |
| Context ID (UPIU) | 0x18 (Pin Data) |
| Transfer Length | random(512K, 2M) |
| Start LBA | startLBA1 = 0, startLBA2 = (LU capacity - 1 - total_size) |
| Chunk Size | random(4K, 64K) |

**Expected**: `GOOD Status`（JIRA Step 6: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.1 (SCSI Command via UPIU), SBC-4 Section 5.32 (WRITE(16))

---

### Step 4.3: LUN16 Sequential Write（Pin Data, FUA=1）

**SCSI CMD**: `WRITE(16) (8Ah)`

**目的**: 對 LUN16 進行 Sequential Write，使用 Context ID = 0x18（pin data），FUA=1。

| Field | Value |
|-------|-------|
| Opcode | 0x8A |
| LUN | 0x10 (LUN16) |
| FUA | 1 (Force Unit Access) |
| Context ID (UPIU) | 0x18 (Pin Data) |
| Transfer Length | random(512K, 2M) |
| Start LBA | startLBA1 = 0, startLBA2 = (LU capacity - 1 - total_size) |
| Chunk Size | random(4K, 64K) |

**Expected**: `GOOD Status`（JIRA Step 6: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.1 (SCSI Command via UPIU), SBC-4 Section 5.32 (WRITE(16))

---

### Step 4.4: LUN24 Sequential Write（Pin Data, FUA=1）

**SCSI CMD**: `WRITE(16) (8Ah)`

**目的**: 對 LUN24 進行 Sequential Write，使用 Context ID = 0x18（pin data），FUA=1。

| Field | Value |
|-------|-------|
| Opcode | 0x8A |
| LUN | 0x18 (LUN24) |
| FUA | 1 (Force Unit Access) |
| Context ID (UPIU) | 0x18 (Pin Data) |
| Transfer Length | random(512K, 2M) |
| Start LBA | startLBA1 = 0, startLBA2 = (LU capacity - 1 - total_size) |
| Chunk Size | random(4K, 64K) |

**Expected**: `GOOD Status`（JIRA Step 6: "expect device response success"）

**UFS SPEC Reference**: JESD220H Section 10.7.1 (SCSI Command via UPIU), SBC-4 Section 5.32 (WRITE(16))

---

## Phase 5 — POR / SPOR Reset

### Step 5.1: POR Reset

**操作**: POR Reset

**目的**: 執行 POR（Power-On Reset）以觸發裝置重新初始化，驗證 pin data 在 POR 後的保留行為。

| Field | Value |
|-------|-------|
| Reset Type | POR (Power-On Reset) |
| Reset Mechanism | Power Cycle / RST_n / EndPoint Reset / UniPro Reset（擇一） |

**UFS SPEC Reference**: JESD220H Section 10.7.3 (Power-on Reset), Section 10.7.4 (Hardware Reset)

---

### Step 5.2: SPOR Reset

**操作**: SPOR Reset

**目的**: 執行 SPOR（Sudden Power-Off Recovery）以觸發裝置斷電恢復，驗證 pin data 在 SPOR 後的保留行為。

| Field | Value |
|-------|-------|
| Reset Type | SPOR (Sudden Power-Off Recovery) |
| Reset Mechanism | Power Cycle / RST_n / EndPoint Reset / UniPro Reset（擇一） |

**UFS SPEC Reference**: JESD220H Section 10.7.4 (Sudden Power-off Recovery)

---

## Phase 6 — Pin Data Bitmap 驗證

### Step 6.1: WRITE BUFFER — 寫入 Pin Data Bitmap 查詢參數

**SCSI CMD**: `WRITE BUFFER (3Bh)`

**目的**: 透過 WRITE BUFFER Mode=2, Buffer ID=3 寫入查詢參數（指定 LUN/LBA），為後續 READ BUFFER 讀取 pin data bitmap 做準備。

| Field | Value |
|-------|-------|
| Opcode | 0x3B |
| Mode | 0x02 (Data) |
| Buffer ID | 0x03 (Vendor-Unique: Pin Data Bitmap Query) |
| Parameter List | LUN = LUN0 / LUN8 / LUN16 / LUN24, LEN = 32, LBA = 0 |
| Parameter List Length | 32 bytes |

**Expected**: `GOOD Status`（JIRA Step 8: "expect device response success"）

**Note**: Buffer ID 0x03 為 Vendor-Unique，非 SPC-5 標準範圍（0x00–0x02）。Mode=2 對應 SPC-5 Data mode。

**UFS SPEC Reference**: SPC-5 Section 6.38 (WRITE BUFFER), JESD220H Section 10.7.1

---

### Step 6.2: READ BUFFER — 讀取並驗證 Pin Data Bitmap

**SCSI CMD**: `READ BUFFER (3Ch)`

**目的**: 透過 READ BUFFER Mode=2, Buffer ID=4 讀取 pin data bitmap，驗證在 POR/SPOR 後 bitmap 仍為 0xFFFF_FFFF（所有 pin data 完整保留）。

| Field | Value |
|-------|-------|
| Opcode | 0x3C |
| Mode | 0x02 (Data) |
| Buffer ID | 0x04 (Vendor-Unique: Pin Data Bitmap Result) |

**Expected**: `GOOD Status, pin data bitmap == 0xFFFF_FFFF`（JIRA Step 9: "expect device response success, expect pin data bitmap = 0xFFFF_FFFF"）

**Note**: Buffer ID 0x04 為 Vendor-Unique，非 SPC-5 標準範圍（0x00–0x02）。Mode=2 對應 SPC-5 Data mode。

**UFS SPEC Reference**: SPC-5 Section 6.17 (READ BUFFER), JESD220H Section 10.7.1

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x02 | SET FLAG | Step 2.2: 啟用 fWriteBoosterEn；Step 3.2: 觸發 fPurgeEnable |
| 0x03 | READ ATTRIBUTE | Step 0.2: 讀取 dVendorFeatureSupport；Step 3.3: 輪詢 bPurgeStatus |
| 0x08 | WRITE DESCRIPTOR | Step 1.1~1.4: LUN 配置；Step 2.1: WB Buffer 配置 |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x06 | fPurgeEnable | Volatile (Set/Clear) | Step 3.2: 觸發 Purge 操作 |
| 0x0E | fWriteBoosterEn | Volatile (Set/Clear) | Step 2.2: 啟用 WriteBooster |

### Attribute IDN

| IDN | 名稱 | Size | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|:---|
| 0x14 | bBackgroundOpStatus | 1 | Read-Only | Step 3.3: 輪詢確認 Purge 完成 |
| 0xE0 | dVendorFeatureSupport | 4 | Read-Only | Step 0.2: bit6 Advance Pin Mode 支援 |

### Descriptor IDN

| IDN | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x01 | Configuration Descriptor | Step 1.1~1.4: LUN MemoryType / BootLunID / Capacity 配置；Step 2.1: WB Buffer Size/Type 配置 |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x3B | WRITE BUFFER | 10 | Step 6.1: VU Pin Data Bitmap 查詢參數寫入（Mode=2, Buffer ID=3） |
| 0x3C | READ BUFFER | 10 | Step 6.2: VU Pin Data Bitmap 讀取驗證（Mode=2, Buffer ID=4） |
| 0x42 | UNMAP | 10 | Step 3.1: 全卡 Unmap 清除既有資料 |
| 0x8A | WRITE(16) | 16 | Step 4.1~4.4: Sequential Write, FUA=1, Context ID=0x18 |

---

## 附錄 C — UFS Reset 類型說明

| Reset 類型 | 縮寫 | 機制 | SPEC Reference | 本 Pattern 用途 |
|:---|:---|:---|:---|:---|
| Power-On Reset | POR | Power Cycle / RST_n / EndPoint / UniPro | JESD220H 10.7.3, 10.7.4 | Step 5.1 |
| Sudden Power-Off Recovery | SPOR | Power Cycle / RST_n / EndPoint / UniPro | JESD220H 10.7.4 | Step 5.2 |

---

## 附錄 D — Branch Logic（隨機參數）

Phase 4 中各 WRITE(16) Step 使用以下隨機參數：

| Parameter | Range | Notes |
|:---|:---|:---|
| total_size | random(512K, 2M) | 單次寫入總大小 |
| chunk_size | random(4K, 64K) | 每個 write command 大小 |
| startLBA | 0 (startLBA1) or LU_capacity - 1 - total_size (startLBA2) | 兩組起始 LBA 交替使用 |

這些隨機參數由 C++ 實作層處理，正規化流程中僅標示取值範圍。

---

## 自我驗證

- Tree Diagram leaf steps: **19**
  Phase 0: 2 (0.1, 0.2), Phase 1: 4 (1.1~1.4), Phase 2: 2 (2.1, 2.2), Phase 3: 3 (3.1~3.3), Phase 4: 4 (4.1~4.4), Phase 5: 2 (5.1, 5.2), Phase 6: 2 (6.1, 6.2) → Total: 19
- `### Step` sections: **19** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（14 個 step 有 Expected，來源均為 JIRA "expect device response success"）
  - Step 0.1: N/A（HW gate，JIRA 僅說 NOT SUPPORTED）
  - Step 0.2: N/A（feature gate，JIRA 僅說 NOT SUPPORTED）
  - Step 3.3: N/A（polling step，JIRA 未指定預期值）
  - Step 5.1, 5.2: N/A（JIRA Step 7 無 Expected）
  - 其餘 14 個 step 均有 JIRA 原文對應
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文 "expect device response success" 或 "expect pin data bitmap = 0xFFFF_FFFF"）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
