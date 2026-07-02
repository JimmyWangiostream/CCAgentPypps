---
title: PF002_0077_BootLUN_Read_In_All_Speed-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_0077, scsi-cmd, boot-lun, speed-gear, read-compare]
description: >
  驗證 Boot LUN（Boot_A 與 Boot_B）在所有支援的 UFS 速度檔位（PWM G1~G4、HS G1~G3）
  下的資料讀取正確性。每個 Boot LUN 啟用後，逐一切換速度檔位並執行 READ(10) 讀取
  Boot W-LUN，比對讀回資料與寫入資料是否一致。執行兩輪（Pass 1 & Pass 2）以確保
  重複啟用後的讀取行為一致。
sources:
  - JIRA: PF002_0077 (SYSTCUFS-176)
  - UFS Spec: JESD220H Section 6.2, 10.5, 10.7.8, 11.2.4, 11.2.5, 14.3
---

# PF002_0077 Boot LUN Read In All Speed — Normalized Test Flow

## 測試架構（Tree Diagram）

```
PF002_0077 Test Flow
│
└── Loop (2 passes: Pass 1 & Pass 2)
    ├── Phase 1: 寫入測試資料至 LUN0 與 LUN1
    │   ├── Step 1.1: WRITE(10) — 寫入 LUN0 (Boot_A)
    │   └── Step 1.2: WRITE(10) — 寫入 LUN1 (Boot_B)
    │
    ├── Phase 2: Boot_A — 全速讀取與資料比對
    │   ├── Step 2.1: WRITE ATTRIBUTE — 啟用 Boot_A (bBootLunEn = 0x01)
    │   ├── Step 2.2: READ(10) — Boot_A W-LUN @ PWM G1, Compare
    │   ├── Step 2.3: READ(10) — Boot_A W-LUN @ PWM G2, Compare
    │   ├── Step 2.4: READ(10) — Boot_A W-LUN @ PWM G3, Compare
    │   ├── Step 2.5: READ(10) — Boot_A W-LUN @ PWM G4, Compare
    │   ├── Step 2.6: READ(10) — Boot_A W-LUN @ HS G1, Compare
    │   ├── Step 2.7: READ(10) — Boot_A W-LUN @ HS G2, Compare
    │   └── Step 2.8: READ(10) — Boot_A W-LUN @ HS G3, Compare
    │
    └── Phase 3: Boot_B — 全速讀取與資料比對
        ├── Step 3.1: WRITE ATTRIBUTE — 啟用 Boot_B (bBootLunEn = 0x02)
        ├── Step 3.2: READ(10) — Boot_B W-LUN @ PWM G1, Compare
        ├── Step 3.3: READ(10) — Boot_B W-LUN @ PWM G2, Compare
        ├── Step 3.4: READ(10) — Boot_B W-LUN @ PWM G3, Compare
        ├── Step 3.5: READ(10) — Boot_B W-LUN @ PWM G4, Compare
        ├── Step 3.6: READ(10) — Boot_B W-LUN @ HS G1, Compare
        ├── Step 3.7: READ(10) — Boot_B W-LUN @ HS G2, Compare
        └── Step 3.8: READ(10) — Boot_B W-LUN @ HS G3, Compare
```

> **注意**：若裝置額外支援 PWM G5 或 HS G4（UFS 3.1+），應擴充對應的速度檔位讀取步驟。
> 速度檔位切換為 UniPro PA_PWRMode 操作，非 SCSI CMD 或 UFS Query，於每個 READ Step
> 中作為前置條件執行。

---

## Phase 1 — 寫入測試資料至 LUN0 與 LUN1

> 此 Phase 在每次 Pass 開始時執行。LUN0 與 LUN1 此時處於一般 LUN 模式
> （bBootLunEn = 0x00, Boot Disabled），可正常寫入。寫入完成後再於後續 Phase
> 中將目標 Boot LUN 設為啟用並進行讀取。

### Step 1.1: 寫入測試資料至 LUN0 (Boot_A)

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 寫入已知測試資料至 LUN0，作為後續於 Boot_A 模式下讀取比對的參考資料。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| WRPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 依 LUN 容量決定（至少涵蓋 Boot W-LUN 可讀取範圍） |
| Target LUN | LUN0 (Boot_A) |
| Data Pattern | 測試用已知 pattern（可為遞增序號或固定 seed 的 pseudo-random） |

