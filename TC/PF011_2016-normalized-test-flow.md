---
title: PF011_2016_B_SLC_Non_FUA_Write_Compare-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf011_2016, scsi-cmd, writebooster, spor, non-fua]
description: >
  驗證 WriteBooster (WB) 配置為最大 buffer 後，進行 Non-FUA Random Write，
  在 SPOR (HW Reset) 後確認寫入的資料仍可正確讀取比對 (Data Retention)。
  涵蓋 WB Config → Erase All (UNMAP + Purge) → WB Enable → Random Non-FUA Write →
  Auto Standby → SPOR → Read Compare 的完整流程。
sources:
  - JIRA: PF011_2016 (SYSTCUFS-2339)
  - UFS Spec: JESD220H Sections 10.7.8~10.7.9, 10.8, 11.4, 14.2.1~14.2.2, 14.3.1~14.3.2
---

# PF011_2016 B SLC Non-FUA Write Compare Test — Normalized Test Flow

## 測試架構（Tree Diagram）

```
PF011_2016 Test Flow
│
├── Phase 1: WriteBooster Configuration
│   ├── Step 1.1: READ DESCRIPTOR (Unit Descriptor) — 讀取最大 WB Buffer 分配單元數
│   │     → Expected: QUERY RESPONSE Success
│   ├── Step 1.2: WRITE DESCRIPTOR (Configuration Descriptor) — 配置 WB Buffer 為最大值
│   │     → Expected: QUERY RESPONSE Success
│
├── Phase 2: Erase All (Pre-condition)
│   ├── Step 2.1: UNMAP (42h) — Unmap 整卡 LBA 範圍 → Expected: GOOD Status
│   ├── Step 2.2: SET FLAG (fPurgeEnable, IDN 0x06) — 觸發 Purge → Expected: QUERY RESPONSE Success
│   ├── Step 2.3: READ ATTRIBUTE (bPurgeStatus, IDN 0x14) — 確認 Purge 完成
│
├── Phase 3: Enable WriteBooster
│   └── Step 3.1: SET FLAG (fWriteBoosterEn, IDN 0x0E) — 啟用 WriteBooster
│         → Expected: QUERY RESPONSE Success
│
├── Phase 4: Random Non-FUA Write
│   └── Loop (5 次迭代)
│       └── Step 4.1: WRITE(10) (2Ah) — Random Non-FUA Write
│             → Expected: GOOD Status
│
├── Phase 5: Auto Standby Verification
│   └── Step 5.1: Idle + Wait for Auto Standby — 閒置等待進入 Auto Standby
│         → Expected: Enters auto standby within 5 minutes
│
├── Phase 6: SPOR (HW Reset)
│   └── Step 6.1: HW_RESET — 觸發硬體重置 → Expected: Reset device success
│
└── Phase 7: Read Compare (SPOR Data Retention Verification)
    └── Loop (5 次迭代，對應 Step 4 寫入的 LBA)
        └── Step 7.1: READ(10) (28h) — Read + Compare
              → Expected: GOOD Status, Data Match
```

---

## Phase 1 — WriteBooster Configuration

### Step 1.1: 讀取最大 WriteBooster Buffer 分配單元數

**UFS QUERY**: `READ DESCRIPTOR (Opcode 0x07)` — Unit Descriptor

**目的**: 讀取 Unit Descriptor 取得 `dLUNumWriteBoosterBufferAllocUnits`，以確定裝置支援的最大 WB Buffer 大小。

| Field | Value |
|-------|-------|
| Opcode | 0x07 |
| IDN | 0x02 (Unit Descriptor) |
| Selector / Index | 0 (LUN 0) |

**Expected**: QUERY RESPONSE Success（Unit Descriptor 資料回傳成功）

**UFS SPEC Reference**: JESD220H Section 14.2.2 (Unit Descriptor), Section 10.7.8.7 (READ DESCRIPTOR)

---

### Step 1.2: 配置 WriteBooster Buffer 為最大值

