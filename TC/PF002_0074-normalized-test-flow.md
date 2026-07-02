---
title: PF002_0074_BootLUN_Disable_Read_Test-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_0074, scsi-cmd, boot-lun, bBootLunEn]
description: >
  驗證當 bBootLunEn 設為 0（Boot LUN 停用）後，無論是否經過其他 LUN 的寫入操作，
  對 Boot W-LUN 發送 READ(10) 皆應回傳 CHECK_CONDITION，
  SENSE_KEY=ILLEGAL_REQUEST(05h)，ASC=LOGICAL_UNIT_NOT_SUPPORTED(25h)。
  測試包含兩輪：第一輪在乾淨環境下立即 Reset + Read；第二輪先寫入其他 LUN 再 Reset + Read。
sources:
  - JIRA: PF002_0074 (SYSTCUFS-232)
  - UFS Spec: JESD220H Section 10.4, 10.7.8, 11.2.4, 11.2.5, 14.3
---

# PF002_0074 Boot LUN Disable Read Test — Normalized Test Flow

## 測試架構（Tree Diagram）

```
PF002_0074 Test Flow
│
├── Phase 0: Setup — 停用 Boot LUN
│   └── Step 0.1: WRITE ATTRIBUTE — bBootLunEn = 0
│
├── Phase 1: 第一輪驗證 — Clean Reset 後讀取 Boot W-LUN
│   ├── Step 1.1: Reset — HW_RESET / RST_n / EndPoint / UniPro
│   └── Step 1.2: READ(10) — Boot W-LUN 讀取 → Expected: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL_UNIT_NOT_SUPPORTED(25h)
│
└── Phase 2: 第二輪驗證 — 寫入其他 LUN 後 Reset 再讀取 Boot W-LUN
    ├── Step 2.1: WRITE ATTRIBUTE — bBootLunEn = 0（再次確認）
    ├── Step 2.2: WRITE(10) — 對每個 Enabled LUN 寫入 512K
    ├── Step 2.3: Reset — HW_RESET / RST_n / EndPoint / UniPro
    └── Step 2.4: READ(10) — Boot W-LUN 讀取 512K → Expected: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL_UNIT_NOT_SUPPORTED(25h)
```

---

## Phase 0 — Setup：停用 Boot LUN

### Step 0.1: 停用 Boot LUN — 設定 bBootLunEn = 0

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bBootLunEn (IDN 0x00)

**目的**: 將 Boot LUN 設為停用狀態，為後續驗證做準備。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Index | 0x00 |
| Selector | 0x00 |
| Value | 0x00 (Boot LUN disabled) |
| Size | 1 byte |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn Attribute)

---

## Phase 1 — 第一輪驗證：Clean Reset 後讀取 Boot W-LUN

### Step 1.1: 觸發裝置 Reset

**UFS RESET**: HW_RESET / RST_n / EndPoint Reset / UniPro Reset

**目的**: 在 Boot LUN 停用後觸發裝置重置，使 Boot LUN 配置生效，然後驗證 Boot W-LUN 存取狀態。

| Parameter | Value |
|-----------|-------|
| Reset Types | HW_RESET, RST_n, EndPoint Reset, UniPro Reset |
| Target | Device-level reset |

**UFS SPEC Reference**: JESD220H Section 10.4 (Reset and Initialization)

---

### Step 1.2: 讀取 Boot W-LUN — 驗證停用後無法存取

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 bBootLunEn=0 且完成 Reset 後，嘗試讀取 Boot W-LUN，驗證裝置拒絕存取。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 (Boot data area) |
| Group Number | 0x00 |
| Transfer Length | 0x0008 (4KB, 測試用基本讀取) |
| Target LUN | Boot W-LUN |

**Expected**: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL_UNIT_NOT_SUPPORTED(25h)
（JIRA Step 4 — "Device shall return fail [Detailed Test Steps]"；JIRA Step 9 提供具體 Sense Code）

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

## Phase 2 — 第二輪驗證：寫入其他 LUN 後 Reset 再讀取 Boot W-LUN

### Step 2.1: 再次確認 Boot LUN 停用 — 設定 bBootLunEn = 0

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bBootLunEn (IDN 0x00)

