---
title: PF002_0075_BootLUN_Read_Boundary_OutOfRange_Test-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_0075, scsi-cmd, boot-lun, boundary-read, out-of-range]
description: >
  驗證 Boot LUN 啟用後，對 Boot W-LUN 進行邊界讀取操作的正確性：
  包含最後一個有效 LBA、倒數第二個 LBA、無效 LBA 單區塊讀取、
  無效 LBA 零長度讀取、以及從有效 LBA 跨越至無效範圍的邊界讀取。
  測試涵蓋 Boot_A 與 Boot_B 兩個 Boot LUN，並執行兩輪（Pass 1 & Pass 2）
  以確保重複啟用後的邊界行為一致。
sources:
  - JIRA: PF002_0075 (SYSTCUFS-230)
  - UFS Spec: JESD220H Section 10.7.8, 11.2.4, 11.2.5, 14.3
---

# PF002_0075 Boot LUN Read Boundary Out-Of-Range Test — Normalized Test Flow

## 測試架構（Tree Diagram）

```
PF002_0075 Test Flow
│
└── Loop (2 passes: Pass 1 & Pass 2)
    ├── Phase 1: 寫入測試資料至 LUN0 與 LUN1
    │   ├── Step 1.1: WRITE(10) — 寫入 LUN0 (Boot_A)
    │   └── Step 1.2: WRITE(10) — 寫入 LUN1 (Boot_B)
    │
    ├── Phase 2: Boot_A 邊界讀取測試
    │   ├── Step 2.1: WRITE ATTRIBUTE — 啟用 Boot_A (bBootLunEn = 1, LUN0)
    │   ├── Step 2.2: READ(10) — Boot_A W-LUN 最後一個有效 LBA
    │   ├── Step 2.3: READ(10) — Boot_A W-LUN 倒數第二個有效 LBA
    │   ├── Step 2.4: READ(10) — Boot_A W-LUN 無效 LBA, Transfer Length = 1
    │   ├── Step 2.5: READ(10) — Boot_A W-LUN 無效 LBA, Transfer Length = 0
    │   └── Step 2.6: READ(10) — Boot_A W-LUN 有效 LBA 跨越至無效範圍
    │
    └── Phase 3: Boot_B 邊界讀取測試
        ├── Step 3.1: WRITE ATTRIBUTE — 啟用 Boot_B (bBootLunEn = 1, LUN1)
        ├── Step 3.2: READ(10) — Boot_B W-LUN 最後一個有效 LBA
        ├── Step 3.3: READ(10) — Boot_B W-LUN 倒數第二個有效 LBA
        ├── Step 3.4: READ(10) — Boot_B W-LUN 無效 LBA, Transfer Length = 1
        ├── Step 3.5: READ(10) — Boot_B W-LUN 無效 LBA, Transfer Length = 0
        └── Step 3.6: READ(10) — Boot_B W-LUN 有效 LBA 跨越至無效範圍
```

---

## Phase 1 — 寫入測試資料至 LUN0 與 LUN1

> 此 Phase 在每次 Pass 開始時執行。LUN0 與 LUN1 此時處於一般 LUN 模式
> （bBootLunEn = 0），可正常寫入。寫入完成後再將目標 Boot LUN 設為啟用。

### Step 1.1: 寫入測試資料至 LUN0 (Boot_A)

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 在 Boot LUN 模式下讀取之前，先將已知測試資料寫入 LUN0（後續將作為 Boot_A W-LUN 讀取）。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| WRPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 依 LUN 容量決定（至少涵蓋邊界測試所需範圍） |
| Target LUN | LUN0 (Boot_A) |
| Data Pattern | 測試用已知 pattern |

**UFS SPEC Reference**: JESD220H Section 11.2.5 (WRITE(10) command)

---

### Step 1.2: 寫入測試資料至 LUN1 (Boot_B)

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 在 Boot LUN 模式下讀取之前，先將已知測試資料寫入 LUN1（後續將作為 Boot_B W-LUN 讀取）。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| WRPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 |
| Group Number | 0x00 |
| Transfer Length | 依 LUN 容量決定（至少涵蓋邊界測試所需範圍） |
| Target LUN | LUN1 (Boot_B) |
| Data Pattern | 測試用已知 pattern |