**UFS QUERY**: `WRITE DESCRIPTOR (Opcode 0x08)` — Configuration Descriptor

**目的**: 使用 Step 1.1 讀取到的最大分配單元數，寫入 Configuration Descriptor 以設定 WB Buffer 為最大值。

| Field | Value |
|-------|-------|
| Opcode | 0x08 |
| IDN | 0x01 (Configuration Descriptor) |
| bWriteBoosterBufferType | 依裝置支援的類型 (Shared = 0x00 / LUN Dedicated = 0x01) |
| dNumSharedWriteBoosterBufferAllocUnits | Max（來自 Step 1.1 的 dLUNumWriteBoosterBufferAllocUnits） |

**Expected**: QUERY RESPONSE Success

**UFS SPEC Reference**: JESD220H Section 14.2.1 (Configuration Descriptor), Section 10.7.8.8 (WRITE DESCRIPTOR)

> **Note**: `dLUNumWriteBoosterBufferAllocUnits` (IDN 0x17) 為 Read-Only 屬性，無法透過 WRITE ATTRIBUTE 寫入。WB Buffer 大小必須透過 WRITE DESCRIPTOR 設定 Configuration Descriptor。

---

## Phase 2 — Erase All (Pre-condition)

### Step 2.1: UNMAP 整卡 LBA 範圍

**SCSI CMD**: `UNMAP (Opcode 0x42)`

**目的**: 發送 UNMAP 命令以取消映射整張卡的所有 LBA，為後續 Purge 清空做準備。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| ANCHOR | 0 |
| PARAMETER LIST LENGTH | 依 UNMAP block descriptor 結構計算 |
| UNMAP Block Descriptor — LBA | 0x0000000000000000 |
| UNMAP Block Descriptor — LOGICAL BLOCK COUNT | Total Card Capacity (in logical blocks) |

**Expected**: GOOD Status

**UFS SPEC Reference**: JESD220H Section 11.4 (SCSI Commands), SBC-4 Section 5.34 (UNMAP)

---

### Step 2.2: 觸發 Purge 操作

**UFS QUERY**: `SET FLAG (Opcode 0x02)` — fPurgeEnable

**目的**: 設定 fPurgeEnable Flag，觸發裝置執行 Purge 以清空整卡資料。

| Field | Value |
|-------|-------|
| Opcode | 0x02 |
| Flag IDN | 0x06 (fPurgeEnable) |

**Expected**: QUERY RESPONSE Success（Flag 設定成功，Purge 操作啟動）

**UFS SPEC Reference**: JESD220H Section 14.3.1 (Flags, fPurgeEnable), Section 10.7.8.2 (SET FLAG)

---

### Step 2.3: 確認 Purge 完成

**UFS QUERY**: `READ ATTRIBUTE (Opcode 0x03)` — bPurgeStatus

**目的**: 輪詢讀取 bPurgeStatus，確認 Purge 操作已完成（bPurgeStatus 回到 Idle 狀態）。

| Field | Value |
|-------|-------|
| Opcode | 0x03 |
| Attr IDN | 0x14 (bBackgroundOpStatus) |
| Selector / Index | 0 |

**UFS SPEC Reference**: JESD220H Section 14.3.2 (Attributes, bBackgroundOpStatus), Section 10.7.8.3 (READ ATTRIBUTE)

> **Note**: Purge 完成後 bBackgroundOpStatus 回到 0x00 (Idle/No BKOPS active)，可繼續進行後續操作。

---

## Phase 3 — Enable WriteBooster

### Step 3.1: 啟用 WriteBooster

**UFS QUERY**: `SET FLAG (Opcode 0x02)` — fWriteBoosterEn

**目的**: 設定 fWriteBoosterEn Flag 為 1，啟用 WriteBooster 功能。

| Field | Value |
|-------|-------|
| Opcode | 0x02 |
| Flag IDN | 0x0E (fWriteBoosterEn) |

