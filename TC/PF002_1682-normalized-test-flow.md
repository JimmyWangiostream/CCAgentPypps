---
title: PF002_1682_D_Boot_LUN_Diff_Index_Diff_Memory_Type-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_1682, scsi-cmd, boot-lun, memory-type]
description: >
  驗證兩個 Boot LUN 使用不同 Memory Type（Enhanced / Normal）及不同配置大小
  時，寫入資料後能正確讀取並比對通過。測試包含 Boot LUN 啟用、Memory Type 配置、
  全部 LUN 清除、寫入及讀取比對。
sources:
  - JIRA: PF002_1682 (SYSTCUFS-1995)
  - UFS Spec: JESD220H
---

# PF002_1682_D_Boot_LUN_Diff_Index_Diff_Memory_Type — 正規化測試流程

## 測試架構（Tree Diagram）

```
PF002_1682 Test Flow
│
├── Phase 0: 裝置相容性檢查
│   └── Step 0.1: 裝置相容性檢查 — IC=8329, NAND=BICS8
│
├── Phase 1: Boot LUN 配置
│   ├── Step 1.1: UFS QUERY WRITE ATTRIBUTE (bBootLunEn) — 啟用 Boot LUN
│   ├── Step 1.2: UFS QUERY WRITE DESCRIPTOR (Configuration Descriptor) — 配置 Boot LU 0 (Enhanced, Max Size)
│   └── Step 1.3: UFS QUERY WRITE DESCRIPTOR (Configuration Descriptor) — 配置 Boot LU 1 (Normal, Min Size)
│
├── Phase 2: 資料清除
│   └── Step 2.1: UNMAP (0x42) — 清除所有 LUN
│
├── Phase 3: 寫入測試資料
│   ├── Step 3.1: WRITE(10) (0x2A) — 寫入資料至 Boot LU 0
│   └── Step 3.2: WRITE(10) (0x2A) — 寫入資料至 Boot LU 1
│
└── Phase 4: 讀取與驗證
    ├── Step 4.1: READ(10) (0x28) — 讀取 Boot LU 0 並比對 → Expected: Data Compare Pass
    └── Step 4.2: READ(10) (0x28) — 讀取 Boot LU 1 並比對 → Expected: Data Compare Pass
```

---

## Phase 0 — 裝置相容性檢查

### Step 0.1: 裝置相容性檢查

**目的**: 確認 IC 及 NAND 型號為支援的組合。

**Check**:
- IC: 8329
- NAND: BICS8

**若不支援**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

**UFS SPEC Reference**: N/A（硬體層級檢查）

---

## Phase 1 — Boot LUN 配置

### Step 1.1: UFS QUERY WRITE ATTRIBUTE — 啟用 Boot LUN

**UFS QUERY**: `WRITE ATTRIBUTE` (Query Opcode 0x04)

**目的**: 設定 bBootLunEn 屬性，啟用 Boot LU A 及 Boot LU B。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| bAttrIDN | 0x00 (bBootLunEn) |
| Attr Value | 0x03 (bit 0: Boot LU A, bit 1: Boot LU B) |
| Attr Size | 1 byte |

**UFS SPEC Reference**: JESD220H Section 14.3 (bBootLunEn, IDN 0x00), Section 10.7.8.4 (WRITE ATTRIBUTE)

---

### Step 1.2: UFS QUERY WRITE DESCRIPTOR — 配置 Boot LU 0 (Enhanced, Max Size)

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 將 Boot LU 0 配置為 Enhanced Memory Type，並設定為最大可用空間。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |
| Index | 0x00 (LU 0) |
| bLUEnable | 0x01 |
| bBootLUNID | 0x00 (Boot LU A) |
| bDescrAccessEn | 0x01 |
| bMemoryType | 0x01 (Enhanced Memory) |
| dLUNumAllocUnits | Max available (透過 Unit Descriptor IDN 0x02 設定) |

**UFS SPEC Reference**: JESD220H Section 14.2.2 (Configuration Descriptor), Section 14.2.3 (Unit Descriptor), Section 10.7.8.8 (WRITE DESCRIPTOR)

---

### Step 1.3: UFS QUERY WRITE DESCRIPTOR — 配置 Boot LU 1 (Normal, Min Size)

**UFS QUERY**: `WRITE DESCRIPTOR` (Query Opcode 0x08)

**目的**: 將 Boot LU 1 配置為 Normal Memory Type，並設定為最小可用空間。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| bDescriptorIDN | 0x01 (Configuration Descriptor) |
| Index | 0x01 (LU 1) |
| bLUEnable | 0x01 |
| bBootLUNID | 0x01 (Boot LU B) |
| bDescrAccessEn | 0x01 |
| bMemoryType | 0x00 (Normal Memory) |
| dLUNumAllocUnits | Min available (透過 Unit Descriptor IDN 0x02 設定) |

