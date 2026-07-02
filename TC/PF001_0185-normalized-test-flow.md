---
title: PF001_0185_BKOP_POR_Test-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf001_0185, scsi-cmd, bkop, por, reset]
description: >
  驗證在 BKOP（Background Operations）可能觸發的條件下，多次 POR Reset 後的
  資料完整性。測試以 3 個回合執行：每回合 Erase all → 循環寫入（1M~512M 隨機大小）
  + 隨機延遲 + 隨機 POR → Read back 比對，直到填滿整個裝置容量後，
  最終全碟讀回比對。
sources:
  - JIRA: PF001_0185 (SYSTCUFS-13)
  - UFS Spec: JESD220H Section 10.7.8 (QUERY), 11.2 (SCSI Commands), 14.2 (Flags)
---

# PF001_0185 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置在 BKOP 觸發條件滿足的環境中（Idle 100ms、Dynamic SLC 已寫過閾值、
Free Block 低於閾值），經多次 POR Reset（HW Reset / RST_n / EndPoint Reset / 
UniPro Reset）後，資料完整性不受影響。

測試以 3 個回合執行，每回合將裝置填滿後全碟比對，確保資料在 BKOP + POR 交錯壓力下
保持正確。

## BKOP 觸發條件（背景資訊）

JIRA Pattern 列出以下 BKOP 觸發條件作為測試環境背景（非測試步驟）：

1. **Idle 100ms** — 韌體在閒置 100ms 後觸發 BKOP
2. **Dynamic SLC 已寫過** — 每個 CE 配置對應容量（如 4CE → 4GB）的 Dynamic SLC 需先寫過
3. **Free Block 低於閾值** — Good Block - Static SLC Block（system 區，存 table）- 預留 10 Block

這些條件在測試過程中自然達成：持續寫入消耗 Free Block、Dynamic SLC 被寫入、
POR 後裝置 Recovery 期間有 Idle 時段。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1, 8, 15 | Erase all | Step 1: UNMAP(42h) — Erase all LBAs（每回合） |
| Step 2, 9, 16 | Random write 1M ~512M | Step 2: WRITE(10)(2Ah) — Random write |
| Step 3, 10, 17 | Random delay from 1 sec to 5 sec | Step 3: Idle — Random delay 1~5 sec |
| Step 4, 11, 18 | Random POR (HW reset, RSTn, EndPoint reset, UniPro reset) | Step 4: Random POR Reset |
| Step 5, 12, 19 | Read & Cmp | Step 5: READ(10)(28h) — Read back & data compare |
| Step 6, 13, 20 | Go to step 2 when cumulative data size != card size | Inner Loop condition |
| Step 7, 14, 21 | Read & Cmp all | Step 6: READ(10)(28h) — Read all written data & compare |
| Step 22~24 | BKOP 觸發條件 | 背景資訊（非測試步驟） |

---

## 測試架構（Tree Diagram）

```
PF001_0185 Test Flow
│
├── Phase 0: Initial Setup
│   ├── Step 0.1: TEST UNIT READY(00h) — Check device readiness
│   └── Step 0.2: READ CAPACITY(10)(25h) — Get device capacity
│
└── Loop (3 rounds)
    └── Round
        │
        ├── Phase 1: Erase All
        │   └── Step 1: UNMAP(42h) — Erase all LBAs
        │
        ├── Inner Loop (cumulative data size < device capacity)
        │   │
        │   └── Phase 2: Write → Delay → POR → Verify
        │       ├── Step 2: WRITE(10)(2Ah) — Random write 1M~512M
        │       ├── Step 3: Idle — Random delay 1~5 sec
        │       ├── Step 4: Random POR Reset — HW / RST_n / EndPoint / UniPro
        │       └── Step 5: READ(10)(28h) — Read back & data compare
        │
        └── Phase 3: Full Read & Compare All
            └── Step 6: READ(10)(28h) — Read all written data & compare
```

---

