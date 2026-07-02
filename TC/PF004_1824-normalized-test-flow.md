---
title: PF004_1824_CommandQueueOrder-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf004_1824, scsi-cmd, command-queue, task-attribute, ordered, simple]
description: >
  驗證 UFS 裝置對 Ordered 與 Simple Task Attribute 的命令排程行為。測試包含三個層級：
  (1) Ordered Commands — 以 ORDERED attribute 推送 Write+Read 對，確認資料比對正確；
  (2) Simple Commands — 以 SIMPLE attribute 執行 Write→Read, Unmap→Read, Write→Read 三種序列，確認裝置可任意重排但不影響資料正確性；
  (3) Buffer-Fill Loop — 持續推送 Simple Commands 直到命令佇列滿，驗證大量排程下的穩定性。
  外層包覆 Auto Standby Enable/Disable 雙模式測試及 Burn-in 長時間壓力迴圈。
sources:
  - JIRA: PF004_1824 (SYSTCUFS-2120)
  - UFS Spec: JESD220H Section 10.7 (Command UPIU), Section 10.7.8 (Query), Section 12.3.13 (UNMAP), Section 14.3 (Attributes)
---

# PF004_1824 Command Queue Order Test — Normalized Test Flow

## 測試架構（Tree Diagram）

```
PF004_1824 Test Flow
│
├── Loop (burn-in time)
│   │
│   └── Loop (auto_standby in [Enable, Disable])
│       │
│       ├── Phase 0: Pre-condition — Erase, Purge, Baseline Write
│       │   ├── Step 0.1: UNMAP(0x42) — Erase all LUNs
│       │   ├── Step 0.2: SET FLAG(fPurgeEnable) — Trigger Purge
│       │   ├── Step 0.3: READ ATTRIBUTE(bBackgroundOpStatus) — Poll Purge complete
│       │   └── Step 0.4: WRITE(10) — Baseline write (increase mode)
│       │
│       ├── Phase 1: Auto Standby Configuration
│       │   └── Step 1.1: HW Configuration — Set auto standby mode → Expected: device response success
│       │
│       ├── Phase 2: Ordered Command Queue Test
│       │   └── Loop (until cmd seq buffer full)
│       │       ├── Step 2.1: WRITE(10) ORDERED — Random LBA, Random Length
│       │       └── Step 2.2: READ(10) ORDERED — Same LBA, Same Length, Compare → Expected: compare pass
│       │
│       ├── Phase 3: Simple Command Queue — Individual Tests
│       │   ├── Step 3.1: WRITE(10) SIMPLE — Random LBA, Random Length
│       │   ├── Step 3.2: READ(10) SIMPLE — Same LBA, Same Length, Compare → Expected: compare pass
│       │   ├── Step 3.3: UNMAP(0x42) SIMPLE — Random LBA, Random Length
│       │   ├── Step 3.4: READ(10) SIMPLE — Same LBA, Same Length, Compare → Expected: compare pass
│       │   ├── Step 3.5: WRITE(10) SIMPLE — Same LBA, Same Length
│       │   └── Step 3.6: READ(10) SIMPLE — Same LBA, Same Length, Compare → Expected: compare pass
│       │
│       └── Phase 4: Simple Command Queue — Buffer-Fill Loop
│           └── Loop (until cmd seq buffer full)
│               ├── Step 4.1: WRITE(10) SIMPLE — Random write
│               ├── Step 4.2: READ(10) SIMPLE — Read back, Compare → Expected: compare pass
│               ├── Step 4.3: UNMAP(0x42) SIMPLE — Random unmap
│               ├── Step 4.4: READ(10) SIMPLE — Read back, Compare → Expected: compare pass
│               ├── Step 4.5: WRITE(10) SIMPLE — Write same LBA
│               └── Step 4.6: READ(10) SIMPLE — Read back, Compare → Expected: compare pass
```

## Phase 0 — Pre-condition: Erase, Purge, Baseline Write

### Step 0.1: Erase All LUNs

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 清除所有 LUN 的既有資料，為 Purge 做準備。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | All LUNs |
| ANCHOR | 0 |
| UNMAP Parameter List Length | (covers all provisioned LBA ranges) |
| UNMAP Block Descriptor Data | All LBA ranges for each LUN |

**UFS SPEC Reference**: JESD220H Section 12.3.13 (UNMAP command), SBC-4

---

### Step 0.2: Trigger Purge Operation

**UFS QUERY**: `SET FLAG (0x02) — fPurgeEnable`

**目的**: 觸發 Purge 操作，將 UNMAP 釋放的區塊實際清除。