**UFS SPEC Reference**: JESD220H Section 11.2.5 (WRITE(10) command)

---

## Phase 2 — Boot_A 邊界讀取測試

> 啟用 Boot_A 後，透過 Boot A W-LUN 對其進行多種邊界讀取測試。
> Boot LUN 容量資訊需事先透過 READ CAPACITY(10) 取得（隱含前置步驟）。

### Step 2.1: 啟用 Boot_A — 設定 bBootLunEn = 1

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bBootLunEn (IDN 0x00)

**目的**: 將 LUN0 設為 Boot LUN 模式，使其可透過 Boot A W-LUN 存取。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Index | 0x00 (LUN0 / Boot_A) |
| Selector | 0x00 |
| Value | 0x01 (Boot LUN enabled) |
| Size | 1 byte |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn Attribute)

---

### Step 2.2: 讀取 Boot_A W-LUN 最後一個有效 LBA

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證 Boot_A W-LUN 最後一個有效 LBA（capacity - 1）可正常讀取。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_a_capacity - 1`（最後一個有效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0001（1 block） |
| Target LUN | Boot A W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

### Step 2.3: 讀取 Boot_A W-LUN 倒數第二個有效 LBA

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證 Boot_A W-LUN 倒數第二個有效 LBA（capacity - 2）可正常讀取。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_a_capacity - 2`（倒數第二個有效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0001（1 block） |
| Target LUN | Boot A W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

### Step 2.4: 讀取 Boot_A W-LUN 無效 LBA（Transfer Length = 1）

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證對 Boot_A W-LUN 的第一個無效 LBA（LBA = capacity）發送長度為 1 的讀取請求時，裝置的行為。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_a_capacity`（第一個無效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0001（1 block，超出容量範圍） |
| Target LUN | Boot A W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

### Step 2.5: 讀取 Boot_A W-LUN 無效 LBA（Transfer Length = 0）

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證對 Boot_A W-LUN 的無效 LBA 發送零長度讀取請求時，裝置的行為（邊界條件：LBA 本身無效但未請求實際資料傳輸）。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_a_capacity`（無效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0000（0 blocks） |
| Target LUN | Boot A W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

### Step 2.6: 讀取 Boot_A W-LUN — 有效 LBA 跨越至無效範圍

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證從 Boot_A W-LUN 的最後一個有效 LBA 開始讀取，但 Transfer Length 超出容量範圍時，裝置的邊界處理行為。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_a_capacity - 1`（最後一個有效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0002（2 blocks，跨越容量邊界） |
| Target LUN | Boot A W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

## Phase 3 — Boot_B 邊界讀取測試

> 啟用 Boot_B 後，透過 Boot B W-LUN 對其進行與 Boot_A 相同的邊界讀取測試。
> 兩個 Boot LUN 的讀取測試內容完全對稱，確保邊界行為在不同 Boot LUN 間一致。

### Step 3.1: 啟用 Boot_B — 設定 bBootLunEn = 1

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bBootLunEn (IDN 0x00)

**目的**: 將 LUN1 設為 Boot LUN 模式，使其可透過 Boot B W-LUN 存取。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Index | 0x01 (LUN1 / Boot_B) |
| Selector | 0x00 |
| Value | 0x01 (Boot LUN enabled) |
| Size | 1 byte |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn Attribute)

---

### Step 3.2: 讀取 Boot_B W-LUN 最後一個有效 LBA

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證 Boot_B W-LUN 最後一個有效 LBA（capacity - 1）可正常讀取。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_b_capacity - 1`（最後一個有效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0001（1 block） |
| Target LUN | Boot B W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

### Step 3.3: 讀取 Boot_B W-LUN 倒數第二個有效 LBA

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證 Boot_B W-LUN 倒數第二個有效 LBA（capacity - 2）可正常讀取。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_b_capacity - 2`（倒數第二個有效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0001（1 block） |
| Target LUN | Boot B W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

### Step 3.4: 讀取 Boot_B W-LUN 無效 LBA（Transfer Length = 1）

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證對 Boot_B W-LUN 的第一個無效 LBA（LBA = capacity）發送長度為 1 的讀取請求時，裝置的行為。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_b_capacity`（第一個無效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0001（1 block，超出容量範圍） |
| Target LUN | Boot B W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