**Expected**: QUERY RESPONSE Success

**UFS SPEC Reference**: JESD220H Section 14.3.1 (Flags, fWriteBoosterEn), Section 10.7.8.2 (SET FLAG)

---

## Phase 4 — Random Non-FUA Write

### Step 4.1: 隨機 Non-FUA 寫入

**SCSI CMD**: `WRITE(10) (Opcode 0x2A)`

**目的**: 執行 5 次隨機 Non-FUA Write，寫入測試資料。每次使用隨機 LBA 與隨機 chunksize，FUA=0 使得寫入資料優先進入 WB Buffer。

**Loop**: 5 次迭代

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0 |
| LBA | Rand(0, Total Card Capacity) |
| TRANSFER LENGTH | 依 chunksize 決定（見下方 Branch Logic） |
| FUA | 0 |
| WRPROTECT | 000b |

**Branch Logic** (per JIRA, 每次隨機選擇):
- Case 1: chunksize = 4K (TRANSFER LENGTH = 8)
- Case 2: chunksize = 16K (TRANSFER LENGTH = 32)
- Case 3: chunksize = 32K (TRANSFER LENGTH = 64)
- Case 4: chunksize = 64K (TRANSFER LENGTH = 128)
- Case 5: chunksize = 128K (TRANSFER LENGTH = 256)
- Case 6: chunksize = 512K (TRANSFER LENGTH = 1024)

**Expected**: GOOD Status（共 5 次 Write，每次均回傳 GOOD Status）

**UFS SPEC Reference**: JESD220H Section 11.4 (SCSI Commands), SBC-4 Section 5.41 (WRITE(10))

> **Note**: 每次寫入的 LBA 與資料 pattern 需記錄下來，供 Phase 7 Read Compare 使用。FUA=0 表示資料可暫存於 WB Buffer，不強制寫入 NAND。

---

## Phase 5 — Auto Standby Verification

### Step 5.1: 閒置等待進入 Auto Standby

**目的**: 讓裝置在閒置 (Idle) 狀態下等待其自動進入 Auto Standby 低功耗模式。透過量測電流來判斷是否已成功進入。

| Parameter | Value |
|-------|-------|
| 操作 | 停止發送命令，裝置進入 Idle 狀態 |
| 監測方式 | 量測電流 |
| 判定條件 | 電流下降至 Auto Standby 等級 |
| 超時判定 | > 5 分鐘未進入 Auto Standby → FAIL |

**Expected**: Enters auto standby within 5 minutes（5 分鐘內進入 Auto Standby，電流符合低功耗規格）

**UFS SPEC Reference**: JESD220H Section 10.8 (Power Management / Auto Standby)

---

## Phase 6 — SPOR (HW Reset)

### Step 6.1: 觸發硬體重置 (HW_RESET)

**操作**: `HW_RESET`

**目的**: 對裝置觸發硬體重置，模擬 Sudden Power-Off Recovery (SPOR) 場景，以驗證 WB Buffer 中的寫入資料是否已正確保存至 NAND。

| Field | Value |
|-------|-------|
| Reset Type | HW_RESET (Hardware Reset) |
| 觸發方式 | 透過 HW RST_n 訊號或等效硬體重置機制 |

**Expected**: Reset device success（裝置重置成功，重新初始化完成）

**UFS SPEC Reference**: JESD220H Section 10.8 (Reset)

---

## Phase 7 — Read Compare (SPOR Data Retention Verification)

### Step 7.1: 讀取比對 SPOR 前的寫入資料

**SCSI CMD**: `READ(10) (Opcode 0x28)`

**目的**: 在 SPOR 後重新讀取 Phase 4 寫入的 5 筆資料，逐一比對確認資料完整保留 (Data Retention)。

