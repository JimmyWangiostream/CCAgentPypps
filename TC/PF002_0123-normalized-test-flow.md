---
title: PF002_0123_ReadBootDataAfterSleepMode-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_0123, scsi-cmd, boot-lu, sleep-mode, reset, hw-reset, rst-n, endpoint-reset, unipro-reset]
description: >
  驗證裝置在 InitPowerMode 設定為 Sleep Mode 的情境下，經過不同類型 Reset
  (HW_RESET, RST_n, EndPoint Reset, UniPro Reset) 後，Boot LU 中的資料仍可正確讀取。
  測試分為兩輪（Round A 與 Round B），每輪包含 Sleep Mode 配置、資料寫入、Boot LU
  設定，以及對四種 Reset 類型的 Boot Data 讀取驗證。
sources:
  - JIRA: PF002_0123 (SYSTCUFS-101)
  - UFS Spec: JESD220H Section 10.3, 10.7.8–10.7.9, 11.3, 11.5, 14.2.2, 14.3.1
---

# PF002_0123: Read Boot Data After Sleep Mode — Normalized Test Flow

## 測試架構（Tree Diagram）

```
PF002_0123 Test Flow
│
├── Phase 0: Device Initialization
│   └── Step 0.1: TEST UNIT READY — 確認裝置就緒
│
└── Loop (2 rounds: Round A, Round B)
    │
    ├── Phase 1: Sleep Mode Configuration
    │   ├── Step 1.1: WRITE DESCRIPTOR — 設定 bInitPowerMode 為 Sleep Mode
    │   ├── Step 1.2: HW_RESET
    │   └── Step 1.3: START STOP UNIT — 切換至 Active 模式
    │
    ├── Phase 2: Write Test Data
    │   └── Step 2.1: WRITE(10) — 對每個已啟用 LUN 從 LBA0 寫入 512KB 資料
    │
    ├── Phase 3: Boot LU Configuration
    │   └── Step 3.1: WRITE ATTRIBUTE(bBootLunEn) — 啟用 Boot LU A 與 Boot LU B
    │
    └── Loop (for each reset type: HW_RESET, RST_n, EndPoint Reset, UniPro Reset)
        │
        ├── Step 4.1: <Reset Type> Reset — 執行對應類型 Reset
        ├── Step 4.2: START STOP UNIT — 切換至 Active 模式
        └── Step 4.3: READ(10) — 讀取 Boot LU 資料
```

---

## Phase 0 — Device Initialization

### Step 0.1: 確認裝置就緒

**SCSI CMD**: `TEST UNIT READY (0x00)`

**目的**: 確認 UFS 裝置已開機且可接受命令，作為測試進入點。

| Field | Value |
|-------|-------|
| Opcode | 0x00 |
| LUN | 0x00 (Well-known LU) |

**UFS SPEC Reference**: JESD220H Section 11.2

---

## Loop — 2 Rounds (Round A, Round B)

依原始 JIRA Pattern，步驟 1–7（Round A）與步驟 8–14（Round B）為兩輪相同流程的重複測試。以下 Phase 1–4 在每輪中完整執行一次。

---

## Phase 1 — Sleep Mode Configuration

### Step 1.1: 設定 InitPowerMode 為 Sleep Mode

**UFS QUERY**: `WRITE DESCRIPTOR (0x08)`

**目的**: 將 Device 的 Initial Power Mode 設定為 Sleep Mode，使裝置在每次 Reset 後自動進入 Sleep 狀態。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| Descriptor Type | 0x01 (Configuration Descriptor) |
| Index | 0x00 |
| Selector | 0x00 |
| Field (within descriptor) | bInitPowerMode |
| Value | 0x00 (UFS-Sleep Mode) |

**UFS SPEC Reference**: JESD220H Section 10.7.9, 14.2.2

---

### Step 1.2: HW_RESET

**操作類型**: Hardware Reset

**目的**: 執行 HW_RESET 使裝置重新初始化，並因 bInitPowerMode = Sleep 而在 Reset 後進入 Sleep Mode。

| Field | Value |
|-------|-------|
| Reset Type | HW_RESET |
| 觸發方式 | 硬體 Reset 訊號 |

**UFS SPEC Reference**: JESD220H Section 10.3.1

---

### Step 1.3: 切換至 Active 模式

**SCSI CMD**: `START STOP UNIT (0x1B)`

**目的**: 將裝置從 Sleep Mode 喚醒至 Active Mode，以便後續進行資料寫入操作。

| Field | Value |
|-------|-------|
| Opcode | 0x1B |
| LUN | 0x00 (Well-known LU) |
| Byte 4, bits 3–0 (POWER CONDITION) | 0x1 (ACTIVE) |
| Byte 4, bit 4 (IMMED) | 0 (Wait for completion) |
| Byte 4, bit 0 (START) | 0 |

**UFS SPEC Reference**: JESD220H Section 11.3

---

## Phase 2 — Write Test Data

### Step 2.1: 對每個已啟用 LUN 寫入 512KB 測試資料

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 對裝置上所有已啟用的 Logical Unit（包含後續將設為 Boot LU 的 LUN），從 LBA 0 寫入 512 KB 測試資料，作為後續 Reset 後資料完整性驗證的基準。