## Phase 0 — Initial Setup

### Step 0.1: Check Device Readiness

**SCSI CMD**: `TEST UNIT READY (00h)`

**目的**: 確認裝置上電後處於可操作狀態。

| Field | Value |
|-------|-------|
| Opcode | 0x00 |
| LUN | 0x00 |

**UFS SPEC Reference**: JESD220H Section 11.2.1 (TEST UNIT READY)

---

### Step 0.2: Get Device Capacity

**SCSI CMD**: `READ CAPACITY(10) (25h)`

**目的**: 取得裝置邏輯區塊容量（Logical Block Address 上限 + Block Length），
作為後續 Inner Loop 的終止條件（cumulative data size >= device capacity）。

| Field | Value |
|-------|-------|
| Opcode | 0x25 |
| LUN | 0x00 |
| CDB[2-5] | 0x00000000 (LBA=0) |
| CDB[6-7] | 0x0000 (PMI=0) |
| Allocation Length | 8 bytes |

**UFS SPEC Reference**: JESD220H Section 11.2.3 (READ CAPACITY(10))

---

## Phase 1 — Erase All（每回合執行）

### Step 1: Erase All LBAs

**SCSI CMD**: `UNMAP (42h)`

**目的**: 清除所有先前寫入的資料，將所有 LBA 恢復為未分配狀態，準備新回合的寫入。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | 0x00 |
| CDB[1] | 0x00 (ANCHOR=0) |
| CDB[8-9] | Parameter List Length (UNMAP block descriptor 長度) |
| UNMAP LBA Range | LBA=0, LBA Count=Device Capacity（全碟範圍） |

**UFS SPEC Reference**: JESD220H Section 11.2.27 (UNMAP)

---

## Phase 2 — Write → Delay → POR → Verify（Inner Loop，填滿裝置）

### Step 2: Random Write

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 以隨機大小的資料（1M ~ 512M）寫入下一個未使用的 LBA 區段，
累積 cumulative data size。

**Branch Logic**:
- Size: 隨機範圍 1 MiB ~ 512 MiB
- LBA: 基於當前 cumulative data size 計算起始 LBA（循序遞增寫入）
- Data Pattern: 可驗證的隨機資料（用於後續 Read & Compare）

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| CDB[2-5] | 基於 cumulative data size 的起始 LBA |
| CDB[7-8] | Transfer Length（= write_size / BlockLength） |
| FUA | 0 (無須強制 flush，後續有 POR) |
| DataOut Buffer | write_size bytes（含可驗證 pattern） |

**UFS SPEC Reference**: JESD220H Section 11.2.12 (WRITE(10))

---

### Step 3: Random Idle Delay

**操作**: Idle / Sleep

**目的**: 寫入後提供隨機閒置時間（1~5 秒），使裝置有機會觸發 BKOP
（滿足 Idle 100ms 條件）或進入內部管理狀態，增加 POR Reset 前的變化性。

| Parameter | Value |
|-----------|-------|
| Duration | Random 1 ~ 5 seconds |
| 方式 | 主機端等待（不發送 SCSI CMD），讓 UFS 進入 Idle |

**UFS SPEC Reference**: N/A（主機端延遲，非 UFS 標準操作）

---

### Step 4: Random POR Reset

**操作**: Reset（非 SCSI CMD，屬 UFS UPIU / DME 層級操作）

**目的**: 在不預警的情況下觸發隨機類型的 POR Reset，模擬真實掉電場景，
驗證裝置在 BKOP 進行中遭遇 Reset 後仍能正確恢復。

**Branch Logic**（等權重隨機選擇）:
- Case A: **HW Reset** — 硬體 RESET 訊號
- Case B: **RST_n Reset** — RST_n 腳位觸發
- Case C: **EndPoint Reset** — UFS UniPro EndPoint Reset
- Case D: **UniPro Reset** — UniPro Link Reset