| Field | Value |
|-------|-------|
| Opcode | 0x02 |
| bFlagIDN | 0x06 (fPurgeEnable) |
| Flag Value | 0x01 |

**UFS SPEC Reference**: JESD220H Section 10.7.8.2 (SET FLAG), Section 14.2 (Flags)

---

### Step 0.3: Wait for Purge Completion

**UFS QUERY**: `READ ATTRIBUTE (0x03) — bBackgroundOpStatus`

**目的**: 輪詢 bBackgroundOpStatus 確認 Purge 背景操作已完成。

| Field | Value |
|-------|-------|
| Opcode | 0x03 |
| bAttrIDN | 0x14 (bBackgroundOpStatus) |
| Selector | 0x00 |

**UFS SPEC Reference**: JESD220H Section 10.7.8.3 (READ ATTRIBUTE), Section 14.3 (Attributes)

---

### Step 0.4: Baseline Write (Increase Mode)

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 以遞增模式（increase mode）對裝置寫入已知資料，作為後續 Read Compare 的基準。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | 0x00000000 (sequential, increasing) |
| Transfer Length | (device capacity, sequential fill) |
| FUA | 0 |
| DPO | 0 |

**Implementation Note**: `byGenWriteRangeCRC = 0`、`固定looptag` 為 vendor-specific 寫入參數，用於控制 CRC 產生與迴圈標記，不屬於 UFS SPEC 定義。

**UFS SPEC Reference**: JESD220H Section 12.2.4 (WRITE(10) command), SBC-4

---

## Phase 1 — Auto Standby Configuration

### Step 1.1: Set Auto Standby Mode

**Operation**: `Vendor-Specific HW Configuration`

**目的**: 設定裝置的 Auto Standby 模式（Enable 或 Disable），作為外層迴圈的測試變因。

| Field | Value |
|-------|-------|
| HW Setting Index | 1287 |
| Setting Value | 0x3B (Enable) / 0x00 (Disable) |
| API | API_dwSetDevice_HWSetting |

**Expected**: device response success

**Note**: 此為 vendor-specific 硬體設定操作，非 UFS SPEC 定義。外層迴圈會在 Enable 與 Disable 兩種模式下各執行一次完整測試。

**UFS SPEC Reference**: N/A (vendor-specific HW setting)

---

## Phase 2 — Ordered Command Queue Test

Phase 2 以 ORDERED Task Attribute 推送 Write+Read 命令對。ORDERED 屬性要求裝置必須依照推送順序執行命令，不可重排。每次迭代推送一對 WRITE → READ，並驗證讀回資料與寫入資料一致。迴圈持續推送直到命令佇列（Command Sequence Buffer）滿為止，然後一次性送出所有累積的命令。

### Step 2.1: Ordered Write — Random LBA, Random Length

**SCSI CMD**: `WRITE(10) (0x2A)` — Task Attribute: ORDERED

**目的**: 以 ORDERED attribute 推送一筆隨機 LBA、隨機長度的寫入命令至命令佇列。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | Random (within device capacity) |
| Transfer Length | Random (within available range) |
| Task Attribute | ORDERED (0b001) |
| FUA | 0 |
| DPO | 0 |

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.4 (WRITE(10))

---

### Step 2.2: Ordered Read — Same LBA, Same Length, Compare

**SCSI CMD**: `READ(10) (0x28)` — Task Attribute: ORDERED

**目的**: 以 ORDERED attribute 推送一筆讀取命令（LBA 與長度與 Step 2.1 的寫入相同），並驗證讀回資料與寫入資料一致。因為 ORDERED 屬性保證 WRITE 在 READ 前執行，資料應為最新寫入值。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | (same as Step 2.1 WRITE LBA) |
| Transfer Length | (same as Step 2.1 WRITE Length) |
| Task Attribute | ORDERED (0b001) |

**Expected**: compare pass（讀回資料與寫入資料一致）

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.3 (READ(10))

---

## Phase 3 — Simple Command Queue: Individual Tests

Phase 3 以 SIMPLE Task Attribute 執行三組操作序列，每組各執行一次，不進入迴圈。SIMPLE 屬性允許裝置任意重排執行順序，測試目的在驗證即使命令順序被重排，最終資料正確性不受影響。

### Step 3.1: Simple Write — Random LBA, Random Length

**SCSI CMD**: `WRITE(10) (0x2A)` — Task Attribute: SIMPLE

**目的**: 以 SIMPLE attribute 推送一筆隨機寫入命令。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | Random (within device capacity) |
| Transfer Length | Random (within available range) |
| Task Attribute | SIMPLE (0b000) |
| FUA | 0 |
| DPO | 0 |

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.4 (WRITE(10))

