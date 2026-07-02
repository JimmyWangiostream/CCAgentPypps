---
title: PF002_1683_Boot_LUN_OOR-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_1683, scsi-cmd, boot-lun, oor, out-of-range]
description: >
  驗證 Boot LUN Configuration Descriptor 在容量超過最大允許值（OOR）時，裝置正確拒絕
  （回傳 invalid value）。並在有效配置 Boot LUN 後，對 Boot LU 執行 Write/Erase/Read
  超出 LBA 範圍的 OOR 存取，確認裝置回應 CHECK_CONDITION 且 SENSE_KEY 為
  ILLEGAL_REQUEST(05h)、ASC 為 LOGICAL BLOCK ADDRESS OUT OF RANGE(21h)。
sources:
  - JIRA: PF002_1683 (SYSTCUFS-1996)
  - UFS Spec: JESD220H Section 10.7.9.8 (WRITE DESCRIPTOR), Section 11.8 (UNMAP),
    Section 14.1.4.1 (Device Descriptor), Section 14.1.4.3 (Configuration Descriptor),
    Section 14.1.6.3 (Unit Descriptor)
---

# PF002_1683 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置在 Boot LUN Configuration Descriptor 配置階段及資料存取階段的
Out-Of-Range (OOR) 錯誤處理機制：
1. 以超過最大容量的參數寫入 Configuration Descriptor 時，裝置應回傳 invalid value
2. 以有效容量配置 Boot LUN 後，對 Boot LU 執行超出 LBA 範圍的 Write/Erase/Read
   操作時，裝置應回傳 CHECK_CONDITION（SENSE_KEY=ILLEGAL_REQUEST，
   ASC=LOGICAL BLOCK ADDRESS OUT OF RANGE）

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | 確認測試IC + Nand是否為 8329 BICS8 若不是則停止測試, 判定non support | Step 0.1 (Phase 0) |
| Step 2 | set boot lun | Step 0.2 (Phase 0) |
| Step 3 | config two boot partition > max capacity size config enhance/normal/mix type LUN check resp should be invalid value | Step 1.1 ~ 1.3 (Phase 1) |
| Step 4 | config two boot partition with normal/enhance/mix type | Step 2.1 (Phase 2) |
| Step 5 | write/erase/read OOR check sense key be illegal_request & ASC be logical_blk_address_out_of_range | Step 3.1 ~ 3.3 (Phase 3) |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF002_1683 Test Flow
│
├── Phase 0: 前置條件與 Boot LUN 啟用
│   ├── Step 0.1: 裝置相容性檢查 — IC=8329, NAND=BICS8
│   └── Step 0.2: WRITE DESCRIPTOR (Device) — 設定 bBootLunEn 啟用 Boot LU A/B
│
├── Phase 1: Boot LUN Configuration Descriptor OOR 測試（容量 > Max）
│   ├── Step 1.1: WRITE DESCRIPTOR (Configuration) — 增強型 Boot LU A+B, dLUNumAllocUnits > Max → Expected: QUERY RESPONSE returns invalid value
│   ├── Step 1.2: WRITE DESCRIPTOR (Configuration) — 一般型 Boot LU A+B, dLUNumAllocUnits > Max → Expected: QUERY RESPONSE returns invalid value
│   └── Step 1.3: WRITE DESCRIPTOR (Configuration) — 混合型 Boot LU A(增強)+B(一般), dLUNumAllocUnits > Max → Expected: QUERY RESPONSE returns invalid value
│
├── Phase 2: Boot LUN 有效配置
│   └── Step 2.1: WRITE DESCRIPTOR (Configuration) — Boot LU A(增強)+B(一般), 有效容量
│
└── Phase 3: Boot LUN OOR 資料存取驗證（Write / Erase / Read）
    ├── Step 3.1: WRITE(10) — Boot LU, LBA > dLUNumAllocUnits → Expected: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL BLOCK ADDRESS OUT OF RANGE(21h)
    ├── Step 3.2: UNMAP — Boot LU, LBA > dLUNumAllocUnits → Expected: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL BLOCK ADDRESS OUT OF RANGE(21h)
    └── Step 3.3: READ(10) — Boot LU, LBA > dLUNumAllocUnits → Expected: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL BLOCK ADDRESS OUT OF RANGE(21h)