| Parameter | Value |
|-----------|-------|
| Reset Type | Random: HW_RESET / RST_n / EndPoint / UniPro |
| 後續動作 | 等待 fDeviceInit Flag == 0（裝置重新初始化完成） |

**UFS SPEC Reference**: JESD220H Section 10.3 (Reset), 14.2.1 (fDeviceInit Flag)

---

### Step 5: Read Back & Data Compare

**SCSI CMD**: `READ(10) (28h)`

**目的**: 讀回本回合剛寫入的資料區段，與寫入時的 Data Pattern 比對，
驗證 POR Reset 後資料未受損壞。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| CDB[2-5] | 與對應 WRITE(10) 步驟相同的起始 LBA |
| CDB[7-8] | Transfer Length（與對應 WRITE 步驟相同長度） |
| DataIn Buffer | 讀回的資料 |

**Compare**: Host 端比對讀回資料與寫入時的 Data Pattern，逐 byte 驗證。

**UFS SPEC Reference**: JESD220H Section 11.2.11 (READ(10))

---

## Phase 3 — Full Read & Compare All（每回合結束後）

### Step 6: Read All Written Data & Compare

**SCSI CMD**: `READ(10) (28h)`

**目的**: 當 cumulative data size 達到裝置總容量（Inner Loop 結束）後，
讀回所有已寫入的 LBA 資料並與原始 Data Pattern 進行全碟比對。
此步驟確認在多次 POR Reset 後所有資料完整無誤。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0x00 |
| CDB[2-5] | LBA=0（從起始 LBA 開始） |
| CDB[7-8] | Transfer Length = Device Capacity（全碟讀取） |
| DataIn Buffer | 全碟資料 |

**Compare**: Host 端比對所有讀回資料與寫入時的 Data Pattern，逐 byte 驗證。

**UFS SPEC Reference**: JESD220H Section 11.2.11 (READ(10))

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

本 Pattern 僅使用 fDeviceInit Flag 查詢確認 Reset 後裝置初始完成。

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x01 | fDeviceInit | Read-Only (No) | POR Reset 後查詢裝置初始化狀態，fDeviceInit == 0 表示 Ready，確認 Ready 後方可繼續操作 |

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x01 | READ FLAG | 讀取 fDeviceInit 確認 Reset 後恢復完成 |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x00 | TEST UNIT READY | 6 | Phase 0 — 確認裝置可操作 |
| 0x25 | READ CAPACITY(10) | 10 | Phase 0 — 取得裝置容量 |
| 0x42 | UNMAP | 10 | Phase 1 — Erase all LBAs |
| 0x2A | WRITE(10) | 10 | Phase 2 — 隨機寫入 1M~512M |
| 0x28 | READ(10) | 10 | Phase 2/3 — 讀回比對 |

---

## 附錄 C — UFS Reset 類型說明

本 Pattern 使用的四種 Reset 類型（JESD220H Section 10.3）：

| Reset Type | 說明 | JESD220H Reference |
|:---|:---|:---|
| HW_RESET | 硬體 RESET 訊號，完全重置裝置硬體 | Section 10.3.1 |
| RST_n Reset | RST_n 腳位觸發，硬體重置 | Section 10.3.1 |
| EndPoint Reset | UniPro EndPoint 層級重置，不影響 Link | Section 10.3.2 |
| UniPro Reset | UniPro Link 層級重置，M-PHY + UniPro 重新初始化 | Section 10.3.2 |

所有 Reset 後需確認 `fDeviceInit Flag == 0` 表示裝置初始化完成。

---

## 自我驗證

- Tree Diagram leaf steps: **8**（Phase 0: 2 (0.1~0.2), Phase 1: 1 (Step 1), Phase 2: 4 (Step 2~5), Phase 3: 1 (Step 6) → Total: 8）
- `### Step` sections: **8** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（本 Pattern 無 Expected — JIRA 所有 Step 的 Note 欄位均為空白，未描述任何預期結果）
- 無憑空生成的 Expected 值 ✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