---

### Step 3.2: Simple Read — Same LBA, Same Length, Compare

**SCSI CMD**: `READ(10) (0x28)` — Task Attribute: SIMPLE

**目的**: 讀回 Step 3.1 寫入的資料並比對，驗證 SIMPLE attribute 下資料正確性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | (same as Step 3.1 WRITE LBA) |
| Transfer Length | (same as Step 3.1 WRITE Length) |
| Task Attribute | SIMPLE (0b000) |

**Expected**: compare pass（讀回資料與寫入資料一致）

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.3 (READ(10))

---

### Step 3.3: Simple Unmap — Random LBA, Random Length

**SCSI CMD**: `UNMAP (0x42)` — Task Attribute: SIMPLE

**目的**: 以 SIMPLE attribute 執行 UNMAP，釋放隨機 LBA 範圍。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | 0x00 |
| ANCHOR | 0 |
| Task Attribute | SIMPLE (0b000) |
| UNMAP Block Descriptor | Single range: Random LBA, Random Length |

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.3.13 (UNMAP)

---

### Step 3.4: Simple Read — After Unmap, Compare

**SCSI CMD**: `READ(10) (0x28)` — Task Attribute: SIMPLE

**目的**: 讀回 Step 3.3 UNMAP 範圍的資料並比對，驗證 SIMPLE attribute 下 UNMAP 後資料狀態正確。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | (same as Step 3.3 UNMAP LBA) |
| Transfer Length | (same as Step 3.3 UNMAP Length) |
| Task Attribute | SIMPLE (0b000) |

**Expected**: compare pass（讀回資料與預期一致）

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.3 (READ(10))

---

### Step 3.5: Simple Write — Same LBA and Length (Overwrite Post-Unmap)

**SCSI CMD**: `WRITE(10) (0x2A)` — Task Attribute: SIMPLE

**目的**: 以 SIMPLE attribute 在相同 LBA 位置重新寫入資料（覆蓋 UNMAP 後的區域）。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | (same as Step 3.3 UNMAP LBA) |
| Transfer Length | (same as Step 3.3 UNMAP Length) |
| Task Attribute | SIMPLE (0b000) |
| FUA | 0 |
| DPO | 0 |

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.4 (WRITE(10))

---

### Step 3.6: Simple Read — After Re-Write, Compare

**SCSI CMD**: `READ(10) (0x28)` — Task Attribute: SIMPLE

**目的**: 讀回 Step 3.5 重新寫入的資料並比對，驗證 UNMAP 後重新寫入的資料正確。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | (same as Step 3.5 WRITE LBA) |
| Transfer Length | (same as Step 3.5 WRITE Length) |
| Task Attribute | SIMPLE (0b000) |

**Expected**: compare pass（讀回資料與寫入資料一致）

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.3 (READ(10))

---

## Phase 4 — Simple Command Queue: Buffer-Fill Loop

Phase 4 重複 Phase 3 的三組 Simple Command 操作模式（Write→Read、Unmap→Read、Write→Read），但以迴圈持續推送直到命令佇列滿。此階段驗證大量 SIMPLE 命令堆疊時裝置的排程穩定性與資料正確性。

### Step 4.1: Simple Write — Buffer-Fill Loop Iteration

**SCSI CMD**: `WRITE(10) (0x2A)` — Task Attribute: SIMPLE

**目的**: 在 Buffer-Fill 迴圈中推送 SIMPLE 寫入命令。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | Random (within device capacity) |
| Transfer Length | Random (within available range) |
| Task Attribute | SIMPLE (0b000) |
| FUA | 0 |
| DPO | 0 |

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.4 (WRITE(10))

---

### Step 4.2: Simple Read — Buffer-Fill Loop Iteration, Compare

**SCSI CMD**: `READ(10) (0x28)` — Task Attribute: SIMPLE

**目的**: 讀回 Step 4.1 寫入的資料並比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | (same as Step 4.1 WRITE LBA) |
| Transfer Length | (same as Step 4.1 WRITE Length) |
| Task Attribute | SIMPLE (0b000) |

**Expected**: compare pass（讀回資料與寫入資料一致）

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.3 (READ(10))

---

### Step 4.3: Simple Unmap — Buffer-Fill Loop Iteration

**SCSI CMD**: `UNMAP (0x42)` — Task Attribute: SIMPLE