**Loop**: 5 次迭代，對應 Phase 4 的 5 次 Write 的 LBA 與 TRANSFER LENGTH

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0 |
| LBA | 對應 Phase 4 Step 4.1 各次寫入的 LBA |
| TRANSFER LENGTH | 對應 Phase 4 Step 4.1 各次寫入的 TRANSFER LENGTH |
| RDPROTECT | 000b |

**Expected**: GOOD Status, Data Match（5 次 Read 均回傳 GOOD Status，且讀取資料與寫入資料完全一致）

**UFS SPEC Reference**: JESD220H Section 11.4 (SCSI Commands), SBC-4 Section 5.17 (READ(10))

> **Note**: Read Compare 需逐一比對每個 sector 的資料。若任何一筆資料比對失敗，則判定為 Data Retention 失敗，代表 WB Buffer 資料未正確寫入 NAND。

---

## 附錄 A — UFS Query IDN 對照表

### Flags

| IDN | Name | Volatile | 使用於 |
|:---|:---|:---|:---|
| 0x06 | fPurgeEnable | Yes | Step 2.2 — 觸發 Purge |
| 0x0E | fWriteBoosterEn | Yes | Step 3.1 — 啟用 WriteBooster |

### Attributes

| IDN | Name | Size | Access | 使用於 |
|:---|:---|:---|:---|:---|
| 0x14 | bBackgroundOpStatus | 1 | Read-Only | Step 2.3 — 確認 Purge 完成狀態 |
| 0x17 | dLUNumWriteBoosterBufferAllocUnits | 4 | **Read-Only** | Step 1.1 — 讀取最大 WB Buffer 分配單元 |

### Descriptors

| IDN | Name | 使用於 |
|:---|:---|:---|
| 0x01 | Configuration Descriptor | Step 1.2 — 寫入 WB Buffer 配置 |
| 0x02 | Unit Descriptor | Step 1.1 — 讀取 WB Buffer 最大分配單元 |

### Query Operations

| Opcode | Name | 使用於 |
|:---|:---|:---|
| 0x02 | SET FLAG | Step 2.2, Step 3.1 |
| 0x03 | READ ATTRIBUTE | Step 2.3 |
| 0x07 | READ DESCRIPTOR | Step 1.1 |
| 0x08 | WRITE DESCRIPTOR | Step 1.2 |

---

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | 使用於 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | Step 7.1 — Read Compare |
| 0x2A | WRITE(10) | 10 | Step 4.1 — Random Non-FUA Write |
| 0x42 | UNMAP | 10 | Step 2.1 — Erase All |

---

## 附錄 C — UFS Reset 類型說明

| Reset 類型 | 使用於 | 說明 |
|:---|:---|:---|
| HW_RESET | Step 6.1 | 硬體重置，透過 RST_n 訊號觸發，模擬 SPOR 場景 |

**UFS SPEC Reference**: JESD220H Section 10.8 (Reset)

---

## 自我驗證

- Tree Diagram leaf steps: **10**（Phase 1: 2 (1.1~1.2), Phase 2: 3 (2.1~2.3), Phase 3: 1 (3.1), Phase 4: 1 (4.1), Phase 5: 1 (5.1), Phase 6: 1 (6.1), Phase 7: 1 (7.1) → Total: 10）
- `### Step` sections: **10** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（9 steps 有 Expected、1 step (2.3) 無 Expected，均與 JIRA 原文對應）
- Expected 可追溯 JIRA 原文對照：
  - Step 1.1/1.2 → JIRA Step 1 "expect device response pass"
  - Step 2.1/2.2 → JIRA Step 2 "expect device response pass"
  - Step 2.3 → 無 Expected（JIRA 未指定 bPurgeStatus 值）
  - Step 3.1 → JIRA Step 3 "expect device response pass"
  - Step 4.1 → JIRA Step 4 "expect device response pass"
  - Step 5.1 → JIRA Step 5 "若超過5分鐘沒進入auto standby判定fail"
  - Step 6.1 → JIRA Step 6 "expect device response pass"
  - Step 7.1 → JIRA Step 7 "expect device response pass"
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
