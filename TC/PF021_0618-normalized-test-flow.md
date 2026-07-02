---
title: PF021_0618_R_CMD_History_Suspend_Test-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf021_0618, scsi-cmd, cmd-history, suspend, vu]
description: >
  驗證 UFS 裝置在 Host Suspend 期間執行各種 Error Case（Invalid MODE SENSE、
  Invalid Vendor CMD、Invalid VU Write/Read Buffer）時，Flash CMD History
  不會被汙染（A 與 C 相同），且 RAM CMD History 正確記錄所有暫停期間執行的指令。
sources:
  - JIRA: PF021_0618 (SYSTCUFS-766)
  - UFS Spec: JESD220H Section 11.4.2, 11.4.7, 11.6.5
---

# PF021_0618 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置在 Host Suspend 期間執行各種 Error Case（MODE SENSE Invalid Page、
Vendor-Unique CMD Invalid Opcode、Invalid VU Write Buffer、Invalid VU Read Buffer）
時：
1. Flash CMD History 不會被更新（Record A == Record C）
2. RAM CMD History 正確記錄所有 Suspend 期間執行的指令（包含 Error Case）

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | 確認 IC + NAND + UFS 版本 | Phase 0 (Step 0.1) |
| Step 2 | 記錄 Flash CMD History A | Phase 1 (Step 1.1, 1.2) |
| Step 3 | Host sleep 1s | Phase 2 (Step 2.1) |
| Step 4 | Error Cases（每次執行一種） | Phase 3 (Step 3.1 ~ 3.4b, Branch) |
| Step 5 | Read buffer CMD history from RAM | Phase 4 (Step 4.1, 4.2) |
| Step 6 | 確認 RAM cmd history | Phase 5 (Step 5.1) |
| Step 7 | 記錄 Flash CMD History C | Phase 6 (Step 6.1, 6.2) |
| Step 8 | 確認沒有存到 Flash cmd history | Phase 7 (Step 7.1) |
| Step 9 | Loop step3 to step8 N times | Loop（Phase 2 ~ Phase 7） |
| Step 10 | Read and compare all | Phase 8 (Step 8.1) |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF021_0618 Test Flow
│
├── Phase 0: Pre-condition — 裝置相容性檢查
│   └── Step 0.1: 裝置相容性檢查 — IC / NAND / UFS 版本 Gate
│
├── Phase 1: 記錄 Flash CMD History A
│   ├── Step 1.1: WRITE BUFFER (3Bh) — 記錄 Flash CMD History A（Mode=E1h, VU） → Expected: GOOD Status
│   └── Step 1.2: READ BUFFER (3Ch) — 讀取 Flash CMD History A 結果（Mode=01h） → Expected: GOOD Status
│
└── Loop（N 次迭代，每次從 Phase 3 選一個 Case 執行）
    │
    ├── Phase 2: Host Suspend Delay
    │   └── Step 2.1: Host Sleep 1s — 觸發 Suspend 狀態
    │
    ├── Phase 3: Error Case Injection（Branch — 每圈執行一種）
    │   ├── [Case A] Step 3.1: MODE SENSE(10) (5Ah) — Invalid Page=02h → Expected: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=24h, ASCQ=00h
    │   ├── [Case B] Step 3.2: Vendor CMD — Invalid Opcode (FFh) → Expected: Response Failure
    │   ├── [Case C] Step 3.3: WRITE BUFFER (3Bh) — Invalid VU Payload (Mode=E1h, BufferID=FFh) → Expected: Response Failure
    │   └── [Case D] Step 3.4a: WRITE BUFFER (3Bh) — Get Smart Info (Mode=E1h, VU) → Expected: GOOD Status
    │                Step 3.4b: READ BUFFER (3Ch) — Invalid BufferID=FFh → Expected: Response Failure
    │
    ├── Phase 4: 讀取 RAM CMD History
    │   ├── Step 4.1: WRITE BUFFER (3Bh) — 讀取 RAM CMD History 請求（Mode=E1h, VU） → Expected: GOOD Status
    │   └── Step 4.2: READ BUFFER (3Ch) — 讀取 RAM CMD History 結果（Mode=01h） → Expected: GOOD Status
    │
    ├── Phase 5: 驗證 RAM CMD History
    │   └── Step 5.1: Data Compare — RAM CMD History vs 本圈 Step 2~4 記錄的 Trans Code / Task Tag → Expected: Data Match
    │
    ├── Phase 6: 記錄 Flash CMD History C
    │   ├── Step 6.1: WRITE BUFFER (3Bh) — 記錄 Flash CMD History C（Mode=E1h, VU） → Expected: GOOD Status
    │   └── Step 6.2: READ BUFFER (3Ch) — 讀取 Flash CMD History C 結果（Mode=01h） → Expected: GOOD Status
    │
    └── Phase 7: 驗證 Flash CMD History A == C
        └── Step 7.1: Data Compare — Flash CMD History A vs C → Expected: Flash CMD History A == C（相同=PASS, 不同=FAIL）