```

---

## Phase 0 — 前置條件與 Boot LUN 啟用

### Step 0.1: 裝置相容性檢查

**目的**: 確認 IC 與 NAND 組合為本 Pattern 支援之配置。

| Field | Value |
|-------|-------|
| IC | 8329 |
| NAND | BICS8 |

**檢查邏輯**: 若 IC ≠ 8329 或 NAND ≠ BICS8，則判定為 `NOT SUPPORTED`，終止測試。

---

### Step 0.2: 設定 bBootLunEn 啟用 Boot LUN

**UFS QUERY**: `WRITE DESCRIPTOR (08h)` — Device Descriptor

**目的**: 設定 Device Descriptor 的 bBootLunEn 欄位，啟用 Boot LU A 與 Boot LU B。

| Field | Value | 說明 |
|-------|-------|------|
| Opcode | 0x08 | WRITE DESCRIPTOR |
| IDN | 0x00 | Device Descriptor |
| Index | 0x00 | |
| Selector | 0x00 | |
| bBootLunEn (offset 0x01) | 0x03 | Bit 0=1 (Boot LU A enabled), Bit 1=1 (Boot LU B enabled) |

**UFS SPEC Reference**: JESD220H Section 14.1.4.1 (Device Descriptor), Section 10.7.9.8 (WRITE DESCRIPTOR)

---

## Phase 1 — Boot LUN Configuration Descriptor OOR 測試（容量 > Max）

### Step 1.1: 增強型 Boot LU Configuration — 容量超過 Max（OOR）

**UFS QUERY**: `WRITE DESCRIPTOR (08h)` — Configuration Descriptor

**目的**: 嘗試以超過最大允許容量（dLUNumAllocUnits > Max）配置兩個增強型 Boot LU，
驗證裝置回傳 invalid value。

| Field | Value | 說明 |
|-------|-------|------|
| Opcode | 0x08 | WRITE DESCRIPTOR |
| IDN | 0x01 | Configuration Descriptor |
| Index | 0x00 | |
| Selector | 0x00 | |
| Unit Desc 0 — bLUEnable | 0x01 | LU enabled |
| Unit Desc 0 — bBootLunID | 0x01 | Boot LU A |
| Unit Desc 0 — bMemoryType | 0x03 | Enhanced (JESD220H Table 14.13) |
| Unit Desc 0 — dLUNumAllocUnits | **> Max capacity** | 故意超出最大容量（OOR） |
| Unit Desc 1 — bLUEnable | 0x01 | LU enabled |
| Unit Desc 1 — bBootLunID | 0x02 | Boot LU B |
| Unit Desc 1 — bMemoryType | 0x03 | Enhanced |
| Unit Desc 1 — dLUNumAllocUnits | **> Max capacity** | 故意超出最大容量（OOR） |

**Expected**: QUERY RESPONSE returns invalid value（Response field ≠ 0x00）。

**UFS SPEC Reference**: JESD220H Section 14.1.4.3 (Configuration Descriptor), Section 14.1.6.3 (Unit Descriptor), Section 10.7.9.8 (WRITE DESCRIPTOR Response)

---

### Step 1.2: 一般型 Boot LU Configuration — 容量超過 Max（OOR）

**UFS QUERY**: `WRITE DESCRIPTOR (08h)` — Configuration Descriptor

**目的**: 嘗試以超過最大允許容量配置兩個一般型 Boot LU，驗證裝置回傳 invalid value。

| Field | Value | 說明 |
|-------|-------|------|
| Opcode | 0x08 | WRITE DESCRIPTOR |
| IDN | 0x01 | Configuration Descriptor |
| Index | 0x00 | |
| Selector | 0x00 | |
| Unit Desc 0 — bLUEnable | 0x01 | LU enabled |
| Unit Desc 0 — bBootLunID | 0x01 | Boot LU A |
| Unit Desc 0 — bMemoryType | 0x00 | Normal (JESD220H Table 14.13) |
| Unit Desc 0 — dLUNumAllocUnits | **> Max capacity** | 故意超出最大容量（OOR） |
| Unit Desc 1 — bLUEnable | 0x01 | LU enabled |
| Unit Desc 1 — bBootLunID | 0x02 | Boot LU B |
| Unit Desc 1 — bMemoryType | 0x00 | Normal |
| Unit Desc 1 — dLUNumAllocUnits | **> Max capacity** | 故意超出最大容量（OOR） |

**Expected**: QUERY RESPONSE returns invalid value（Response field ≠ 0x00）。

**UFS SPEC Reference**: JESD220H Section 14.1.4.3, Section 14.1.6.3, Section 10.7.9.8

---

### Step 1.3: 混合型 Boot LU Configuration — 容量超過 Max（OOR）

**UFS QUERY**: `WRITE DESCRIPTOR (08h)` — Configuration Descriptor

**目的**: 嘗試以超過最大允許容量配置混合型 Boot LU（A 增強型 + B 一般型），驗證裝置回傳 invalid value。

| Field | Value | 說明 |
|-------|-------|------|
| Opcode | 0x08 | WRITE DESCRIPTOR |
| IDN | 0x01 | Configuration Descriptor |
| Index | 0x00 | |
| Selector | 0x00 | |
| Unit Desc 0 — bLUEnable | 0x01 | LU enabled |
| Unit Desc 0 — bBootLunID | 0x01 | Boot LU A |
| Unit Desc 0 — bMemoryType | 0x03 | Enhanced |
| Unit Desc 0 — dLUNumAllocUnits | **> Max capacity** | 故意超出最大容量（OOR） |
| Unit Desc 1 — bLUEnable | 0x01 | LU enabled |
| Unit Desc 1 — bBootLunID | 0x02 | Boot LU B |
| Unit Desc 1 — bMemoryType | 0x00 | Normal |
| Unit Desc 1 — dLUNumAllocUnits | **> Max capacity** | 故意超出最大容量（OOR） |

**Expected**: QUERY RESPONSE returns invalid value（Response field ≠ 0x00）。

**UFS SPEC Reference**: JESD220H Section 14.1.4.3, Section 14.1.6.3, Section 10.7.9.8

---

## Phase 2 — Boot LUN 有效配置

### Step 2.1: 有效容量 Boot LU Configuration

**UFS QUERY**: `WRITE DESCRIPTOR (08h)` — Configuration Descriptor

**目的**: 以有效容量配置兩個 Boot LU（A 增強型 + B 一般型），作為 Phase 3 OOR 存取
測試的前置設定。

| Field | Value | 說明 |
|-------|-------|------|
| Opcode | 0x08 | WRITE DESCRIPTOR |
| IDN | 0x01 | Configuration Descriptor |
| Index | 0x00 | |
| Selector | 0x00 | |
| Unit Desc 0 — bLUEnable | 0x01 | LU enabled |
| Unit Desc 0 — bBootLunID | 0x01 | Boot LU A |
| Unit Desc 0 — bMemoryType | 0x03 | Enhanced |
| Unit Desc 0 — dLUNumAllocUnits | 有效值（≤ Max） | 不超過最大允許容量 |
| Unit Desc 1 — bLUEnable | 0x01 | LU enabled |
| Unit Desc 1 — bBootLunID | 0x02 | Boot LU B |
| Unit Desc 1 — bMemoryType | 0x00 | Normal |
| Unit Desc 1 — dLUNumAllocUnits | 有效值（≤ Max） | 不超過最大允許容量 |

**UFS SPEC Reference**: JESD220H Section 14.1.4.3, Section 14.1.6.3, Section 10.7.9.8

---

## Phase 3 — Boot LUN OOR 資料存取驗證（Write / Erase / Read）

### Step 3.1: WRITE(10) OOR — LBA 超出 Boot LU 容量

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對 Boot LU 執行 WRITE(10)，使用超出 dLUNumAllocUnits 範圍的 LBA，
驗證裝置回傳 CHECK_CONDITION。

| Field | Value | 說明 |
|-------|-------|------|
| Opcode | 0x2A | WRITE(10) |
| LUN | Boot LU (A 或 B) | |
| LBA | **> dLUNumAllocUnits** | 故意超出 Boot LU 容量範圍（OOR） |
| Transfer Length | 0x01 (1 block) | |
| WRPROTECT | 0x00 | |

**Expected**: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL BLOCK ADDRESS OUT OF RANGE(21h)。

**UFS SPEC Reference**: JESD220H Section 11.2 (WRITE(10) command), SPC-5 Section 4.5.6 (ILLEGAL_REQUEST), SBC-5 Section 5.2.2 (LBA OUT OF RANGE)

---

### Step 3.2: UNMAP OOR — LBA 超出 Boot LU 容量

**SCSI CMD**: `UNMAP (42h)`

**目的**: 對 Boot LU 執行 UNMAP，使用超出 dLUNumAllocUnits 範圍的 LBA，
驗證裝置回傳 CHECK_CONDITION。

| Field | Value | 說明 |
|-------|-------|------|
| Opcode | 0x42 | UNMAP |
| LUN | Boot LU (A 或 B) | |
| UNMAP Block Descriptor — LBA | **> dLUNumAllocUnits** | 故意超出 Boot LU 容量範圍（OOR） |
| UNMAP Block Descriptor — Block Count | 0x01 (1 block) | |
| ANCHOR | 0x00 | |

**Expected**: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL BLOCK ADDRESS OUT OF RANGE(21h)。

**UFS SPEC Reference**: JESD220H Section 11.8 (UNMAP command), SBC-5 Section 5.2.2

---

### Step 3.3: READ(10) OOR — LBA 超出 Boot LU 容量

**SCSI CMD**: `READ(10) (28h)`

**目的**: 對 Boot LU 執行 READ(10)，使用超出 dLUNumAllocUnits 範圍的 LBA，
驗證裝置回傳 CHECK_CONDITION。

| Field | Value | 說明 |
|-------|-------|------|
| Opcode | 0x28 | READ(10) |
| LUN | Boot LU (A 或 B) | |
| LBA | **> dLUNumAllocUnits** | 故意超出 Boot LU 容量範圍（OOR） |
| Transfer Length | 0x01 (1 block) | |
| RDPROTECT | 0x00 | |

**Expected**: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h), ASC=LOGICAL BLOCK ADDRESS OUT OF RANGE(21h)。

**UFS SPEC Reference**: JESD220H Section 11.1 (READ(10) command), SBC-5 Section 5.2.2

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x08 | WRITE DESCRIPTOR | 寫入 Device Descriptor (bBootLunEn) 與 Configuration Descriptor (Boot LU 配置) |

### Descriptor IDN

| IDN | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x00 | Device Descriptor | 設定 bBootLunEn 以啟用 Boot LU A/B |
| 0x01 | Configuration Descriptor | 配置 Boot LU 容量（dLUNumAllocUnits）與記憶體類型（bMemoryType） |

### Configuration Descriptor Unit Descriptor 關鍵欄位

| Offset | 欄位 | 大小 | 說明 |
|:---|:---|:---|:---|
| 0x00 | bLUEnable | 1 | LU 啟用旗標 (0x00=disabled, 0x01=enabled) |
| 0x01 | bBootLunID | 1 | Boot LUN ID (0x00=非Boot LU, 0x01=Boot LU A, 0x02=Boot LU B) |
| 0x02 | bMemoryType | 1 | 記憶體類型 (0x00=Normal, 0x03=Enhanced) |
| 0x04–0x07 | dLUNumAllocUnits | 4 | LU 容量（Allocation Unit 數量） |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB Size | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | 對 Boot LU 執行 OOR 讀取（LBA > 容量） |
| 0x2A | WRITE(10) | 10 | 對 Boot LU 執行 OOR 寫入（LBA > 容量） |
| 0x42 | UNMAP | 10 | 對 Boot LU 執行 OOR Erase（LBA > 容量） |

### SCSI Sense Data（本 Pattern 預期的 Error Response）

| 欄位 | 值 | 說明 |
|:---|:---|:---|
| SENSE_KEY | 0x05 | ILLEGAL REQUEST |
| ASC | 0x21 | LOGICAL BLOCK ADDRESS OUT OF RANGE |
| ASCQ | 0x00 | |

---

## 附錄 C — UFS Descriptor 操作確認

本 Pattern 未使用 RESET 或 Power Cycle。Boot LUN 配置透過 WRITE DESCRIPTOR
完成，Configuration Descriptor 變更後如需生效，由測試框架根據實作需求決定
是否插入 Reset（JIRA Pattern 未明確要求）。

---

## 自我驗證

- Tree Diagram leaf steps: **9**（Phase 0: 2 (0.1~0.2), Phase 1: 3 (1.1~1.3), Phase 2: 1 (2.1), Phase 3: 3 (3.1~3.3) → Total: 9）
- `### Step` sections: **9** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓
  - 有 Expected 的 step: 6 個（Step 1.1~1.3 → JIRA Step 3 "check resp should be invalid value"；Step 3.1~3.3 → JIRA Step 5 "check sense key be illegal_request & ASC be logical_blk_address_out_of_range"）
  - 無 Expected 的 step: 3 個（Step 0.1, 0.2, 2.1 → JIRA Step 1, 2, 4 未描述預期結果）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