**UFS SPEC Reference**: JESD220H Section 14.2.2 (Configuration Descriptor), Section 14.2.3 (Unit Descriptor), Section 10.7.8.8 (WRITE DESCRIPTOR)

---

## Phase 2 — 資料清除

### Step 2.1: UNMAP — 清除所有 LUN

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 對所有 LUN 發出 UNMAP 命令，清除既有資料。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| ANCHOR | 0 |
| LBA | 0x00000000 |
| Parameter List Length | 依 UNMAP 參數列表大小（涵蓋所有 LUN 全部 LBA 範圍） |

**UNMAP Parameter List** (per LUN):
| Field | Value |
|-------|-------|
| UNMAP LBA | 0x0000000000000000 |
| Number of LBAs | Max LBA count (全 LUN 範圍) |

**UFS SPEC Reference**: SBC-4 Section 5.36 (UNMAP command), JESD220H Section 10.6 (SCSI Command Set)

---

## Phase 3 — 寫入測試資料

### Step 3.1: WRITE(10) — 寫入資料至 Boot LU 0

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 將測試 Pattern 資料寫入 Boot LU 0。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| FUA | 0 |
| DPO | 0 |
| LUN | Boot LU 0 |
| LBA | 0x00000000 |
| Transfer Length | 依測試範圍（由 Boot LU 0 配置大小決定） |

**UFS SPEC Reference**: SBC-4 Section 5.47 (WRITE(10) command)

---

### Step 3.2: WRITE(10) — 寫入資料至 Boot LU 1

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 將測試 Pattern 資料寫入 Boot LU 1。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| FUA | 0 |
| DPO | 0 |
| LUN | Boot LU 1 |
| LBA | 0x00000000 |
| Transfer Length | 依測試範圍（由 Boot LU 1 配置大小決定） |

**UFS SPEC Reference**: SBC-4 Section 5.47 (WRITE(10) command)

---

## Phase 4 — 讀取與驗證

### Step 4.1: READ(10) — 讀取 Boot LU 0 並比對資料

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 從 Boot LU 0 讀回先前寫入的資料，並與原始寫入資料進行比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LU 0 |
| LBA | 0x00000000 |
| Transfer Length | 與 Step 3.1 寫入範圍相同 |

**Expected**: Data Compare Pass

**UFS SPEC Reference**: SBC-4 Section 5.16 (READ(10) command)

---

### Step 4.2: READ(10) — 讀取 Boot LU 1 並比對資料

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 從 Boot LU 1 讀回先前寫入的資料，並與原始寫入資料進行比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LU 1 |
| LBA | 0x00000000 |
| Transfer Length | 與 Step 3.2 寫入範圍相同 |

**Expected**: Data Compare Pass

**UFS SPEC Reference**: SBC-4 Section 5.16 (READ(10) command)

---

## 附錄 A — UFS Query IDN 對照表

| IDN | Name | Type | Description | SPEC Ref |
|:---|:---|:---|:---|:---|
| 0x00 | bBootLunEn | Attribute | Boot LU Enable 位元遮罩 | JESD220H 14.3 |
| 0x01 | Configuration Descriptor | Descriptor | 裝置組態描述元（含 per-LU bMemoryType） | JESD220H 14.2.2 |
| 0x02 | Unit Descriptor | Descriptor | LU 組態描述元（含 dLUNumAllocUnits） | JESD220H 14.2.3 |

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | Description | SPEC Ref |
|:---|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | 讀取資料 | SBC-4 5.16 |
| 0x2A | WRITE(10) | 10 | 寫入資料 | SBC-4 5.47 |
| 0x42 | UNMAP | 10 | 釋放對應 LBA 空間 | SBC-4 5.36 |

## 附錄 C — UFS Query Opcode 對照表

| Opcode | Name | Description |
|:---|:---|:---|
| 0x04 | WRITE ATTRIBUTE | 寫入 UFS Attribute |
| 0x08 | WRITE DESCRIPTOR | 寫入 UFS Descriptor |

---

## 自我驗證

- Tree Diagram leaf steps: **9**（Phase 0: 1 (0.1), Phase 1: 3 (1.1~1.3), Phase 2: 1 (2.1), Phase 3: 2 (3.1~3.2), Phase 4: 2 (4.1~4.2) → Total: 9）
- `### Step` sections: **9** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（Step 4.1, 4.2 — 來源: JIRA Step 6 "check data cmp pass"）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
