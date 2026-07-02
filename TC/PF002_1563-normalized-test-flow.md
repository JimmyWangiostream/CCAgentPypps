---
title: PF002_1563_D_Boot_Lun_Different_AU_Memory_Type-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_1563, scsi-cmd, boot-lun, au-size, memory-type]
description: >
  驗證 Boot LUN 在不同 AU (Allocation Unit) 大小與 Memory Type 配置下的正確性。
  測試涵蓋多個 VC (Validation Case) 場景：基礎配置、錯誤配置（VC-6 & VC-13）、
  多 AU 大小寫入比對（VC1~13）、Boot LUN 啟用後配置（VC-15）、Bug 回歸驗證、
  以及隨機化配置壓測。每個配置階段後寫入全部 LUN 並讀取比對確認資料完整性。
sources:
  - JIRA: PF002_1563 (SYSTCUFS-1838)
  - UFS Spec: JESD220H Section 14.2.2 (Configuration Descriptor), Section 14.2.3 (Unit Descriptor), Section 14.2.5 (Geometry Descriptor), Section 14.3 (bBootLunEn)
---

# PF002_1563_D_Boot_Lun_Different_AU_Memory_Type — 正規化測試流程

## 測試目標

驗證 UFS 裝置在不同 AU 大小及 Memory Type 配置下，Boot LUN 的正確行為。測試透過多個
VC 場景（VC1~15）覆蓋：基礎 Boot LUN 配置、錯誤配置邊界條件、多種 AU 大小寫入讀取比對、
Boot LUN 啟用後的配置、Bug 回歸案例及隨機化配置壓力測試。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | 檢查 IC + NAND 為 8329 BICS8 KIC，否則 non-support | Phase 0 |
| Step 2 | 從 Geometry Descriptor 取得 MAX AU，然後 Config LUN | Phase 1, Phase 2 |
| Step 3 | VC-6 & VC-13 Config error Case | Phase 3 |
| Step 4 | VC1~13 除 VC6 & 13，Config & Write all card test（6 組 AU 配置） | Phase 4（Loop） |
| Step 5 | VC-14 Config LUN | Phase 5 |
| Step 6 | VC-15 Write attribute 啟用 Boot LUN A + Config LUN | Phase 6 |
| Step 7 | Bug 回歸驗證 Config LUN | Phase 7 |
| Step 8 | Random Case：隨機 Config + Write all Card + Compare all card | Phase 8 |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF002_1563 Test Flow
│
├── Phase 0: 裝置相容性檢查
│   └── Step 0.1: 裝置相容性檢查 — IC=8329, NAND=BICS8, KIC
│
├── Phase 1: 讀取 Geometry Descriptor
│   └── Step 1.1: UFS QUERY READ DESCRIPTOR (Geometry) — 取得 MAX AU 資訊
│
├── Phase 2: 基礎 LUN 配置（JIRA Step 2）
│   └── Step 2.1: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0=Normal, LUN1=BootA, LUN2=BootB
│
├── Phase 3: 錯誤配置測試 — VC-6 & VC-13（JIRA Step 3）
│   └── Step 3.1: UFS QUERY WRITE DESCRIPTOR — Config Error Case
│
├── Loop (6 組 AU Size 配置, per JIRA Step 4 VC1~13 except VC6 & VC13)
│   ├── Phase 4: VC1~13 配置與寫入測試
│   │   ├── Step 4.1: UFS QUERY WRITE DESCRIPTOR — 依當前 AU Config 配置 LUN 與 Memory Type
│   │   ├── Step 4.2: WRITE(10) (0x2A) — 寫入測試資料至 Boot LU A
│   │   ├── Step 4.3: WRITE(10) (0x2A) — 寫入測試資料至 Boot LU B
│   │   ├── Step 4.4: READ(10) (0x28) — 讀取 Boot LU A 並比對資料
│   │   └── Step 4.5: READ(10) (0x28) — 讀取 Boot LU B 並比對資料
│
├── Phase 5: VC-14 配置（JIRA Step 5）
│   └── Step 5.1: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0=Normal, LUN1=BootA, LUN2=BootB
│
├── Phase 6: VC-15 — 啟用 Boot LUN A 後配置（JIRA Step 6）
│   ├── Step 6.1: UFS QUERY WRITE ATTRIBUTE (bBootLunEn) — 啟用 Boot LU A
│   └── Step 6.2: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0=Normal, LUN1=BootA, LUN2=BootB
│
├── Phase 7: Bug 回歸驗證（JIRA Step 7）
│   └── Step 7.1: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0=Normal, LUN1=BootA
│
└── Phase 8: Random Case — 隨機配置與資料驗證（JIRA Step 8）
    ├── Step 8.1: UFS QUERY WRITE DESCRIPTOR — 隨機化 LUN 配置
    ├── Step 8.2: WRITE(10) (0x2A) — 寫入全部隨機配置之 LUN → Expected: GOOD Status
    └── Step 8.3: READ(10) (0x28) — 讀取全部 LUN 並比對 → Expected: GOOD Status, Data Match