**目的**: 在 Buffer-Fill 迴圈中推送 SIMPLE UNMAP 命令。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | 0x00 |
| ANCHOR | 0 |
| Task Attribute | SIMPLE (0b000) |
| UNMAP Block Descriptor | Single range: Random LBA, Random Length |

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.3.13 (UNMAP)

---

### Step 4.4: Simple Read — After Unmap, Compare

**SCSI CMD**: `READ(10) (0x28)` — Task Attribute: SIMPLE

**目的**: 讀回 Step 4.3 UNMAP 範圍的資料並比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | (same as Step 4.3 UNMAP LBA) |
| Transfer Length | (same as Step 4.3 UNMAP Length) |
| Task Attribute | SIMPLE (0b000) |

**Expected**: compare pass（讀回資料與預期一致）

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.3 (READ(10))

---

### Step 4.5: Simple Write — Same LBA Re-Write

**SCSI CMD**: `WRITE(10) (0x2A)` — Task Attribute: SIMPLE

**目的**: 在 Buffer-Fill 迴圈中以相同 LBA 重新寫入資料。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | (same as Step 4.3 UNMAP LBA) |
| Transfer Length | (same as Step 4.3 UNMAP Length) |
| Task Attribute | SIMPLE (0b000) |
| FUA | 0 |
| DPO | 0 |

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.4 (WRITE(10))

---

### Step 4.6: Simple Read — After Re-Write, Compare

**SCSI CMD**: `READ(10) (0x28)` — Task Attribute: SIMPLE

**目的**: 讀回 Step 4.5 重新寫入的資料並比對。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| LBA | (same as Step 4.5 WRITE LBA) |
| Transfer Length | (same as Step 4.5 WRITE Length) |
| Task Attribute | SIMPLE (0b000) |

**Expected**: compare pass（讀回資料與寫入資料一致）

**UFS SPEC Reference**: JESD220H Section 10.7 (Command UPIU — Task Attribute field), Section 12.2.3 (READ(10))

---

## 附錄 A — UFS Query IDN 對照表

| Query Type | Opcode | IDN | Name | Size (bytes) | Access | Description |
|:---|:---|:---|:---|:---|:---|:---|
| SET FLAG | 0x02 | 0x06 | fPurgeEnable | 1 | R/W | 觸發 Purge 背景清除操作 |
| READ ATTRIBUTE | 0x03 | 0x14 | bBackgroundOpStatus | 1 | Read-Only | 背景操作完成狀態（90h=idle, 其他=進行中） |

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | Task Attribute | Use in This Pattern |
|:---|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | ORDERED / SIMPLE | 讀取並比對資料，驗證命令排程正確性 |
| 0x2A | WRITE(10) | 10 | ORDERED / SIMPLE | 寫入測試資料（baseline / random / re-write） |
| 0x42 | UNMAP | 10 | SIMPLE | 釋放 LBA 範圍，搭配 SIMPLE attribute 測試 |

### Task Attribute 說明（JESD220H Section 10.7, Command UPIU）

| Value | Name | Behavior |
|:---|:---|:---|
| 0b000 | SIMPLE | 裝置可任意重排執行順序 |
| 0b001 | ORDERED | 必須依照推送順序執行，不可重排 |
| 0b010 | HEAD OF QUEUE | 優先於佇列中所有命令執行 |
| 0b011 | ACA | Auto-Contingent Allegiance（本 pattern 未使用） |

## 附錄 C — UFS Reset 類型說明

（本 pattern 未使用任何 Reset 操作，故省略此附錄）

---

## 自我驗證

- Tree Diagram leaf steps: **19**
  Phase 0: 4 (0.1~0.4), Phase 1: 1 (1.1), Phase 2: 2 (2.1~2.2), Phase 3: 6 (3.1~3.6), Phase 4: 6 (4.1~4.6) → Total: 19
- `### Step` sections: **19** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（共 8 個 step 有 Expected）

  Expected 追溯表：

  | Step | Expected 值 | JIRA 來源 |
  |:---|:---|:---|
  | 1.1 | device response success | Raw Step 2: "Expected device response success" |
  | 2.2 | compare pass | Raw Step 3: "Expected compare pass" |
  | 3.2 | compare pass | Raw Step 6: "Expected compare pass" |
  | 3.4 | compare pass | Raw Step 8: "Expected compare pass" |
  | 3.6 | compare pass | Raw Step 10: "Expected compare pass" |
  | 4.2 | compare pass | Raw Step 10 via Step 11 loop (flows carry Expected from source) |
  | 4.4 | compare pass | Raw Step 8 via Step 11 loop (flows carry Expected from source) |
  | 4.6 | compare pass | Raw Step 10 via Step 11 loop (flows carry Expected from source) |

- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
