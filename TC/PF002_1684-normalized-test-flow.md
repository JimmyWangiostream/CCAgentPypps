---
title: PF002_1684_D_Boot_LUN_Combination_Test-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_1684, scsi-cmd, boot-lun, hpb, writebooster, rpmb]
description: >
  驗證 UFS 裝置在 Boot LUN 組合配置下的功能正確性。測試涵蓋不同 Boot LUN
  分區類型（Enhanced / Normal / Mixed）與大小配置，並搭配 HPB、WriteBooster、
  RPMB 三種功能組合進行 Write → Erase → Read Compare 壓力驗證。
sources:
  - JIRA: PF002_1684 (SYSTCUFS-1997)
  - UFS Spec: JESD220H Sections 10.7.4, 10.7.5, 10.7.8–10.7.9, 14.1.4, 14.2, 14.3
---

# PF002_1684 D Boot LUN Combination Test — Normalized Test Flow

## 測試架構（Tree Diagram）

```
PF002_1684 Test Flow
│
├── Phase 0: Hardware Compatibility Check
│   └── Step 0.1: 裝置相容性檢查 (IC=8329, NAND=BICS8)
│
└── Loop (per JIRA burn-in iteration)
    │
    ├── Phase 1: Boot LUN Configuration
    │   ├── Step 1.1: WRITE ATTRIBUTE (bBootLunEn) — 設定 Boot LUN 啟用
    │   └── Step 1.2: WRITE DESCRIPTOR (Configuration Descriptor) — 配置兩個 Boot 分區類型與大小
    │
    ├── Phase 2: Feature Configuration (Branch — 每輪選一 Case)
    │   ├── [Case 1: HPB] Step 2.1: SET FLAG (fHPBEn) — 啟用 HPB
    │   ├── [Case 2: WriteBooster] Step 2.2: WRITE DESCRIPTOR (Configuration Descriptor) — 設定 WB Buffer 大小
    │   ├── [Case 2: WriteBooster] Step 2.3: SET FLAG (fWriteBoosterEn) — 啟用 WriteBooster
    │   ├── [Case 3: RPMB] Step 2.4: SECURITY PROTOCOL OUT — RPMB Authentication Key 寫入 (OUT 1)
    │   ├── [Case 3: RPMB] Step 2.5: SECURITY PROTOCOL OUT — RPMB Result Request (OUT 2)
    │   └── [Case 3: RPMB] Step 2.6: SECURITY PROTOCOL IN — RPMB Receive Result (IN)
    │
    ├── Phase 3: Erase All LUN
    │   ├── Step 3.1: UNMAP — Erase Boot LUN A
    │   └── Step 3.2: UNMAP — Erase Boot LUN B
    │
    └── Phase 4: Write / Erase / Read & Data Compare
        ├── Step 4.1: WRITE(10) — 寫入測試資料至 Boot LUN A
        ├── Step 4.2: WRITE(10) — 寫入測試資料至 Boot LUN B
        ├── Step 4.3: UNMAP — Erase Boot LUN A
        ├── Step 4.4: UNMAP — Erase Boot LUN B
        ├── Step 4.5: READ(10) — 讀取比對 Boot LUN A → Expected: GOOD Status, Data Match
        └── Step 4.6: READ(10) — 讀取比對 Boot LUN B → Expected: GOOD Status, Data Match
```

---

## Phase 0 — Hardware Compatibility Check

### Step 0.1: 裝置相容性檢查

**目的**: 確認 IC 與 NAND 組合為支援的配置。

**類型**: 前置條件閘道（非 SCSI CMD）

| Check | Condition |
|-------|-----------|
| IC | Must be 8329 |
| NAND | Must be BICS8 |

**判斷邏輯**: 若 IC ≠ 8329 或 NAND ≠ BICS8，則 Pattern 判定為 `NOT SUPPORTED`，終止測試。

---

## Phase 1 — Boot LUN Configuration