### Step 3.5: 讀取 Boot_B W-LUN 無效 LBA（Transfer Length = 0）

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證對 Boot_B W-LUN 的無效 LBA 發送零長度讀取請求時，裝置的行為（邊界條件：LBA 本身無效但未請求實際資料傳輸）。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_b_capacity`（無效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0000（0 blocks） |
| Target LUN | Boot B W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

### Step 3.6: 讀取 Boot_B W-LUN — 有效 LBA 跨越至無效範圍

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 驗證從 Boot_B W-LUN 的最後一個有效 LBA 開始讀取，但 Transfer Length 超出容量範圍時，裝置的邊界處理行為。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | `boot_b_capacity - 1`（最後一個有效 LBA） |
| Group Number | 0x00 |
| Transfer Length | 0x0002（2 blocks，跨越容量邊界） |
| Target LUN | Boot B W-LUN |

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

## 附錄 A — UFS Query IDN 對照表

| Query Opcode | Name | IDN | Target | Description |
|:---|:---|:---|:---|:---|
| 0x04 | WRITE ATTRIBUTE | 0x00 | bBootLunEn | Boot Logical Unit enable (1 byte, Read-Write, per-LUN via Index) |

---

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | Use in This Pattern |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | 對 Boot W-LUN 進行邊界讀取（有效/無效/跨越邊界） |
| 0x2A | WRITE(10) | 10 | 寫入測試資料至 LUN0 (Boot_A) 與 LUN1 (Boot_B) |

### READ(10) CDB Layout

| Byte | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| 0 | Opcode = 0x28 |
| 1 | RDPROTECT[2:0] | DPO | FUA | Reserved | FUA_NV | Obsolete[0] |
| 2–5 | Logical Block Address (MSB first) |
| 6 | Reserved (Group Number) |
| 7–8 | Transfer Length (MSB first) |
| 9 | Control |

### WRITE(10) CDB Layout

| Byte | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| 0 | Opcode = 0x2A |
| 1 | WRPROTECT[2:0] | DPO | FUA | Reserved | FUA_NV | Obsolete[0] |
| 2–5 | Logical Block Address (MSB first) |
| 6 | Reserved (Group Number) |
| 7–8 | Transfer Length (MSB first) |
| 9 | Control |

---

## 附錄 C — Boot LUN 邊界讀取測試情境摘要

| JIRA Step | Normalized Step | 情境 | LBA | Transfer Length | 說明 |
|:---|:---|:---|:---|:---|:---|
| 3, 16 | 2.2 | 最後一個有效 LBA | capacity − 1 | 1 | 邊界內單區塊讀取 |
| 4, 17 | 2.3 | 倒數第二個有效 LBA | capacity − 2 | 1 | 邊界內正常讀取 |
| 5, 18 | 2.4 | 無效 LBA, len=1 | capacity | 1 | LBA 超出範圍，有資料請求 |
| 6, 19 | 2.5 | 無效 LBA, len=0 | capacity | 0 | LBA 超出範圍，無資料請求 |
| 7, 20 | 2.6 | 有效→無效跨越 | capacity − 1 | 2 | 從有效 LBA 開始跨越容量邊界 |
| 9, 22 | 3.2 | (Boot_B 對稱) | capacity − 1 | 1 | 同 Step 2.2，Boot_B |
| 10, 23 | 3.3 | (Boot_B 對稱) | capacity − 2 | 1 | 同 Step 2.3，Boot_B |
| 11, 24 | 3.4 | (Boot_B 對稱) | capacity | 1 | 同 Step 2.4，Boot_B |
| 12, 25 | 3.5 | (Boot_B 對稱) | capacity | 0 | 同 Step 2.5，Boot_B |
| 13, 26 | 3.6 | (Boot_B 對稱) | capacity − 1 | 2 | 同 Step 2.6，Boot_B |

---

## 自我驗證

- Tree Diagram leaf steps: **14**
  Phase 1: 2 (1.1~1.2), Phase 2: 6 (2.1~2.6), Phase 3: 6 (3.1~3.6) → Total: 14
- `### Step` sections: **14** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（0 steps with Expected — JIRA 未描述任何步驟的預期結果）
- 無憑空生成的 Expected 值 ✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