**UFS SPEC Reference**: JESD220H Section 11.2.5 (WRITE(10) command)

---

### Step 1.2: 寫入測試資料至 LUN1 (Boot_B)

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 寫入已知測試資料至 LUN1，作為後續於 Boot_B 模式下讀取比對的參考資料。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| WRPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 依 LUN 容量決定（至少涵蓋 Boot W-LUN 可讀取範圍） |
| Target LUN | LUN1 (Boot_B) |
| Data Pattern | 測試用已知 pattern（可為遞增序號或固定 seed 的 pseudo-random） |

**UFS SPEC Reference**: JESD220H Section 11.2.5 (WRITE(10) command)

---

## Phase 2 — Boot_A 全速讀取與資料比對

> 啟用 Boot_A 後，Boot W-LUN 會映射至 Boot_A LU（原 LUN0）。本 Phase 逐一將
> UFS 連結速度切換至每個支援的檔位，並在該檔位下執行 READ(10) 比對資料。
> 速度檔位切換透過 UniPro DME PA_PWRMode 設定完成。

### Step 2.1: 啟用 Boot_A

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bBootLunEn (IDN 0x00)

**目的**: 設定 bBootLunEn 為 0x01，使 Boot W-LUN 映射至 Boot_A LU（LUN0），
後續可透過 Boot W-LUN 讀取 Boot_A 的開機資料。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| Attr IDN | 0x00 (bBootLunEn) |
| Attr Value | 0x01 (Boot_A Enabled) |
| Attr Size | 1 byte |
| Target LUN | Device-level (0) |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn)

---

### Step 2.2: 讀取 Boot_A W-LUN — PWM Gear 1

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 PWM Gear 1 速度下，從 Boot W-LUN 讀取 Boot_A 的資料，並與 Step 1.1
寫入的參考資料進行比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.1 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | PWM Gear 1 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → PWM Gear 1 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command), Section 6.2 (PWM Gears), Section 10.5 (UniPro Power Mode)

---

### Step 2.3: 讀取 Boot_A W-LUN — PWM Gear 2

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 PWM Gear 2 速度下，從 Boot W-LUN 讀取 Boot_A 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.1 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | PWM Gear 2 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → PWM Gear 2 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 2.4: 讀取 Boot_A W-LUN — PWM Gear 3

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 PWM Gear 3 速度下，從 Boot W-LUN 讀取 Boot_A 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.1 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | PWM Gear 3 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → PWM Gear 3 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 2.5: 讀取 Boot_A W-LUN — PWM Gear 4

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 PWM Gear 4 速度下，從 Boot W-LUN 讀取 Boot_A 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.1 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | PWM Gear 4 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → PWM Gear 4 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 2.6: 讀取 Boot_A W-LUN — HS Gear 1

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 HS Gear 1 速度下，從 Boot W-LUN 讀取 Boot_A 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.1 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | HS Gear 1 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → HS Gear 1 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2 (HS Gears), Section 10.5

---

### Step 2.7: 讀取 Boot_A W-LUN — HS Gear 2

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 HS Gear 2 速度下，從 Boot W-LUN 讀取 Boot_A 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.1 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | HS Gear 2 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → HS Gear 2 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 2.8: 讀取 Boot_A W-LUN — HS Gear 3

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 HS Gear 3 速度下，從 Boot W-LUN 讀取 Boot_A 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.1 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | HS Gear 3 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → HS Gear 3 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

## Phase 3 — Boot_B 全速讀取與資料比對

> 啟用 Boot_B 後，Boot W-LUN 會映射至 Boot_B LU（原 LUN1）。本 Phase 逐一將
> UFS 連結速度切換至每個支援的檔位，並在該檔位下執行 READ(10) 比對資料。
> 速度檔位切換透過 UniPro DME PA_PWRMode 設定完成。

### Step 3.1: 啟用 Boot_B

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bBootLunEn (IDN 0x00)

**目的**: 設定 bBootLunEn 為 0x02，使 Boot W-LUN 映射至 Boot_B LU（LUN1），
後續可透過 Boot W-LUN 讀取 Boot_B 的開機資料。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| Attr IDN | 0x00 (bBootLunEn) |
| Attr Value | 0x02 (Boot_B Enabled) |
| Attr Size | 1 byte |
| Target LUN | Device-level (0) |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn)

---