```

---

## Phase 0 — 裝置相容性檢查

### Step 0.1: 裝置相容性檢查

**目的**: 確認 IC 及 NAND 型號為支援的組合。

**Check**:
- IC: 8329
- NAND: BICS8
- Vendor: KIC

**若不支援**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

**UFS SPEC Reference**: N/A（硬體層級檢查）

---

## Phase 1 — 讀取 Geometry Descriptor

### Step 1.1: UFS QUERY READ DESCRIPTOR — 取得 MAX AU 資訊

**UFS QUERY**: `READ DESCRIPTOR` (Query Opcode 0x07)

**目的**: 從 Geometry Descriptor 讀取裝置最大 AU (Allocation Unit) 資訊，用於後續 LUN 配置。

| Field | Value |
|-------|-------|
| Query Opcode | 0x07 (READ DESCRIPTOR) |
| bDescriptorIDN | 0x07 (Geometry Descriptor) |
| Index | 0x00 |
| Selector | 0x00 |

**讀取重點欄位**（Geometry Descriptor 內容）:
| Field | 說明 |
|-------|------|
| dMaxNumberLU | 最大 LU 數量 |
| dSegmentSize | Segment 大小 |
| bAllocationUnitSize | AU 大小 |

**UFS SPEC Reference**: JESD220H Section 14.2.5 (Geometry Descriptor), Section 10.7.8.7 (READ DESCRIPTOR)

---

## Phase 2 — 基礎 LUN 配置

### Step 2.1: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0=Normal, LUN1=BootA, LUN2=BootB

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 設定基礎 LUN 配置：LUN 0 為 Normal、LUN 1 為 Boot LU A、LUN 2 為 Boot LU B。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |

**Per-LUN 配置**:

| LUN Index | bLUEnable | bBootLUNID | 說明 |
|:----------|:----------|:-----------|:-----|
| 0 | 0x01 | 0xFF (Normal) | 一般 LU |
| 1 | 0x01 | 0x00 (Boot LU A) | Boot LU A |
| 2 | 0x01 | 0x01 (Boot LU B) | Boot LU B |

**UFS SPEC Reference**: JESD220H Section 14.2.2 (Configuration Descriptor), Section 14.2.3 (Unit Descriptor — bBootLUNID, dLUNumAllocUnits), Section 10.7.8.8 (WRITE DESCRIPTOR)

---

## Phase 3 — 錯誤配置測試（VC-6 & VC-13）

### Step 3.1: UFS QUERY WRITE DESCRIPTOR — Config Error Case

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 驗證 VC-6 與 VC-13 的錯誤配置場景。配置 LUN 8 為 Boot LU A、LUN 31 為 Boot LU B，測試邊界條件下的裝置行為。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |

**Per-LUN 配置**:

| LUN Index | bLUEnable | bBootLUNID | 說明 |
|:----------|:----------|:-----------|:-----|
| 0 | 0x01 | 0xFF (Normal) | 一般 LU |
| 8 | 0x01 | 0x00 (Boot LU A) | Boot LU A（高 index） |
| 31 | 0x01 | 0x01 (Boot LU B) | Boot LU B（邊界 index） |

**UFS SPEC Reference**: JESD220H Section 14.2.2 (Configuration Descriptor), Section 14.2.3 (Unit Descriptor), Section 10.7.8.8 (WRITE DESCRIPTOR)

---

## Phase 4 — VC1~13 配置與寫入測試（6 組 AU Size 迭代）

> **Loop 說明**: 本 Phase 在 6 組不同的 AU Size / Memory Type 配置下重複執行。
> 每組配置對應 JIRA Step 4 中的一個 Config Block，主要差異在 dLUNumAllocUnits 及
> 部分 LUN Index 的 Boot LUN 指派（詳見下方 Loop Iteration 對照表）。
>
> **Loop Iteration 對照表**（來自 JIRA Step 4 Config Case 1 的 6 個 Block）:
>
> | Iter | LUN→Boot 映射 | 說明 |
> |:-----|:--------------|:-----|
> | 1 | LUN1=BootA, LUN2=BootB | AU Config 1 |
> | 2 | LUN2=BootB, LUN1=BootA, LUN8=BootA, LUN31=BootB | AU Config 2 |
> | 3 | LUN31=BootB, LUN1=BootA, LUN2=BootB | AU Config 3 |
> | 4 | LUN1=BootA, LUN2=BootB | AU Config 4 |
> | 5 | LUN1=BootA, LUN2=BootB, LUN8=BootA, LUN31=BootB | AU Config 5 |
> | 6 | LUN31=BootB | AU Config 6 |

### Step 4.1: UFS QUERY WRITE DESCRIPTOR — 依當前 AU Config 配置 LUN 與 Memory Type

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 依當前 Loop 迭代的 AU 配置，寫入 Configuration Descriptor 設定各 LUN 的
Boot LUN ID、Memory Type 及 Allocation Unit 大小。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |

**Per-LUN 設定**（依迭代變化）:
| Field | 說明 |
|-------|------|
| bLUEnable | 0x01 |
| bBootLUNID | 依對照表（0x00 = BootA, 0x01 = BootB, 0xFF = Normal） |
| bMemoryType | 依當前配置（0x00 = Normal, 0x01 = Enhanced 等） |
| dLUNumAllocUnits | 依當前 AU 配置決定 |

**UFS SPEC Reference**: JESD220H Section 14.2.2 (Configuration Descriptor), Section 14.2.3 (Unit Descriptor), Section 10.7.8.8 (WRITE DESCRIPTOR)

---

### Step 4.2: WRITE(10) — 寫入測試資料至 Boot LU A

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 將測試 Pattern 資料寫入當前配置的 Boot LU A。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| FUA | 0 |
| DPO | 0 |
| LUN | Boot LU A（bBootLUNID = 0x00） |
| LBA | 0x00000000 |
| Transfer Length | 依當前 AU 配置之 LU 容量決定 |

**UFS SPEC Reference**: SBC-4 Section 5.47 (WRITE(10) command)

---

### Step 4.3: WRITE(10) — 寫入測試資料至 Boot LU B

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 將測試 Pattern 資料寫入當前配置的 Boot LU B。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| FUA | 0 |
| DPO | 0 |
| LUN | Boot LU B（bBootLUNID = 0x01） |
| LBA | 0x00000000 |
| Transfer Length | 依當前 AU 配置之 LU 容量決定 |

**UFS SPEC Reference**: SBC-4 Section 5.47 (WRITE(10) command)

---

### Step 4.4: READ(10) — 讀取 Boot LU A 並比對資料

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 從 Boot LU A 讀回先前寫入的資料，並與原始寫入資料進行比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LU A（bBootLUNID = 0x00） |
| LBA | 0x00000000 |
| Transfer Length | 與 Step 4.2 寫入範圍相同 |

**UFS SPEC Reference**: SBC-4 Section 5.16 (READ(10) command)

---

### Step 4.5: READ(10) — 讀取 Boot LU B 並比對資料

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 從 Boot LU B 讀回先前寫入的資料，並與原始寫入資料進行比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LU B（bBootLUNID = 0x01） |
| LBA | 0x00000000 |
| Transfer Length | 與 Step 4.3 寫入範圍相同 |

**UFS SPEC Reference**: SBC-4 Section 5.16 (READ(10) command)

---

## Phase 5 — VC-14 配置

### Step 5.1: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0=Normal, LUN1=BootA, LUN2=BootB

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 執行 VC-14 配置案例：LUN 0 為 Normal、LUN 1 為 Boot LU A、LUN 2 為 Boot LU B。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |

**Per-LUN 配置**:

| LUN Index | bLUEnable | bBootLUNID | 說明 |
|:----------|:----------|:-----------|:-----|
| 0 | 0x01 | 0xFF (Normal) | 一般 LU |
| 1 | 0x01 | 0x00 (Boot LU A) | Boot LU A |
| 2 | 0x01 | 0x01 (Boot LU B) | Boot LU B |

**UFS SPEC Reference**: JESD220H Section 14.2.2, Section 14.2.3, Section 10.7.8.8

---

## Phase 6 — VC-15：啟用 Boot LUN A 後配置

### Step 6.1: UFS QUERY WRITE ATTRIBUTE — 啟用 Boot LU A

**UFS QUERY**: `WRITE ATTRIBUTE` (Query Opcode 0x04)

**目的**: 透過寫入 bBootLunEn 屬性啟用 Boot LU A。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| bAttrIDN | 0x00 (bBootLunEn) |
| Attr Value | 0x01 (Bit 0: Boot LU A Enable) |
| Attr Size | 1 byte |

**UFS SPEC Reference**: JESD220H Section 14.3 (bBootLunEn, IDN 0x00), Section 10.7.8.4 (WRITE ATTRIBUTE)

---

### Step 6.2: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0=Normal, LUN1=BootA, LUN2=BootB

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 在 Boot LU A 啟用後，配置 LUN 0 為 Normal、LUN 1 為 Boot LU A、LUN 2 為 Boot LU B。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |

**Per-LUN 配置**:

| LUN Index | bLUEnable | bBootLUNID | 說明 |
|:----------|:----------|:-----------|:-----|
| 0 | 0x01 | 0xFF (Normal) | 一般 LU |
| 1 | 0x01 | 0x00 (Boot LU A) | Boot LU A |
| 2 | 0x01 | 0x01 (Boot LU B) | Boot LU B |

**UFS SPEC Reference**: JESD220H Section 14.2.2, Section 14.2.3, Section 10.7.8.8

---

## Phase 7 — Bug 回歸驗證

### Step 7.1: UFS QUERY WRITE DESCRIPTOR — 配置 LUN0=Normal, LUN1=BootA

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 執行 Bug 回歸驗證（參考 JIRA U383291001-3982），配置 LUN 0 為 Normal、LUN 1 為 Boot LU A。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |

**Per-LUN 配置**:

| LUN Index | bLUEnable | bBootLUNID | 說明 |
|:----------|:----------|:-----------|:-----|
| 0 | 0x01 | 0xFF (Normal) | 一般 LU |
| 1 | 0x01 | 0x00 (Boot LU A) | Boot LU A |

**UFS SPEC Reference**: JESD220H Section 14.2.2, Section 14.2.3, Section 10.7.8.8

---

## Phase 8 — Random Case：隨機配置與資料驗證

### Step 8.1: UFS QUERY WRITE DESCRIPTOR — 隨機化 LUN 配置

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 隨機決定 LUN 配置參數，包含 Index 數量、AU 大小、Boot LUN 指派，模擬多變的配置壓力場景。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |

**Branch Logic** (per JIRA Random Case):
- 隨機決定 Index 數量：0 ~ 3
- 隨機決定 LUN 數量：0 ~ 8
- 隨機決定 AU Size
- 隨機決定 Boot LUN 指派：Boot LU A / Boot LU B / Normal

**UFS SPEC Reference**: JESD220H Section 14.2.2, Section 14.2.3, Section 10.7.8.8

---

### Step 8.2: WRITE(10) — 寫入全部隨機配置之 LUN

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 對所有已配置的 LUN 寫入測試 Pattern 資料。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| FUA | 0 |
| DPO | 0 |
| LUN | 所有已配置 LUN（依 Step 8.1 隨機結果） |
| LBA | 0x00000000 |
| Transfer Length | 依各 LUN 配置大小 |

**Expected**: GOOD Status（來源：JIRA Step 8 "預期 Response Success"）

**UFS SPEC Reference**: SBC-4 Section 5.47 (WRITE(10) command)

---

### Step 8.3: READ(10) — 讀取全部 LUN 並比對

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 從所有已配置 LUN 讀回資料，並與原始寫入資料逐一比對驗證。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 所有已配置 LUN（依 Step 8.1 隨機結果） |
| LBA | 0x00000000 |
| Transfer Length | 與 Step 8.2 寫入範圍相同 |

**Expected**: GOOD Status, Data Match（來源：JIRA Step 8 "預期 Response Success * Compare success"）

**UFS SPEC Reference**: SBC-4 Section 5.16 (READ(10) command)

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x04 | WRITE ATTRIBUTE | 啟用 Boot LU A (bBootLunEn) |
| 0x07 | READ DESCRIPTOR | 讀取 Geometry Descriptor 取得 MAX AU |
| 0x08 | WRITE DESCRIPTOR | 配置 LUN 組態（Boot LUN ID / AU Size / Memory Type） |

### Attribute IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x00 | bBootLunEn | Read-Write | 啟用/停用 Boot LU A 及 Boot LU B |

### Descriptor IDN

| IDN | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x01 | Configuration Descriptor | 配置各 LUN 的啟用狀態、Boot LUN ID、Memory Type、AU Size |
| 0x07 | Geometry Descriptor | 讀取裝置最大 AU 資訊及 LU 數量上限 |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | 從 Boot LUN 讀取資料並比對驗證 |
| 0x2A | WRITE(10) | 10 | 寫入測試 Pattern 資料至 Boot LUN |

---

## 附錄 C — UFS Boot LUN ID 對照表

| bBootLUNID | 名稱 | 說明 |
|:-----------|:-----|:-----|
| 0x00 | Boot LU A | 第一 Boot Logical Unit |
| 0x01 | Boot LU B | 第二 Boot Logical Unit |
| 0xFF | Normal LU | 非 Boot 的一般 Logical Unit |

**UFS SPEC Reference**: JESD220H Section 14.2.3 (Unit Descriptor — bBootLUNID)

---

## 自我驗證

- Tree Diagram leaf steps: **16**（Phase 0: 1 (0.1), Phase 1: 1 (1.1), Phase 2: 1 (2.1), Phase 3: 1 (3.1), Phase 4: 5 (4.1~4.5), Phase 5: 1 (5.1), Phase 6: 2 (6.1~6.2), Phase 7: 1 (7.1), Phase 8: 3 (8.1~8.3) → Total: 16）
- `### Step` sections: **16** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（2 個 Steps 含 Expected：Step 8.2, 8.3 — 來源: JIRA Step 8 "預期 Response Success * Compare success"）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