### Step 1.1: WRITE ATTRIBUTE (bBootLunEn) — 設定 Boot LUN 啟用

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)`

**目的**: 啟用指定 LUN 作為 Boot LUN。bBootLunEn 的每個 bit 對應一個 LUN 的 Boot 啟用狀態。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| bAttrIDN | 0x00 (bBootLunEn) |
| Attribute Value | 依隨機選取的 2 個 LUN 設定對應 bits（e.g., 0x03 表示 LUN 0 與 LUN 1 為 Boot LUN） |

**UFS SPEC Reference**: JESD220H Section 14.3 (bBootLunEn, IDN 0x00)

---

### Step 1.2: WRITE DESCRIPTOR (Configuration Descriptor) — 配置兩個 Boot 分區類型與大小

**UFS QUERY**: `WRITE DESCRIPTOR (0x08)`

**目的**: 對隨機選取的 2 個 LUN 設定分區類型（Enhanced / Normal / Mixed）與大小（Max Size / Min Size / Total AU/2），寫入完整 Configuration Descriptor。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| Descriptor IDN | 0x01 (Configuration Descriptor) |
| bNumberLU | ≥ 2 (至少包含被設定的 2 個 Boot LUN) |

**Unit Descriptor — Boot LUN A**:

| Field | Value |
|-------|-------|
| bLUEnable | 0x01 (Enabled) |
| bBootLunID | 0x01 (Boot LUN A) |
| bMemoryType | 隨機選取：0x00 (Normal) / 0x01 (Enhanced) / Mixed |
| dNumAllocUnits | 隨機選取：Max Size / Min Size / Total AU ÷ 2 |
| bLogicalBlockSize | 0x0C (4096 bytes) |
| bProvisioningType | 0x00 (Thin Provisioning) |

**Unit Descriptor — Boot LUN B**:

| Field | Value |
|-------|-------|
| bLUEnable | 0x01 (Enabled) |
| bBootLunID | 0x02 (Boot LUN B) |
| bMemoryType | 隨機選取：0x00 (Normal) / 0x01 (Enhanced) / Mixed |
| dNumAllocUnits | 隨機選取：Max Size / Min Size / Total AU ÷ 2 |
| bLogicalBlockSize | 0x0C (4096 bytes) |
| bProvisioningType | 0x00 (Thin Provisioning) |

**UFS SPEC Reference**: JESD220H Section 14.1.4 (Configuration Descriptor)

---

## Phase 2 — Feature Configuration

**Branch Logic** (per JIRA — 每輪迭代選取一個 Case):

- **Case 1**: Config HPB → Step 2.1
- **Case 2**: Config WriteBooster → Step 2.2, Step 2.3
- **Case 3**: Config RPMB → Step 2.4, Step 2.5, Step 2.6

---

### Step 2.1: [Case 1 — HPB] SET FLAG (fHPBEn) — 啟用 HPB

**UFS QUERY**: `SET FLAG (0x02)`

**目的**: 啟用 Host Performance Booster 功能。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x07 (fHPBEn) |

**UFS SPEC Reference**: JESD220H Section 14.2 (fHPBEn, IDN 0x07)

---

### Step 2.2: [Case 2 — WriteBooster] WRITE DESCRIPTOR (Configuration Descriptor) — 設定 WB Buffer 大小

**UFS QUERY**: `WRITE DESCRIPTOR (0x08)`

**目的**: 在 Configuration Descriptor 的 Unit Descriptor 中設定 `dLUNumWriteBoosterBufferAllocUnits`，為 Boot LUN 分配 WriteBooster Buffer。

> **註**: `dLUNumWriteBoosterBufferAllocUnits` 為唯讀 Attribute (IDN 0x17)，不可透過 WRITE ATTRIBUTE 設定，必須透過 WRITE DESCRIPTOR (Configuration Descriptor) 配置。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| Descriptor IDN | 0x01 (Configuration Descriptor) |

**Unit Descriptor — Boot LUN A**:

| Field | Value |
|-------|-------|
| dLUNumWriteBoosterBufferAllocUnits | Non-zero (依裝置容量設定 WB Buffer 大小) |

**Unit Descriptor — Boot LUN B**:

| Field | Value |
|-------|-------|
| dLUNumWriteBoosterBufferAllocUnits | Non-zero (依裝置容量設定 WB Buffer 大小) |

**UFS SPEC Reference**: JESD220H Section 14.1.4 (Configuration Descriptor — Unit Descriptor fields for WriteBooster)

---

### Step 2.3: [Case 2 — WriteBooster] SET FLAG (fWriteBoosterEn) — 啟用 WriteBooster

**UFS QUERY**: `SET FLAG (0x02)`

**目的**: 在 WB Buffer 配置完成後，啟用 WriteBooster 功能。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x0E (fWriteBoosterEn) |

**UFS SPEC Reference**: JESD220H Section 14.2 (fWriteBoosterEn, IDN 0x0E)

---

### Step 2.4: [Case 3 — RPMB] SECURITY PROTOCOL OUT — RPMB Authentication Key 寫入 (OUT 1)

**SCSI CMD**: `SECURITY PROTOCOL OUT (0xB5)`

**目的**: 發送 RPMB Authentication Key Programming Request，將 Authentication Key 寫入 RPMB 區域。（RPMB Key Programming 流程的第一個 OUT）

| Field | Value |
|-------|-------|
| Opcode | 0xB5 |
| SECURITY PROTOCOL | 0xEC (RPMB Protocol ID) |
| SECURITY PROTOCOL SPECIFIC | 0x0001 (RPMB Authentication Key Programming Request) |
| INC_512 | 1 |
| Allocation Length / Transfer Length | 512 bytes (RPMB frame size) |
| LUN | RPMB LUN |

**RPMB Frame Payload** (簡述):

| Field | Value |
|-------|-------|
| Request Type | 0x0001 (Authentication Key Programming) |
| Key / MAC | 32-byte Authentication Key |

**UFS SPEC Reference**: JESD220H Section 10.7.5 (RPMB), JEDEC JESD84-B51 Section 6.4 (RPMB Operation)

---

### Step 2.5: [Case 3 — RPMB] SECURITY PROTOCOL OUT — RPMB Result Request (OUT 2)

**SCSI CMD**: `SECURITY PROTOCOL OUT (0xB5)`

**目的**: 發送 Result Read Request，查詢 RPMB Authentication Key Programming 的執行結果。（RPMB Key Programming 流程的第二個 OUT）

| Field | Value |
|-------|-------|
| Opcode | 0xB5 |
| SECURITY PROTOCOL | 0xEC (RPMB Protocol ID) |
| SECURITY PROTOCOL SPECIFIC | 0x0003 (RPMB Result Read Request) |
| INC_512 | 1 |
| Allocation Length / Transfer Length | 512 bytes (RPMB frame size) |
| LUN | RPMB LUN |

**RPMB Frame Payload** (簡述):

| Field | Value |
|-------|-------|
| Request Type | 0x0003 (Result Read Request) |

**UFS SPEC Reference**: JESD220H Section 10.7.5 (RPMB), JEDEC JESD84-B51 Section 6.4 (RPMB Operation)

---

### Step 2.6: [Case 3 — RPMB] SECURITY PROTOCOL IN — RPMB Receive Result (IN)

**SCSI CMD**: `SECURITY PROTOCOL IN (0xA2)`

**目的**: 接收 RPMB Authentication Key Programming 的執行結果，確認 Key 寫入成功。

| Field | Value |
|-------|-------|
| Opcode | 0xA2 |
| SECURITY PROTOCOL | 0xEC (RPMB Protocol ID) |
| SECURITY PROTOCOL SPECIFIC | 0x0003 (RPMB Result Read Response) |
| INC_512 | 1 |
| Allocation Length / Transfer Length | 512 bytes (RPMB frame size) |
| LUN | RPMB LUN |

**UFS SPEC Reference**: JESD220H Section 10.7.5 (RPMB), JEDEC JESD84-B51 Section 6.4 (RPMB Operation)

---

## Phase 3 — Erase All LUN

### Step 3.1: UNMAP — Erase Boot LUN A

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 對 Boot LUN A 執行 Unmap，清除所有已寫入資料。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | Boot LUN A |
| ANCHOR | 0 (non-anchored) |
| UNMAP LBA 範圍 | LBA 0 至 MaxLBA (全部邏輯區塊) |

**UFS SPEC Reference**: JESD220H Section 10.7.4 (UNMAP command)

---

### Step 3.2: UNMAP — Erase Boot LUN B

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 對 Boot LUN B 執行 Unmap，清除所有已寫入資料。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | Boot LUN B |
| ANCHOR | 0 (non-anchored) |
| UNMAP LBA 範圍 | LBA 0 至 MaxLBA (全部邏輯區塊) |

**UFS SPEC Reference**: JESD220H Section 10.7.4 (UNMAP command)

---

## Phase 4 — Write / Erase / Read & Data Compare

### Step 4.1: WRITE(10) — 寫入測試資料至 Boot LUN A

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 將測試 Pattern 資料寫入 Boot LUN A，作為後續 Erase 與 Read Compare 的基準。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | Boot LUN A |
| LBA | 0x00000000 |
| Transfer Length | 依 JIRA 隨機選取（至少 1 block） |
| Data | 隨機測試 Pattern |

**UFS SPEC Reference**: JESD220H Section 10.7.2 (WRITE(10) command)

---

### Step 4.2: WRITE(10) — 寫入測試資料至 Boot LUN B

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 將測試 Pattern 資料寫入 Boot LUN B，作為後續 Erase 與 Read Compare 的基準。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | Boot LUN B |
| LBA | 0x00000000 |
| Transfer Length | 依 JIRA 隨機選取（至少 1 block） |
| Data | 隨機測試 Pattern |

**UFS SPEC Reference**: JESD220H Section 10.7.2 (WRITE(10) command)

---

### Step 4.3: UNMAP — Erase Boot LUN A

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 對 Boot LUN A 執行 Erase（Unmap），清除 Step 4.1 寫入的測試資料。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | Boot LUN A |
| ANCHOR | 0 (non-anchored) |
| UNMAP LBA 範圍 | LBA 0 至 Step 4.1 寫入範圍 |

**UFS SPEC Reference**: JESD220H Section 10.7.4 (UNMAP command)

---

### Step 4.4: UNMAP — Erase Boot LUN B

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 對 Boot LUN B 執行 Erase（Unmap），清除 Step 4.2 寫入的測試資料。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | Boot LUN B |
| ANCHOR | 0 (non-anchored) |
| UNMAP LBA 範圍 | LBA 0 至 Step 4.2 寫入範圍 |

**UFS SPEC Reference**: JESD220H Section 10.7.4 (UNMAP command)

---

### Step 4.5: READ(10) — 讀取比對 Boot LUN A

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 讀回 Boot LUN A 上經 Erase 後的資料，與預期之 unmapped block pattern 進行比對。JIRA 明確要求 "check data cmp pass"。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LUN A |
| LBA | 0x00000000 |
| Transfer Length | 與 Step 4.1 寫入範圍相同 |
| Compare | 讀取資料與預期 unmapped block pattern 比對 |

**Expected**: GOOD Status, Data Match

**UFS SPEC Reference**: JESD220H Section 10.7.2 (READ(10) command)

---

### Step 4.6: READ(10) — 讀取比對 Boot LUN B

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 讀回 Boot LUN B 上經 Erase 後的資料，與預期之 unmapped block pattern 進行比對。JIRA 明確要求 "check data cmp pass"。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LUN B |
| LBA | 0x00000000 |
| Transfer Length | 與 Step 4.2 寫入範圍相同 |
| Compare | 讀取資料與預期 unmapped block pattern 比對 |

**Expected**: GOOD Status, Data Match

**UFS SPEC Reference**: JESD220H Section 10.7.2 (READ(10) command)

---

## 附錄 A — UFS Query IDN 對照表

### Flags (bFlagIDN)

| IDN | Name | Description |
|:---|:---|:---|
| 0x07 | fHPBEn | Host Performance Booster enable (Case 1) |
| 0x0E | fWriteBoosterEn | Write Booster enable (Case 2) |

### Attributes (bAttrIDN)

| IDN | Name | Size | Access | Description |
|:---|:---|:---|:---|:---|
| 0x00 | bBootLunEn | 1 | R/W | Boot LU enable bitmap |

### Descriptors (Descriptor IDN)

| IDN | Name | Description |
|:---|:---|:---|
| 0x01 | Configuration Descriptor | Device-wide LU configuration including Unit Descriptors |

### Query Opcodes

| Opcode | Name | Description |
|:---|:---|:---|
| 0x02 | SET FLAG | Set specified flag to 1 |
| 0x04 | WRITE ATTRIBUTE | Write specified attribute value |
| 0x08 | WRITE DESCRIPTOR | Write specified descriptor |

---

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | Command | CDB Size | Use in Pattern |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | Phase 4: Read & Compare Boot LUN data |
| 0x2A | WRITE(10) | 10 | Phase 4: Write test data to Boot LUNs |
| 0x42 | UNMAP | 10 | Phase 3 & Phase 4: Erase LUN data |
| 0xA2 | SECURITY PROTOCOL IN | 12 | Phase 2 (Case 3): RPMB Result Receive |
| 0xB5 | SECURITY PROTOCOL OUT | 12 | Phase 2 (Case 3): RPMB Key Programming & Result Request |

---

## 自我驗證

- Tree Diagram leaf steps: **17**（Phase 0: 1 (0.1), Phase 1: 2 (1.1~1.2), Phase 2: 6 (2.1~2.6), Phase 3: 2 (3.1~3.2), Phase 4: 6 (4.1~4.6) → Total: 17）
- `### Step` sections: **17** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（2 個 step 有 Expected: Step 4.5, Step 4.6，來源為 JIRA Step 6 "check data cmp pass"）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