> **注意**: 此 Step 在每個已啟用的 LUN 上各執行一次 WRITE(10)。LUN 清單需在執行期透過 READ DESCRIPTOR (Unit Descriptor) 或 READ CAPACITY 掃描取得。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 各已啟用 LUN |
| LBA | 0x00000000 |
| Transfer Length | 1024 (512 KB at 512B sector) 或對應區塊數 |
| Data | 測試 Pattern（預先定義的已知資料） |

**UFS SPEC Reference**: JESD220H Section 11.5

---

## Phase 3 — Boot LU Configuration

### Step 3.1: 設定 Boot LU A 與 Boot LU B

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)`

**目的**: 透過寫入 bBootLunEn Attribute，將 Boot LU A 與 Boot LU B 同時啟用，使裝置在後續 Reset 後可從這些 Boot LU 讀取開機資料。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| Attribute IDN | 0x00 (bBootLunEn) |
| LUN | 0x00 (Well-known LU) |
| Value | 0x03 (Bit 0 = Boot LU A enabled, Bit 1 = Boot LU B enabled) |
| Size | 1 byte |

**UFS SPEC Reference**: JESD220H Section 14.3.1

---

## Loop — 4 Reset Types (per Round)

依原始 JIRA Pattern，以下 Step 4.1–4.3 對四種 Reset 類型各執行一次：

| 迴圈索引 | Reset 類型 |
|:---|:---|
| 1 | HW_RESET |
| 2 | RST_n |
| 3 | EndPoint Reset |
| 4 | UniPro Reset |

---

### Step 4.1: <Reset Type> Reset

**操作類型**: Reset

**目的**: 對裝置執行當前迴圈對應的 Reset 類型，使裝置重新初始化並因 bInitPowerMode = Sleep 而進入 Sleep Mode。此 Reset 後 Boot LU 中的資料應保持完整。

| Field | Value |
|-------|-------|
| Reset Type | 依 Loop 指定（HW_RESET / RST_n / EndPoint Reset / UniPro Reset） |
| 參數 | 依 Reset 類型而定 |

**UFS SPEC Reference**: JESD220H Section 10.3 (各 Reset 類型說明)

---

### Step 4.2: 切換至 Active 模式（Reset 後）

**SCSI CMD**: `START STOP UNIT (0x1B)`

**目的**: Reset 後裝置處於 Sleep Mode（因 bInitPowerMode = Sleep），需切換至 Active 才能進行 Boot LU 資料讀取。

| Field | Value |
|-------|-------|
| Opcode | 0x1B |
| LUN | 0x00 (Well-known LU) |
| Byte 4, bits 3–0 (POWER CONDITION) | 0x1 (ACTIVE) |
| Byte 4, bit 4 (IMMED) | 0 (Wait for completion) |
| Byte 4, bit 0 (START) | 0 |

**UFS SPEC Reference**: JESD220H Section 11.3

---

### Step 4.3: 讀取 Boot LU 資料

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 從已配置的 Boot LU 讀取資料，用於驗證 Reset 後 Boot Data 的完整性（與 Step 2.1 寫入的資料比對）。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LU（由 bBootLunEn 設定決定；通常為 Boot LU A） |
| LBA | 0x00000000 |
| Transfer Length | 1024 (512 KB at 512B sector) 或對應區塊數 |

**UFS SPEC Reference**: JESD220H Section 11.5

---

## 附錄 A — UFS Query IDN 對照表

| Query Opcode | Name | 本 Pattern 用途 |
|:---|:---|:---|
| 0x04 | WRITE ATTRIBUTE | 寫入 bBootLunEn (IDN 0x00)，設定啟用的 Boot LU |
| 0x08 | WRITE DESCRIPTOR | 寫入 Configuration Descriptor，設定 bInitPowerMode |

| Attribute IDN | Name | Size | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x00 | bBootLunEn | 1 byte | 啟用 Boot LU A (bit 0) + Boot LU B (bit 1) |

---

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x00 | TEST UNIT READY | 6 | Phase 0：確認裝置就緒 |
| 0x1B | START STOP UNIT | 6 | Phase 1/4：切換 Power Condition 至 Active |
| 0x28 | READ(10) | 10 | Phase 4：讀取 Boot LU 資料驗證 |
| 0x2A | WRITE(10) | 10 | Phase 2：寫入 512KB 測試資料至各 LUN |

---

## 附錄 C — UFS Reset 類型說明

| Reset 類型 | 說明 | SPEC Reference |
|:---|:---|:---|
| HW_RESET | 硬體 Reset 訊號 (REF_CLK / RST_n asserted) | JESD220H Section 10.3.1 |
| RST_n | RST_n 接腳 Reset 訊號 | JESD220H Section 10.3.2 |
| EndPoint Reset | UFS EndPoint Reset (M-PHY level) | JESD220H Section 10.3 |
| UniPro Reset | UniPro 層 Reset (via DME) | JESD220H Section 10.3 / MIPI UniPro |

---

## 自我驗證

- Tree Diagram leaf steps: **9**（列出每個 Phase 數量並加總）
  Phase 0: 1 (0.1), Phase 1: 3 (1.1~1.3), Phase 2: 1 (2.1), Phase 3: 1 (3.1), Phase 4: 3 (4.1~4.3) → Total: 9
- `### Step` sections: **9** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（0 個 Expected — JIRA Note 欄全空，無任何預期結果描述）
- 無憑空生成的 Expected 值（JIRA Pattern 未描述任何預期行為）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
