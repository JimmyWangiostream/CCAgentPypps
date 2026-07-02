---
title: PF010_0310_Write-Booster-SSU-Rst-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf010_0310, scsi-cmd, write-booster, ssu, por, reset]
description: >
  驗證 Write Booster 啟用／退出期間，搭配隨機 Write/Read 與 Data Compare，
  在 SSU (START STOP UNIT) 及所有 Reset (POR) 場景下的穩定性。
  Phase 0 檢查 WB 支援並設定 Shared Buffer（最大配置），
  Phase 1–3 在 Loop 中循環：啟用 WB → W/R → POR；
  退出 WB → W/R → POR；Flush Flag + 隨機延遲 + SSU/POR。
sources:
  - JIRA: PF010_0310 (SYSTCUFS-15)
  - UFS Spec: JESD220H Section 10.7.8, 10.7.9, 14.1.4, 14.2, 14.3
---

# PF010_0310 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 Write Booster 功能在啟用／退出兩種模式下，經歷隨機 Write/Read 與 Data Compare 後，
搭配 SSU (START STOP UNIT) 與 POR 重置的穩定性，並在長時間燒機迴圈（Loop）中重複執行。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | Config 最大Support size Write Booster Buff（Flow 1: Check Support WB, Flow 2: Config WB Buf to Share type） | Phase 0 |
| Step 2 | Write Booster enable during W/R compare data period with SSU + all reset（Flow 3: Set fWriteBoosterEn, Flow 4: W/R + Compare, Flow 5: POR） | Phase 1 |
| Step 3 | Exit Write Booster during W/R compare data period with SSU + all reset（Flow 7: Clear fWriteBoosterEn, Flow 8: W/R + Compare, Flow 9: POR） | Phase 2 |
| Step 4 | flushEnable並作相對應的動作且隨機搭配SSU + all reset（Flow 10-1: 50% FlushEn, Flow 10-2: 50% FlushDuringHibernate, Flow 11-1: Rand delay + POR, Flow 11-2: SSU/Hibernate + POR） | Phase 3 |
| Loop | Loop Step 2 to step 4 | Loop（Phase 1 → Phase 2 → Phase 3） |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF010_0310 Test Flow
│
├── Phase 0: Pre-condition — Write Booster Buffer Configuration
│   ├── Step 0.1: READ DESCRIPTOR (Device) — Check Write Booster support capability
│   └── Step 0.2: WRITE DESCRIPTOR (Configuration) — Configure Shared WB buffer, max allocation size
│
└── Loop (burn_in_loop iterations)
    │
    ├── Phase 1: Write Booster Enable — Random W/R + POR
    │   ├── Step 1.1: SET FLAG(fWriteBoosterEn) — Enable Write Booster
    │   ├── Step 1.2: WRITE(10) — Random Write (WB enabled)
    │   ├── Step 1.3: READ(10) — Random Read + Data Compare
    │   └── Step 1.4: POR device → Expected: Reset device success
    │
    ├── Phase 2: Write Booster Exit — Random W/R + POR
    │   ├── Step 2.1: CLEAR FLAG(fWriteBoosterEn) — Disable Write Booster
    │   ├── Step 2.2: WRITE(10) — Random Write (WB disabled)
    │   ├── Step 2.3: READ(10) — Random Read + Data Compare
    │   └── Step 2.4: POR device → Expected: Reset device success
    │
    └── Phase 3: Flush Enable + Reset Scenarios
        ├── Step 3.1: SET FLAG — FlushEn (50%) or FlushDuringHibernate (50%)
        ├── Step 3.2: Random delay 0~2s
        ├── Step 3.3: POR device → Expected: Reset device success
        ├── Step 3.4: START STOP UNIT — Enter Sleep mode
        └── Step 3.5: POR device → Expected: Reset device success