│
└── Phase 8: Data Integrity 驗證（Loop 結束後）
    └── Step 8.1: READ(10) — Read Compare All → Expected: GOOD Status, Data Match
```

---

## Phase 0 — Pre-condition：裝置相容性檢查

### Step 0.1: 裝置相容性檢查

**目的**: 確認測試對象為支援的 IC / NAND / UFS 版本組合，不符合則終止測試。

| Check | Value |
|-------|-------|
| IC | 8318 |
| NAND | BICS5 (for OPPO) |
| UFS Version | UFS 3.1 |

**Branch Logic**:
- 若全部符合 → 繼續測試
- 若任一不符 → Pattern 判定為 `NOT SUPPORTED`，終止測試

---

## Phase 1 — 記錄 Flash CMD History A

### Step 1.1: WRITE BUFFER — 記錄 Flash CMD History A（VU）

**SCSI CMD**: `WRITE BUFFER (0x3B)`

**目的**: 透過 Vendor-Unique WRITE BUFFER 指令觸發裝置將目前的 CMD History
寫入 Flash，作為 Baseline Record A。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| Mode | 0xE1 | Vendor Specific (VU) |
| Buffer ID | 0x00 | |
| Buffer Offset | 0x000000 | |
| Parameter List Length | 0x000004 | 4 bytes payload |
| VU Payload[0:3] | {0xF9, 0x40, 0x14, 0x14} | Record Flash CMD History |

**Expected**: GOOD Status。

**Note**: VU payload `{0xF9, 0x40, 0x14, 0x14}` 為 Vendor-Unique 定義的
「Record Flash CMD History」指令格式。byte[2:3] = `0x1414` 為回傳資料長度
（後續 READ BUFFER 使用）。

**UFS SPEC Reference**: JESD220H Section 11.6.5.1 (WRITE BUFFER)；
Mode=0xE1 為 Vendor Specific，無 SPEC 定義。

---

### Step 1.2: READ BUFFER — 讀取 Flash CMD History A 結果

**SCSI CMD**: `READ BUFFER (0x3C)`

**目的**: 讀取 Step 1.1 觸發的 Flash CMD History 內容，並記錄其 Trans Code
與 Task Tag 作為 Baseline Record A。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3C | READ BUFFER |
| Mode | 0x01 | Data (without header) |
| Buffer ID | 0x00 | |
| Buffer Offset | 0x000000 | |
| Allocation Length | 0x1414 | 5,140 bytes |

**Expected**: GOOD Status。

**Note**: 測試 Harness 需記錄 Buffer 中每一筆 CMD 的 Trans Code 與 Task Tag，
作為後續 Phase 5 比對的基準 Record A。

**UFS SPEC Reference**: JESD220H Section 11.6.5.2 (READ BUFFER)。

---

## Phase 2 — Host Suspend Delay

### Step 2.1: Host Sleep 1s — 觸發 Suspend 狀態

**目的**: 模擬 Host 端暫停 1 秒，使 UFS 裝置進入 Suspend 狀態，
此為測試 CMD History Suspend 行為的前置條件。

| Parameter | Value | Description |
|-----------|-------|-------------|
| Duration | 1000 ms | Host sleep 1 second |

**Note**: 此步驟為 Test Harness 延遲操作，非 SCSI Command。

---

## Phase 3 — Error Case Injection（Branch — 每圈執行一種）

Phase 3 為 Branch 結構。每次 Loop 迭代時從以下四種 Case 中擇一執行，
並記錄執行的 Error Case 之 Trans Code 與 Task Tag。

### Branch Logic（per JIRA 隨機選擇）

- Case A: Invalid MODE SENSE Page
- Case B: Invalid Vendor CMD Opcode
- Case C: Invalid VU WRITE BUFFER Payload
- Case D: Valid VU WRITE BUFFER + Invalid READ BUFFER BufferID

---

### Case A: Invalid MODE SENSE Page

#### Step 3.1: MODE SENSE(10) — 使用 Invalid Page Code 觸發 ILLEGAL_REQUEST

**SCSI CMD**: `MODE SENSE(10) (0x5A)`

**目的**: 發出帶有無效 Page Code (02h) 的 MODE SENSE 指令，
驗證裝置在 Suspend 狀態下正確回報 CHECK_CONDITION 且不汙染 CMD History。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x5A | MODE SENSE(10) |
| DBD | 0 | Disable Block Descriptors = false |
| PC | 0x00 | Page Control = Current Values |
| Page Code | 0x02 | Invalid Page（UFS 不支援 Disconnect-Reconnect Page） |
| SubPage Code | 0x00 | |
| Allocation Length | 0x00FF | 255 bytes（最小合法值） |
| Control | 0x00 | |

**Expected**: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=24h, ASCQ=00h
（INVALID FIELD IN CDB）。

**UFS SPEC Reference**: JESD220H Section 11.4.7 (MODE SENSE(10))。

---

### Case B: Invalid Vendor CMD Opcode

#### Step 3.2: Vendor CMD — 使用未定義 Opcode FFh

**SCSI CMD**: `Vendor-Unique Command (0xFF)`

**目的**: 發出未定義的 SCSI Opcode (FFh)，驗證裝置回報失敗且不影響 CMD History。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0xFF | Undefined / Invalid SCSI Opcode |
| CDB Byte[1:9] | 0x00 | |

**Expected**: Response Failure（裝置回報 CHECK_CONDITION 或 Task Management 失敗）。

**Note**: Opcode FFh 不在任何 SCSI Standard 定義範圍內，裝置應回報
CHECK_CONDITION (SENSE_KEY=ILLEGAL_REQUEST) 或直接回傳 failure。

**UFS SPEC Reference**: Opcode FFh 為未定義指令，無 SPEC 對應章節。

---

### Case C: Invalid VU WRITE BUFFER Payload

#### Step 3.3: WRITE BUFFER — Invalid VU Payload（Mode=E1h, BufferID=FFh）

**SCSI CMD**: `WRITE BUFFER (0x3B)`

**目的**: 發出帶有全 FFh VU Payload 與無效 BufferID (FFh) 的 WRITE BUFFER，
驗證裝置回報失敗。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| Mode | 0xE1 | Vendor Specific (VU) |
| Buffer ID | 0xFF | Invalid Buffer ID |
| Buffer Offset | 0x000000 | |
| Parameter List Length | 0x000004 | 4 bytes payload |
| VU Payload[0:3] | {0xFF, 0xFF, 0xFF, 0xFF} | Invalid VU payload |

**Expected**: Response Failure。

**UFS SPEC Reference**: JESD220H Section 11.6.5.1 (WRITE BUFFER)。

---

### Case D: Valid VU WRITE BUFFER + Invalid READ BUFFER BufferID

#### Step 3.4a: WRITE BUFFER — Get Smart Info（Mode=E1h, VU）

**SCSI CMD**: `WRITE BUFFER (0x3B)`

**目的**: 透過 VU WRITE BUFFER 觸發 Get Smart Info（用於後續 READ BUFFER 步驟），
此指令本身為合法 VU 操作。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| Mode | 0xE1 | Vendor Specific (VU) |
| Buffer ID | 0x00 | |
| Buffer Offset | 0x000000 | |
| Parameter List Length | 0x1000 | 4 KB |
| VU Payload[0:3] | {0xBB, 0x40, 0x10, 0x00} | Get Smart Info |

**Expected**: GOOD Status。

**UFS SPEC Reference**: JESD220H Section 11.6.5.1 (WRITE BUFFER)；
VU payload 定義為 Vendor Unique。

---

#### Step 3.4b: READ BUFFER — Invalid BufferID 觸發失敗（Mode=01h, BufferID=FFh）

**SCSI CMD**: `READ BUFFER (0x3C)`

**目的**: 使用無效的 BufferID (FFh) 讀取 Buffer，驗證裝置回報失敗。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3C | READ BUFFER |
| Mode | 0x01 | Data (without header) |
| Buffer ID | 0xFF | Invalid Buffer ID |
| Buffer Offset | 0x000000 | |
| Allocation Length | 0x0400 | 1 KB |

**Expected**: Response Failure。

**UFS SPEC Reference**: JESD220H Section 11.6.5.2 (READ BUFFER)。

---

## Phase 4 — 讀取 RAM CMD History

### Step 4.1: WRITE BUFFER — 讀取 RAM CMD History 請求（Mode=E1h, VU）

**SCSI CMD**: `WRITE BUFFER (0x3B)`

**目的**: 透過 VU WRITE BUFFER 觸發從 RAM 讀取目前的 CMD History，
取得 Suspend 期間執行的所有指令記錄。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| Mode | 0xE1 | Vendor Specific (VU) |
| Buffer ID | 0x00 | |
| Buffer Offset | 0x000000 | |
| Parameter List Length | 0x000004 | 4 bytes payload |
| VU Payload[0:3] | {0xF8, 0x40, 0x14, 0x14} | Read RAM CMD History |

**Expected**: GOOD Status。

**Note**: VU payload `{0xF8, 0x40, 0x14, 0x14}` 為 Vendor-Unique 定義的
「Read RAM CMD History」指令。byte[2:3] = `0x1414` 為回傳資料長度。

**UFS SPEC Reference**: JESD220H Section 11.6.5.1 (WRITE BUFFER)；
VU payload 定義為 Vendor Unique。

---

### Step 4.2: READ BUFFER — 讀取 RAM CMD History 結果（Mode=01h）

**SCSI CMD**: `READ BUFFER (0x3C)`

**目的**: 讀取 Step 4.1 觸發的 RAM CMD History 內容，作為 Record B。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3C | READ BUFFER |
| Mode | 0x01 | Data (without header) |
| Buffer ID | 0x00 | |
| Buffer Offset | 0x000000 | |
| Allocation Length | 0x1414 | 5,140 bytes |

**Expected**: GOOD Status。

**Note**: 測試 Harness 讀取 Buffer 內容作為 Record B（RAM CMD History）。

**UFS SPEC Reference**: JESD220H Section 11.6.5.2 (READ BUFFER)。

---

## Phase 5 — 驗證 RAM CMD History

### Step 5.1: Data Compare — RAM CMD History vs 本圈執行指令

**目的**: 比對 Step 4.2 讀到的 RAM CMD History（Record B）中的 Trans Code 與
Task Tag，是否包含本圈 Phase 2 ~ Phase 3 執行的指令（Host Sleep 後的 Error Case）。
驗證 RAM CMD History 正確記錄 Suspend 期間的所有指令。

| Compare Item | Source |
|--------------|--------|
| Record B (RAM CMD History) | Step 4.2 READ BUFFER 結果 |
| Expected Commands | Phase 2 ~ Phase 3 本圈執行之 Error Case 的 Trans Code 與 Task Tag |

**Expected**: Data Match（RAM CMD History 包含本圈所執行指令的紀錄）。

**Note**: 此步驟為 Test Harness 比對操作，非 SCSI Command。

---

## Phase 6 — 記錄 Flash CMD History C

### Step 6.1: WRITE BUFFER — 記錄 Flash CMD History C（Mode=E1h, VU）

**SCSI CMD**: `WRITE BUFFER (0x3B)`

**目的**: 再次觸發 Flash CMD History 寫入，取得 Suspend+Error Case 後的
Flash CMD History 內容，作為 Record C。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| Mode | 0xE1 | Vendor Specific (VU) |
| Buffer ID | 0x00 | |
| Buffer Offset | 0x000000 | |
| Parameter List Length | 0x000004 | 4 bytes payload |
| VU Payload[0:3] | {0xF9, 0x40, 0x14, 0x14} | Record Flash CMD History |

**Expected**: GOOD Status。

**Note**: 與 Step 1.1 使用相同 VU Payload `{0xF9, 0x40, 0x14, 0x14}`。

**UFS SPEC Reference**: JESD220H Section 11.6.5.1 (WRITE BUFFER)。

---

### Step 6.2: READ BUFFER — 讀取 Flash CMD History C 結果（Mode=01h）

**SCSI CMD**: `READ BUFFER (0x3C)`

**目的**: 讀取 Step 6.1 觸發的 Flash CMD History C 內容。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3C | READ BUFFER |
| Mode | 0x01 | Data (without header) |
| Buffer ID | 0x00 | |
| Buffer Offset | 0x000000 | |
| Allocation Length | 0x1414 | 5,140 bytes |

**Expected**: GOOD Status。

**Note**: 測試 Harness 記錄 Buffer 內容作為 Record C。

**UFS SPEC Reference**: JESD220H Section 11.6.5.2 (READ BUFFER)。

---

## Phase 7 — 驗證 Flash CMD History A == C

### Step 7.1: Data Compare — Flash CMD History A vs C

**目的**: 比對 Phase 1 讀取的 Record A 與 Phase 6 讀取的 Record C 是否完全相同。
若相同 → Suspend 期間的 Error Case 並未寫入 Flash CMD History（預期行為）；
若不同 → Flash CMD History 被 Suspend 期間的操作汙染。

| Compare Item | Source |
|--------------|--------|
| Record A (Flash CMD History) | Step 1.2 READ BUFFER 結果 |
| Record C (Flash CMD History) | Step 6.2 READ BUFFER 結果 |

**Expected**: Flash CMD History A == C（相同 → PASS，不同 → FAIL）。

**Note**: 此步驟為 Test Harness 比對操作，非 SCSI Command。

---

## Phase 8 — Data Integrity 驗證（Loop 結束後）

### Step 8.1: READ(10) — Read Compare All

**SCSI CMD**: `READ(10) (0x28)`

**目的**: Loop 全部結束後，讀回所有先前寫入的資料並進行比對，
確認 Suspend 期間的 VU 操作與 Error Case Injection 未造成資料損毀。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x28 | READ(10) |
| RDPROTECT | 0x00 | |
| DPO | 0 | |
| FUA | 0 | |
| FUA_NV | 0 | |
| Logical Block Address | 0x00000000 | 從 LBA 0 開始 |
| Transfer Length | (依寫入範圍) | 涵蓋所有已寫入的 LBA 範圍 |

**Expected**: GOOD Status, Data Match。

**Note**: 實際 LBA 範圍與比對基準取決於測試前置設定中寫入的資料範圍。

**UFS SPEC Reference**: JESD220H Section 11.4.2 (READ(10))。

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

本 Pattern 未使用 UFS Query 操作（READ/SET/CLEAR Flag、READ/WRITE Attribute/Descriptor）。
所有 Command History 操作均透過 Vendor-Unique WRITE BUFFER / READ BUFFER 實現。

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | Phase 8: Read Compare All |
| 0x3B | WRITE BUFFER | 10 | Phase 1/3/4/6: VU CMD History / Smart Info |
| 0x3C | READ BUFFER | 10 | Phase 1/3/4/6: 讀取 VU CMD History 結果 |
| 0x5A | MODE SENSE(10) | 10 | Phase 3 Case A: Invalid Page Error Case |
| 0xFF | Vendor-Unique CMD | — | Phase 3 Case B: Invalid Opcode Error Case |

**WRITE BUFFER Mode 說明**：

| Mode | 值 | 說明 | SPEC 參照 |
|:---|:---|:---|:---|
| Data (with header) | 0x00 | Standard download microcode | JESD220H 11.6.5.1 |
| Data (without header) | 0x01 | — | JESD220H 11.6.5.1 |
| Vendor Specific | 0xE1 | VU CMD History / Smart Info 操作 | Vendor Unique |

**READ BUFFER Mode 說明**：

| Mode | 值 | 說明 | SPEC 參照 |
|:---|:---|:---|:---|
| Data (with header) | 0x00 | Standard read buffer | JESD220H 11.6.5.2 |
| Data (without header) | 0x01 | 本 Pattern 使用 | JESD220H 11.6.5.2 |

---

## 附錄 C — VU Payload 對照表

本 Pattern 使用多個 Vendor-Unique WRITE BUFFER Payload。以下為各 Payload
的用途說明（均非 SPEC 定義）：

| Payload (hex) | 用途 | 使用位置 |
|:---|:---|:---|
| `{0xF9, 0x40, 0x14, 0x14}` | Record Flash CMD History | Step 1.1, Step 6.1 |
| `{0xF8, 0x40, 0x14, 0x14}` | Read RAM CMD History | Step 4.1 |
| `{0xBB, 0x40, 0x10, 0x00}` | Get Smart Info | Step 3.4a |
| `{0xFF, 0xFF, 0xFF, 0xFF}` | Invalid VU Payload（觸發 failure） | Step 3.3 |

---

## 自我驗證

- Tree Diagram leaf steps: **16**（Phase 0: 1 (0.1), Phase 1: 2 (1.1~1.2), Phase 2: 1 (2.1), Phase 3: 5 (3.1, 3.2, 3.3, 3.4a, 3.4b), Phase 4: 2 (4.1~4.2), Phase 5: 1 (5.1), Phase 6: 2 (6.1~6.2), Phase 7: 1 (7.1), Phase 8: 1 (8.1) → Total: 16）
- `### Step` sections: **16** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（14 個 step 有 Expected，Step 0.1 與 Step 2.1 無 JIRA 指定的 Expected）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