**目的**: 在第二輪驗證開始前，再次確認 bBootLunEn 維持為 0（Boot LUN disabled）。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Index | 0x00 |
| Selector | 0x00 |
| Value | 0x00 (Boot LUN disabled) |
| Size | 1 byte |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn Attribute)

---

### Step 2.2: 對每個 Enabled LUN 寫入測試資料

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 對所有已啟用的非 Boot LUN 寫入 512KB 測試資料，產生裝置活動後再觸發 Reset，以驗證 Boot LUN 在裝置有寫入歷史後仍維持停用狀態。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| WRPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 (測試資料起始位址) |
| Group Number | 0x00 |
| Transfer Length | 0x0400 (1024 blocks = 512KB) |
| Target LUN | 每個已啟用的 LUN（逐一寫入，排除 Boot W-LUN） |
| Data Pattern | 測試用任意 pattern |

**備註**: 需逐一對每個 enabled LUN 發送 WRITE(10)，不可合併為單一命令。

**UFS SPEC Reference**: JESD220H Section 11.2.5 (WRITE(10) command)

---

### Step 2.3: 觸發裝置 Reset

**UFS RESET**: HW_RESET / RST_n / EndPoint Reset / UniPro Reset

**目的**: 在完成其他 LUN 的寫入後觸發裝置重置，使 Boot LUN 配置再次生效，為第二輪 Boot W-LUN 讀取驗證做準備。

| Parameter | Value |
|-----------|-------|
| Reset Types | HW_RESET, RST_n, EndPoint Reset, UniPro Reset |
| Target | Device-level reset |

**UFS SPEC Reference**: JESD220H Section 10.4 (Reset and Initialization)

---

### Step 2.4: 讀取 Boot W-LUN（512K）— 驗證寫入後仍無法存取

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在其他 LUN 寫入並 Reset 後，嘗試對 Boot W-LUN 進行 512KB 讀取，驗證 Boot LUN 仍維持停用狀態，裝置拒絕存取並回傳預期的 Sense Code。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| RDPROTECT / DPO / FUA / FUA_NV | 0x00 |
| LBA | 0x00000000 (Boot data area) |
| Group Number | 0x00 |
| Transfer Length | 0x0400 (1024 blocks = 512KB) |
| Target LUN | Boot W-LUN |

**Expected**: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL_UNIT_NOT_SUPPORTED(25h)
（JIRA Step 9 — "Device shall return fail, SK shall be ILLEGAL_REQUEST, ASC shall be LOGICAL_UNIT_NOT_SUPPORTED"）

**UFS SPEC Reference**: JESD220H Section 11.2.4 (READ(10) command)

---

## 附錄 A — UFS Query IDN 對照表

| Query Opcode | Name | IDN | Target | Description |
|:---|:---|:---|:---|:---|
| 0x04 | WRITE ATTRIBUTE | 0x00 | bBootLunEn | Boot Logical Unit enable (1 byte, Read-Write) |

---

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | Use in This Pattern |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | 讀取 Boot W-LUN 驗證停用後拒絕存取 |
| 0x2A | WRITE(10) | 10 | 對 enabled LUN 寫入測試資料 |

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

## 附錄 C — UFS Reset 類型說明

| Reset Type | Scope | Description |
|:---|:---|:---|
| HW_RESET | Device | Hardware reset signal to device |
| RST_n | Device | Reset pin assertion (active low) |
| EndPoint Reset | Transport | UFS EndPoint (M-PHY) reset |
| UniPro Reset | Transport | UniPro link reset |

**UFS SPEC Reference**: JESD220H Section 10.4 (Reset and Initialization)

---

## 自我驗證

- Tree Diagram leaf steps: **7**
  Phase 0: 1 (0.1), Phase 1: 2 (1.1~1.2), Phase 2: 4 (2.1~2.4) → Total: 7
- `### Step` sections: **7** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（2 steps with Expected: 1.2, 2.4）
  - Step 1.2 Expected 來自 JIRA Step 4 ("Device shall return fail [Detailed Test Steps]") + Step 9 具體 Sense Code
  - Step 2.4 Expected 來自 JIRA Step 9 ("SK shall be ILLEGAL_REQUEST, ASC shall be LOGICAL_UNIT_NOT_SUPPORTED")
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