```

---

## Phase 0 — Pre-condition: Write Booster Buffer Configuration

### Step 0.1: 檢查 Write Booster 支援能力

**UFS QUERY**: `READ DESCRIPTOR (0x07)` — Device Descriptor (IDN 0x00)

**目的**: 讀取 Device Descriptor，確認裝置是否支援 Write Booster 功能，並取得最大 Buffer 配置能力資訊。

| Field | Value |
|-------|-------|
| Opcode (Query) | 0x07 (READ DESCRIPTOR) |
| IDN | 0x00 (Device Descriptor) |
| Selector | 0x00 |
| Index | 0x00 |
| Length | Descriptor 實際長度（依 bLength 而定） |

**UFS SPEC Reference**: JESD220H Section 10.7.9 (READ DESCRIPTOR), Section 14.1.1 (Device Descriptor)

---

### Step 0.2: 設定 Write Booster Buffer 為 Shared 類型（最大配置）

**UFS QUERY**: `WRITE DESCRIPTOR (0x08)` — Configuration Descriptor (IDN 0x01)

**目的**: 將 Write Booster Buffer 設定為 Shared 類型（所有 LU 共享），並配置最大支援的 Buffer Allocation Units 數量。

| Field | Value |
|-------|-------|
| Opcode (Query) | 0x08 (WRITE DESCRIPTOR) |
| IDN | 0x01 (Configuration Descriptor) |
| Selector | 0x00 |
| Index | 0x00 |
| bWriteBoosterBufferType | 0x01 (Shared) |
| dSharedWriteBoosterBufferAllocUnits | 最大支援值（依 Step 0.1 讀取結果） |
| Length | 依實際 Configuration Descriptor 總長度 |

**UFS SPEC Reference**: JESD220H Section 10.7.9 (WRITE DESCRIPTOR), Section 14.1.4 (Configuration Descriptor)

---

## Phase 1 — Write Booster Enable: Random W/R + POR

### Step 1.1: 啟用 Write Booster

**UFS QUERY**: `SET FLAG (0x02)` — fWriteBoosterEn (IDN 0x0E)

**目的**: 設定 fWriteBoosterEn Flag，啟用 Write Booster 功能，使後續寫入操作使用 WB Buffer。

| Field | Value |
|-------|-------|
| Opcode (Query) | 0x02 (SET FLAG) |
| bFlagIDN | 0x0E (fWriteBoosterEn) |
| LUN | 0x00 |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (SET FLAG), Section 14.2 (Flags)

---

### Step 1.2: 隨機寫入（Write Booster 啟用中）

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 在 Write Booster 啟用狀態下，對隨機 LBA 執行寫入操作，資料經由 WB Buffer。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | 隨機（依 Test LBA Range） |
| Transfer Length | 隨機區塊數（依測試設計） |
| Data | 隨機 Pattern |

**UFS SPEC Reference**: JESD220H Section 12.2.3 (WRITE(10)), SBC-4 Section 5.27

---

### Step 1.3: 隨機讀取與資料比對

**SCSI CMD**: `READ(10) (28h)`

**目的**: 讀回 Step 1.2 寫入的 LBA，比對資料正確性（Data Compare），驗證 WB Buffer 中的資料可正確讀取。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | 與 Step 1.2 寫入的 LBA 相同 |
| Transfer Length | 與 Step 1.2 寫入長度相同 |

**UFS SPEC Reference**: JESD220H Section 12.2.2 (READ(10)), SBC-4 Section 5.17

---

### Step 1.4: POR（Power On Reset）

**操作**: `Power On Reset`

**目的**: 對裝置執行 Power On Reset，驗證 WB 啟用狀態下經過 POR 後的穩定性。

| Field | Value |
|-------|-------|
| Reset Type | POR (Power On Reset) |
| 後續 | 等待裝置就緒（fDeviceInit == 0） |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 10.7.1.1 (Power On Reset)

---

## Phase 2 — Write Booster Exit: Random W/R + POR

### Step 2.1: 關閉 Write Booster

**UFS QUERY**: `CLEAR FLAG (0x05)` — fWriteBoosterEn (IDN 0x0E)

**目的**: 清除 fWriteBoosterEn Flag，退出 Write Booster 模式，使後續寫入不再使用 WB Buffer。

| Field | Value |
|-------|-------|
| Opcode (Query) | 0x05 (CLEAR FLAG) |
| bFlagIDN | 0x0E (fWriteBoosterEn) |
| LUN | 0x00 |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (CLEAR FLAG), Section 14.2 (Flags)

---

### Step 2.2: 隨機寫入（Write Booster 已退出）

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 在 Write Booster 已退出的狀態下，對隨機 LBA 執行寫入操作，資料直接寫入 NAND。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | 隨機（依 Test LBA Range） |
| Transfer Length | 隨機區塊數（依測試設計） |
| Data | 隨機 Pattern |

**UFS SPEC Reference**: JESD220H Section 12.2.3 (WRITE(10)), SBC-4 Section 5.27

---

### Step 2.3: 隨機讀取與資料比對

**SCSI CMD**: `READ(10) (28h)`

**目的**: 讀回 Step 2.2 寫入的 LBA，比對資料正確性（Data Compare），驗證 WB 退出後寫入的資料正確。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | 與 Step 2.2 寫入的 LBA 相同 |
| Transfer Length | 與 Step 2.2 寫入長度相同 |

**UFS SPEC Reference**: JESD220H Section 12.2.2 (READ(10)), SBC-4 Section 5.17

---

### Step 2.4: POR（Power On Reset）

**操作**: `Power On Reset`

**目的**: 對裝置執行 Power On Reset，驗證 WB 退出後經過 POR 的穩定性。

| Field | Value |
|-------|-------|
| Reset Type | POR (Power On Reset) |
| 後續 | 等待裝置就緒（fDeviceInit == 0） |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 10.7.1.1 (Power On Reset)

---

## Phase 3 — Flush Enable + Reset Scenarios

### Step 3.1: 設定 Flush Flag（隨機選擇）

**UFS QUERY**: `SET FLAG (0x02)` — 分支選擇

**目的**: 依 50%/50% 機率隨機選擇設定 fWriteBoosterBufferFlushEn 或 fWriteBoosterBufferFlushDuringHibernate，為後續 Reset 場景建立前置條件。

| Field | Value |
|-------|-------|
| Opcode (Query) | 0x02 (SET FLAG) |
| bFlagIDN | **Branch 1 (50%)**: 0x0F (fWriteBoosterBufferFlushEn) |
| | **Branch 2 (50%)**: 0x10 (fWriteBoosterBufferFlushDuringHibernate) |
| LUN | 0x00 |

**Branch Logic** (per JIRA weighted random):
- 50%: SET FLAG fWriteBoosterBufferFlushEn (0x0F) — Enable WB buffer flush
- 50%: SET FLAG fWriteBoosterBufferFlushDuringHibernate (0x10) — Enable flush during Hibernate

**UFS SPEC Reference**: JESD220H Section 10.7.8 (SET FLAG), Section 14.2 (Flags)

---

### Step 3.2: 隨機延遲

**操作**: `Delay`

**目的**: 等待一段隨機延遲時間（0~2 秒），模擬實際使用場景中的非同步事件間隔，觸發 WB Buffer Flush 行為。

| Field | Value |
|-------|-------|
| Delay Range | 0 ~ 2 秒（均勻隨機） |

**UFS SPEC Reference**: N/A（純延遲操作，無 SPEC 參照）

---

### Step 3.3: POR（Power On Reset）

**操作**: `Power On Reset`

**目的**: 在 Flush Flag 設定後執行 POR，驗證 WB Buffer Flush 機制在 POR 下的行為。

| Field | Value |
|-------|-------|
| Reset Type | POR (Power On Reset) |
| 後續 | 等待裝置就緒（fDeviceInit == 0） |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 10.7.1.1 (Power On Reset)

---

### Step 3.4: START STOP UNIT — 進入 Sleep 模式

**SCSI CMD**: `START STOP UNIT (1Bh)`

**目的**: 將裝置轉入 Sleep 低功耗模式，模擬 Hibernate/SSU 場景後再進行 POR。

| Field | Value |
|-------|-------|
| Opcode | 0x1B |
| START | 0 (Stop) |
| Power Condition | 0x02 (Sleep) |
| IMMED | 0x00 |

**UFS SPEC Reference**: JESD220H Section 12.2.8 (START STOP UNIT), SBC-4 Section 5.22

---

### Step 3.5: POR（Power On Reset）

**操作**: `Power On Reset`

**目的**: 從 Sleep 狀態執行 POR，驗證 WB Buffer Flush 在 Sleep → POR 路徑下的穩定性。

| Field | Value |
|-------|-------|
| Reset Type | POR (Power On Reset) |
| 後續 | 等待裝置就緒（fDeviceInit == 0） |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 10.7.1.1 (Power On Reset)

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x02 | SET FLAG | 設定 fWriteBoosterEn / fWriteBoosterBufferFlushEn / fWriteBoosterBufferFlushDuringHibernate |
| 0x05 | CLEAR FLAG | 清除 fWriteBoosterEn |
| 0x07 | READ DESCRIPTOR | 讀取 Device Descriptor（檢查 WB 支援能力） |
| 0x08 | WRITE DESCRIPTOR | 寫入 Configuration Descriptor（設定 Shared WB Buffer） |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x0E | fWriteBoosterEn | Volatile (Set/Clear) | Phase 1 啟用 WB；Phase 2 退出 WB |
| 0x0F | fWriteBoosterBufferFlushEn | Volatile (Set/Clear) | Phase 3 Branch 1 — 啟用 Buffer Flush |
| 0x10 | fWriteBoosterBufferFlushDuringHibernate | Volatile (Set/Clear) | Phase 3 Branch 2 — 啟用 Hibernate 期間 Flush |

### Descriptor IDN

| IDN | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x00 | Device Descriptor | Phase 0 — 讀取 WB 支援能力與最大 Buffer 配置 |
| 0x01 | Configuration Descriptor | Phase 0 — 設定 Shared WB Buffer 類型與大小 |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | Phase 1/2 — 讀取並比對寫入資料 |
| 0x2A | WRITE(10) | 10 | Phase 1/2 — 隨機寫入測試資料 |
| 0x1B | START STOP UNIT | 6 | Phase 3 — 將裝置轉入 Sleep 模式 |

---

## 附錄 C — 本 Pattern 使用的 UFS Reset 類型

| Reset 類型 | 縮寫 | 本 Pattern 用途 | SPEC Reference |
|:---|:---|:---|:---|
| Power On Reset | POR | Phase 1/2/3 — 驗證 WB 各階段重啟後穩定性 | JESD220H Section 10.7.1.1 |

---

## 自我驗證

- Tree Diagram leaf steps: **15**（Phase 0: 2 (0.1~0.2), Phase 1: 4 (1.1~1.4), Phase 2: 4 (2.1~2.4), Phase 3: 5 (3.1~3.5) → Total: 15）
- `### Step` sections: **15** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（含 Expected 的 step: 4 — Step 1.4, 2.4, 3.3, 3.5；均為 POR Reset steps，對應 JIRA 中的 "POR device" 操作。Reset 類型依使用者記憶規則統一使用 "Reset device success"）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文或使用者記憶中的 Reset 規則）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
