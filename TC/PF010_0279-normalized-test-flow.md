---
title: PF010_0279_QD1_SeqR_PreRead_Test-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf010_0279, scsi-cmd, pre-read, sequential-read, burn-in]
description: >
  驗證 UFS 裝置在 QD1 Sequential Read 操作下 PreRead 功能的行為。
  測試包含 24 小時燒機 loop，在 loop 內交替執行 QD1 Sequential Read（固定 8KB）
  與隨機分支操作（Sequential Read、Random Read、Write、Erase、Sync Cache、
  POR、Config LUN 等），並驗證各操作對 PreRead 觸發與否的預期行為。
sources:
  - JIRA: PF010_0279 (SYSTCUFS-62)
  - UFS Spec: JESD220H Section 10.7.1, 10.7.3, 10.7.8-10.7.9
---

# PF010_0279 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置在 QD1（Queue Depth 1）Sequential Read 操作下，PreRead 功能的觸發行為。
核心驗證點：
- QD1 Sequential Read 應觸發 PreRead 機制，且資料比對正確
- 非 Sequential Read 操作（Random Read、Write、Erase、TMF、Sync Cache、POR、Config LUN）不應觸發 PreRead
- 24 小時連續燒機下行為穩定

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Flow-1 | Measure idle current | Phase 0 — Step 0.1 |
| Flow-2 | Write all LUN | Phase 0 — Step 0.2 |
| Flow-3 | QD1 Sequential Read with 8k Chuck Size and Compare data | Phase 1 — Step 1.1（24hr Loop 內） |
| Flow-4 | Half chance Pattern idle (device auto STB) | Phase 2 — Step 2.1（50% 機率，24hr Loop 內） |
| Step 2 (Flow-4) | QD1 Sequential Read with Random Chuck Size and Compare data | Branch A — Step 2A.1 |
| Step 3 (Flow-4) | Task Management test | Branch B — Step 2B.1 |
| Step 4 (Flow-4) | QD1 Random Read with Random Chuck Size and Compare data | Branch C — Step 2C.1 |
| Step 5 (Flow-4) | Rand QD Random Read with Random Chuck Size and Compare data | Branch D — Step 2D.1 |
| Step 6 (Flow-4) | Random Write with Random Chuck Size and Compare data | Branch E — Step 2E.1, 2E.2 |
| Step 7 (Flow-4) | Random Erase with Random Chuck Size and Compare data | Branch F — Step 2F.1, 2F.2 |
| Step 8 (Flow-4) | Sync Cache | Branch G — Step 2G.1 |
| Step 9 (Flow-4) | POR and after POR Compare data | Branch H — Step 2H.1, 2H.2 |
| Step 10 (Flow-4) | Config LUN and Compare data | Branch I — Step 2I.1, 2I.2 |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF010_0279 Test Flow
│
├── Phase 0: Pre-condition（一次性執行）
│   ├── Step 0.1: Hardware Measurement — Measure Idle Current
│   └── Step 0.2: WRITE(10) — Write Sequential Data to All LUNs, Full LBA Range
│
└── Loop (24hr burn-in)
    │
    ├── Phase 1: QD1 Sequential Read（Fixed 8KB）
    │   └── Step 1.1: READ(10) — QD1 Sequential Read, TL=16 (8KB), Compare Data
    │         → Expected: Pre-read activated, data compare pass
    │
    └── Phase 2: Pattern Idle & Random Branch
        │
        ├── Step 2.1: [50%] Hardware Measurement — Idle + Measure Current（device auto STB）
        │
        ├── [Branch A] QD1 Sequential Read Random Size
        │   └── Step 2A.1: READ(10) — QD1 Sequential Read, Random Transfer Length, Compare Data
        │         → Expected: Pre-read activated, data compare pass
        │
        ├── [Branch B] Task Management Test
        │   └── Step 2B.1: TMF — Task Management Function
        │         → Expected: Pre-read NOT activated
        │
        ├── [Branch C] QD1 Random Read
        │   └── Step 2C.1: READ(10) — QD1 Random Read, Random LBA, Random Transfer Length, Compare Data
        │         → Expected: Pre-read NOT activated, data compare pass
        │
        ├── [Branch D] Rand QD Random Read
        │   └── Step 2D.1: READ(10) — Random QD Random Read, Random LBA, Random Transfer Length, Compare Data
        │         → Expected: Pre-read NOT activated, data compare pass
        │
        ├── [Branch E] Random Write + Compare
        │   ├── Step 2E.1: WRITE(10) — Random Write, Random LBA, Random Transfer Length
        │   │     → Expected: Pre-read NOT activated
        │   └── Step 2E.2: READ(10) — Read Back and Compare Data
        │         → Expected: data compare pass
        │
        ├── [Branch F] Random Erase + Compare
        │   ├── Step 2F.1: UNMAP(10) — Random Erase (Unmap), Random LBA, Random Transfer Length
        │   │     → Expected: Pre-read NOT activated
        │   └── Step 2F.2: READ(10) — Read Back and Verify Data Erased
        │         → Expected: data compare pass
        │
        ├── [Branch G] Sync Cache
        │   └── Step 2G.1: SYNCHRONIZE CACHE(10)
        │         → Expected: Pre-read NOT activated, data compare pass
        │
        ├── [Branch H] POR + Compare
        │   ├── Step 2H.1: POR — Power On Reset
        │   └── Step 2H.2: READ(10) — Compare Data After POR
        │         → Expected: Pre-read NOT activated, data compare pass
        │
        └── [Branch I] Config LUN + Compare
            ├── Step 2I.1: WRITE DESCRIPTOR — Re-Configure LUN (Unit Descriptor)
            │     → Expected: Pre-read NOT activated
            └── Step 2I.2: READ(10) — Read Back, Verify Data is Zero
                  → Expected: data is 0