### Step 3.2: 讀取 Boot_B W-LUN — PWM Gear 1

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 PWM Gear 1 速度下，從 Boot W-LUN 讀取 Boot_B 的資料，並與 Step 1.2
寫入的參考資料進行比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.2 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | PWM Gear 1 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → PWM Gear 1 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 3.3: 讀取 Boot_B W-LUN — PWM Gear 2

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 PWM Gear 2 速度下，從 Boot W-LUN 讀取 Boot_B 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.2 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | PWM Gear 2 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → PWM Gear 2 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 3.4: 讀取 Boot_B W-LUN — PWM Gear 3

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 PWM Gear 3 速度下，從 Boot W-LUN 讀取 Boot_B 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.2 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | PWM Gear 3 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → PWM Gear 3 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 3.5: 讀取 Boot_B W-LUN — PWM Gear 4

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 PWM Gear 4 速度下，從 Boot W-LUN 讀取 Boot_B 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.2 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | PWM Gear 4 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → PWM Gear 4 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 3.6: 讀取 Boot_B W-LUN — HS Gear 1

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 HS Gear 1 速度下，從 Boot W-LUN 讀取 Boot_B 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.2 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | HS Gear 1 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → HS Gear 1 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 3.7: 讀取 Boot_B W-LUN — HS Gear 2

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 HS Gear 2 速度下，從 Boot W-LUN 讀取 Boot_B 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.2 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | HS Gear 2 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → HS Gear 2 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

### Step 3.8: 讀取 Boot_B W-LUN — HS Gear 3

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 HS Gear 3 速度下，從 Boot W-LUN 讀取 Boot_B 的資料，並與參考資料比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 與 Step 1.2 寫入範圍一致 |
| Target LUN | Boot W-LUN |
| Speed Gear | HS Gear 3 |
| Post-Read | 比對讀回資料與參考資料 |

**速度前置條件**: UniPro PA_PWRMode → HS Gear 3 (UniPro DME_SET)

**UFS SPEC Reference**: JESD220H Section 11.2.4, Section 6.2, Section 10.5

---

## 附錄 A — UFS Query IDN 對照表

| Query Opcode | Name | IDN | Attr Name | Access | Size | Used In |
|:---|:---|:---|:---|:---|:---|:---|
| 0x04 | WRITE ATTRIBUTE | 0x00 | bBootLunEn | Read-Write | 1 byte | Step 2.1, 3.1 |

### bBootLunEn 值定義

| Value | Meaning |
|:---|:---|
| 0x00 | Boot Disabled |
| 0x01 | Boot_A Enabled |
| 0x02 | Boot_B Enabled |

---

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | Use | Used In |
|:---|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | Read data from Boot W-LUN | Step 2.2~2.8, 3.2~3.8 |
| 0x2A | WRITE(10) | 10 | Write test data to LUN0/LUN1 | Step 1.1, 1.2 |

---

## 附錄 C — UFS Speed Gear 說明

| Gear | Series | Lane Rate | Used In |
|:---|:---|:---|:---|
| PWM G1 | PWM | Slowest | Step 2.2, 3.2 |
| PWM G2 | PWM | — | Step 2.3, 3.3 |
| PWM G3 | PWM | — | Step 2.4, 3.4 |
| PWM G4 | PWM | — | Step 2.5, 3.5 |
| HS G1 | HS (A/B) | — | Step 2.6, 3.6 |
| HS G2 | HS (A/B) | — | Step 2.7, 3.7 |
| HS G3 | HS (A/B) | — | Step 2.8, 3.8 |

> **Optional Gears** (device-dependent): PWM G5, HS G4 (UFS 3.1+).
> 實作時應查詢裝置支援的速度檔位清單，僅對實際支援的檔位執行讀取比對。

**UFS SPEC Reference**: JESD220H Section 6.2 (PWM Gears & HS Gears), Section 10.5 (UniPro Power Mode Change)

---

## 自我驗證

- Tree Diagram leaf steps: **18**（Phase 1: 2 (1.1~1.2), Phase 2: 8 (2.1~2.8), Phase 3: 8 (3.1~3.8) → Total: 18）
- `### Step` sections: **18** ✓
- `→ Expected:` 在此 Pattern 中數量：**0**（原始 JIRA Pattern 未明確描述任何步驟的預期結果，因此不填入 Expected）✓
- 無憑空生成的 Expected 值 ✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