```

**Expected 格式說明：**
- `→ Expected: Pre-read activated` — 預期裝置啟動 PreRead 機制
- `→ Expected: Pre-read NOT activated` — 預期裝置不啟動 PreRead 機制
- `→ Expected: data compare pass` — 預期讀取資料與寫入資料比對正確
- `→ Expected: data is 0` — 預期讀取資料全為 0

---

## Phase 0 — Pre-condition（一次性執行，不在 24hr Loop 內）

### Step 0.1: Measure Idle Current

**Hardware Measurement**

**目的**: 量測裝置在 idle state 下的基準電流值，作為後續 Auto STB 電流比對的參考。

| Field | Value |
|-------|-------|
| 量測對象 | Device Idle Current |
| 量測時機 | 裝置上電初始化完成後，無任何 pending command |

**Note**: 此為硬體量測步驟，非 SCSI CMD 或 UFS Query。量測結果記錄為基準值，供 Phase 2 Step 2.1 比對使用。

---

### Step 0.2: Write Sequential Data to All LUNs

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對所有 active LUN 寫入連續測試資料（Sequential pattern），建立後續 Read Compare 的比對基準。寫入範圍涵蓋整個 LBA 空間。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 所有 active LUN（依序寫入） |
| Logical Block Address | 0x00000000 |
| Transfer Length | LUN 容量（Full LBA Range） |
| Data Pattern | 已知測試 pattern（供後續 Compare 使用） |
| Queue Depth | QD1 |

**UFS SPEC Reference**: JESD220H Section 10.7.1（SCSI Command over UFS Transport Protocol）；SBC-4 WRITE(10)

---

## Loop — 24hr Burn-in

以下 Phase 1 和 Phase 2 在 24 小時內重複執行。每個 loop iteration 依序執行 Phase 1 → Phase 2。

---

## Phase 1 — QD1 Sequential Read（Fixed 8KB）

### Step 1.1: QD1 Sequential Read with 8KB Chuck Size

**SCSI CMD**: `READ(10) (28h)`

**目的**: 以 QD1 對裝置發出 Sequential Read（循序讀取），Chuck Size 固定為 8KB（16 blocks）。驗證裝置在此條件下啟動 PreRead 機制，且讀回資料與原始寫入資料一致。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Active LUN |
| Logical Block Address | Sequential（接續上次讀取位置） |
| Transfer Length | 16（8KB = 16 × 512B） |
| Queue Depth | QD1 |
| Read Type | Sequential |
| Data Compare | 與 Phase 0 Step 0.2 寫入之測試 pattern 比對 |

**Expected**: Pre-read activated, data compare pass。

**Note**: JIRA 原文 —「預期啟動Pre-read，且預期data compare pass」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 READ(10)

---

## Phase 2 — Pattern Idle & Random Branch

此 Phase 包含一個 50% 機率的 Idle 步驟（Step 2.1），隨後從 Branch A–I 中隨機選取一個分支執行。

**Branch Logic**（per JIRA）：
- 每次 loop iteration 從 Branch A ~ I 中隨機選一個分支執行
- JIRA 未指定各分支權重，採用均等機率分配（各 ~11.1%）

---

### Step 2.1: [50%] Idle + Measure Current（Device Auto STB）

**Hardware Measurement**

**目的**: 50% 機率讓 Pattern 進入 idle 狀態，等待裝置進入 Auto Standby（Auto STB）。透過量測電流確認裝置是否進入 Auto STB 模式（比對 Phase 0 Step 0.1 基準電流值）。

| Field | Value |
|-------|-------|
| 執行機率 | 50%（Half chance） |
| Idle 持續時間 | 等待裝置進入 Auto STB |
| 量測對象 | Device Current（與 Phase 0 Step 0.1 基準值比對） |
| 驗證方式 | 電流值低於基準 idle 電流 → Auto STB entered |

**Note**: 此為硬體量測步驟。若未進入此分支（50% 機率），直接跳到隨機選擇的 Branch A–I。

---

## Branch A — QD1 Sequential Read Random Size

### Step 2A.1: QD1 Sequential Read with Random Chuck Size

**SCSI CMD**: `READ(10) (28h)`

**目的**: 以 QD1 對裝置發出 Sequential Read，Chuck Size 為隨機值。驗證裝置在 Sequential Read 條件下仍應啟動 PreRead 機制。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Active LUN |
| Logical Block Address | Sequential（接續上次讀取位置） |
| Transfer Length | Random（隨機值，範圍：[1, max_blocks_per_cmd]） |
| Queue Depth | QD1 |
| Read Type | Sequential |
| Data Compare | 與 Phase 0 Step 0.2 寫入之測試 pattern 比對 |

**Expected**: Pre-read activated, data compare pass。

**Note**: JIRA 原文 —「預期啟動Pre-read，且預期data compare pass」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 READ(10)

---

## Branch B — Task Management Test

### Step 2B.1: Task Management Function

**TMF**: Task Management Function

**目的**: 發送 Task Management Function（TMF）至裝置。驗證 TMF 操作不應觸發 PreRead 機制。

| Field | Value |
|-------|-------|
| Function | Task Management Function（TMF） |
| TMF Type | JIRA 未指定具體 TMF 類型；含 ABORT TASK、LOGICAL UNIT RESET、CLEAR TASK SET 等 |

**Expected**: Pre-read NOT activated。

**Note**: JIRA 原文 —「預期不啟動Pre-read」。JIRA 未指定具體 TMF 類型，實際測試可涵蓋多種 TMF。

**UFS SPEC Reference**: JESD220H Section 10.7.3（Task Management）；SAM-5

---

## Branch C — QD1 Random Read

### Step 2C.1: QD1 Random Read with Random Chuck Size

**SCSI CMD**: `READ(10) (28h)`

**目的**: 以 QD1 對裝置發出 Random Read（隨機 LBA），Chuck Size 為隨機值。驗證 Random Read 不應觸發 PreRead 機制。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Active LUN |
| Logical Block Address | Random（隨機 LBA，在有效 LBA 範圍內） |
| Transfer Length | Random（隨機值） |
| Queue Depth | QD1 |
| Read Type | Random |
| Data Compare | 與 Phase 0 Step 0.2 寫入之測試 pattern 比對 |

**Expected**: Pre-read NOT activated, data compare pass。

**Note**: JIRA 原文 —「預期不啟動Pre-read，且預期data compare pass」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 READ(10)

---

## Branch D — Rand QD Random Read

### Step 2D.1: Random QD Random Read with Random Chuck Size

**SCSI CMD**: `READ(10) (28h)`

**目的**: 以隨機 Queue Depth（非固定 QD1）對裝置發出 Random Read（隨機 LBA），Chuck Size 為隨機值。驗證非 QD1 的 Random Read 不應觸發 PreRead 機制。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Active LUN |
| Logical Block Address | Random（隨機 LBA） |
| Transfer Length | Random（隨機值） |
| Queue Depth | Random QD（非固定 QD1，e.g. QD2~QD32 隨機） |
| Read Type | Random |
| Data Compare | 與 Phase 0 Step 0.2 寫入之測試 pattern 比對 |

**Expected**: Pre-read NOT activated, data compare pass。

**Note**: JIRA 原文 —「預期不啟動Pre-read，且預期data compare pass」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 READ(10)

---

## Branch E — Random Write + Compare

### Step 2E.1: Random Write with Random Chuck Size

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對隨機 LBA 寫入隨機大小的資料。驗證 Write 操作不應觸發 PreRead 機制。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | Active LUN |
| Logical Block Address | Random（隨機 LBA） |
| Transfer Length | Random（隨機值） |
| Data Pattern | 已知測試 pattern（記錄供後續 Step 2E.2 比對） |

**Expected**: Pre-read NOT activated。

**Note**: JIRA 原文 —「預期不啟動Pre-read，且預期data compare pass」。其中「data compare pass」歸屬於 Step 2E.2。

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 WRITE(10)

---

### Step 2E.2: Read Back and Compare Data

**SCSI CMD**: `READ(10) (28h)`

**目的**: 讀回 Step 2E.1 寫入之 LBA 範圍，比對資料是否正確。驗證 Write 後資料一致性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Active LUN |
| Logical Block Address | 與 Step 2E.1 相同（寫入之 LBA 範圍） |
| Transfer Length | 與 Step 2E.1 相同 |
| Queue Depth | QD1 |
| Data Compare | 與 Step 2E.1 寫入之測試 pattern 比對 |

**Expected**: data compare pass。

**Note**: JIRA 原文分支預期 —「預期data compare pass」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 READ(10)

---

## Branch F — Random Erase + Compare

### Step 2F.1: Random Erase (Unmap) with Random Chuck Size

**SCSI CMD**: `UNMAP(10) (42h)`

**目的**: 對隨機 LBA 範圍執行 Unmap（Erase）操作。驗證 Erase 操作不應觸發 PreRead 機制。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | Active LUN |
| UNMAP LBA Range | Random（隨機 LBA 起點 + 隨機長度） |
| Transfer Length | Random（隨機值，表示 Unmap 的 block 數量） |

**Expected**: Pre-read NOT activated。

**Note**: JIRA 原文 —「預期不啟動Pre-read，且預期data compare pass」。其中「data compare pass」歸屬於 Step 2F.2。

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 UNMAP

---

### Step 2F.2: Read Back and Verify Data Erased

**SCSI CMD**: `READ(10) (28h)`

**目的**: 讀回 Step 2F.1 Unmap 之 LBA 範圍，驗證資料已被清除（Unmapped LBA 應回傳特定 pattern，如全零或 vendor-specific 值）。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Active LUN |
| Logical Block Address | 與 Step 2F.1 Unmap 範圍相同 |
| Transfer Length | 與 Step 2F.1 相同 |
| Queue Depth | QD1 |
| Data Compare | 與 erased 預期值比對（unmapped LBA 之回傳 pattern） |

**Expected**: data compare pass。

**Note**: JIRA 原文分支預期 —「預期data compare pass」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 READ(10)

---

## Branch G — Sync Cache

### Step 2G.1: Synchronize Cache

**SCSI CMD**: `SYNCHRONIZE CACHE(10) (35h)`

**目的**: 對裝置發出 Sync Cache 命令，確保所有 cached data 寫入 NAND。驗證 Sync Cache 操作不應觸發 PreRead 機制。

| Field | Value |
|-------|-------|
| Opcode | 0x35 |
| LUN | Active LUN |
| Logical Block Address | 0x00000000 |
| Number of Blocks | 0x0000（flush entire cache） |
| Immediate (Immed) | 0（wait for completion） |

**Expected**: Pre-read NOT activated, data compare pass。

**Note**: JIRA 原文 —「預期不啟動Pre-read，且預期data compare pass」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 SYNCHRONIZE CACHE(10)

---

## Branch H — POR + Compare

### Step 2H.1: Power On Reset (POR)

**Hardware Operation**: Power On Reset

**目的**: 對裝置執行 Power On Reset（斷電再上電）。POR 後裝置回到初始狀態。

| Field | Value |
|-------|-------|
| Reset 類型 | POR（Power On Reset） |
| 操作方式 | 裝置斷電後重新上電 |

**Note**: JIRA 原文分支預期 —「預期不啟動Pre-read，且預期data compare pass」。PreRead 預期歸屬於 Step 2H.2（POR 後的 Read 操作），data compare pass 亦歸屬於 Step 2H.2。

**UFS SPEC Reference**: JESD220H Section 10.4（Power Management / Reset）

---

### Step 2H.2: Compare Data After POR

**SCSI CMD**: `READ(10) (28h)`

**目的**: 裝置完成 POR 後，讀回先前寫入之 LBA 範圍資料進行比對。驗證 POR 後資料完整性，以及 POR 後的 Read 操作不應觸發 PreRead 機制。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Active LUN |
| Logical Block Address | 與 Phase 0 Step 0.2 寫入範圍相同（或上次變更後的有效 LBA） |
| Transfer Length | 對應 LBA 範圍 |
| Queue Depth | QD1 |
| Data Compare | 與 Phase 0 Step 0.2 寫入之測試 pattern 比對 |

**Expected**: Pre-read NOT activated, data compare pass。

**Note**: JIRA 原文 —「預期不啟動Pre-read，且預期data compare pass」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 READ(10)

---

## Branch I — Config LUN + Compare

### Step 2I.1: Re-Configure LUN

**UFS QUERY**: `WRITE DESCRIPTOR (08h)` — Unit Descriptor

**目的**: 對 LUN 重新配置（修改 Unit Descriptor）。驗證 Config LUN 操作不應觸發 PreRead 機制。重新配置後 LUN 資料應被清除。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08（WRITE DESCRIPTOR） |
| Descriptor Type | Unit Descriptor |
| Descriptor IDN | 對應 LUN 之 Unit Descriptor IDN |
| bLUEnable | 依測試需求配置（如 Disable → Enable） |

**Expected**: Pre-read NOT activated。

**Note**: JIRA 原文 —「預期不啟動Pre-read，且預期data為0」。其中「data is 0」歸屬於 Step 2I.2。JIRA 未指定具體 LUN 配置方式（如 toggle bLUEnable 或修改 bMemoryType），實作時可依需求選擇。

**UFS SPEC Reference**: JESD220H Section 10.7.9.8（WRITE DESCRIPTOR）；Section 14.1.6.3（Unit Descriptor）

---

### Step 2I.2: Read Back and Verify Data is Zero

**SCSI CMD**: `READ(10) (28h)`

**目的**: 完成 LUN 重新配置後，讀回該 LUN 資料。驗證重新配置後 LUN 資料全為 0。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 被重新配置的 LUN |
| Logical Block Address | 0x00000000 |
| Transfer Length | LUN 容量（Full LBA Range） |
| Queue Depth | QD1 |
| Data Compare | 預期所有讀回資料為 0x00 |

**Expected**: data is 0。

**Note**: JIRA 原文 —「預期data為0」

**UFS SPEC Reference**: JESD220H Section 10.7.1；SBC-4 READ(10)

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x08 | WRITE DESCRIPTOR | Config LUN：寫入 Unit Descriptor（Branch I） |

### Descriptor IDN

| IDN | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| — | Unit Descriptor | Branch I — Config LUN：修改 LUN 配置（bLUEnable 等） |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB Size | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | Phase 1 / Branch A/C/D/E/F/G/H/I — Sequential/Random Read + Data Compare |
| 0x2A | WRITE(10) | 10 | Phase 0 — Write All LUN；Branch E — Random Write |
| 0x35 | SYNCHRONIZE CACHE(10) | 10 | Branch G — Sync Cache |
| 0x42 | UNMAP(10) | 10 | Branch F — Random Erase (Unmap) |

### Task Management

| 類型 | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| TMF | Task Management Function | Branch B — Task Management Test（ABORT TASK / LOGICAL UNIT RESET / CLEAR TASK SET 等） |

---

## 附錄 C — 本 Pattern 使用的 Reset 類型

| 類型 | 簡稱 | 此 Pattern 使用情境 | SPEC 參照 |
|:---|:---|:---|:---|
| Power On Reset | POR | Branch H Step 2H.1 — 裝置斷電後重新上電 | JESD220H Section 10.4 |

---

## 自我驗證

- Tree Diagram leaf steps: **17**（Phase 0: 2 (0.1~0.2), Phase 1: 1 (1.1), Phase 2: 14 (2.1, 2A.1, 2B.1, 2C.1, 2D.1, 2E.1~2E.2, 2F.1~2F.2, 2G.1, 2H.1~2H.2, 2I.1~2I.2) → Total: 17）
- `### Step` sections: **17** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（有 Expected 的 steps: 1.1, 2A.1, 2B.1, 2C.1, 2D.1, 2E.1, 2E.2, 2F.1, 2F.2, 2G.1, 2H.2, 2I.1, 2I.2 = 13 個；無 Expected: 0.1, 0.2, 2.1, 2H.1 = 4 個）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
