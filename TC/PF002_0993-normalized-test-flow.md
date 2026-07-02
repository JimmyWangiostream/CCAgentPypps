---
title: PF002_0993_MultiCmdInUpdateBootCode-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_0993, scsi-cmd, writebooster, boot-lu, gc, flush, interleave]
description: >
  驗證在 Boot Code 更新期間，當 GC 觸發 WriteBooster Buffer Flush 時，Host 可以同時
  執行多種不同類型的 Host Command（WRITE/READ/UNMAP/FORMAT UNIT/FFU/SSU/QUERY/Idle）
  而不影響 Boot Code 更新的正確性。測試涵蓋 WriteBooster Shared Mode 配置、GC 情境
  觸發、Power Cycle 後 Flush 驗證，以及 8 小時 Burn-in。
sources:
  - JIRA: PF002_0993 (SYSTCUFS-1284)
  - UFS Spec: JESD220H Section 6.2 (WriteBooster), 10.7.8 (Query Request), 10.7.9 (Query Descriptor), 10.9 (SCSI Command Set), 11.1 (Power Cycle), 11.6.7 (FFU), 12.3 (Boot LU), 14.4 (Configuration Descriptor)
---

# PF002_0993 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證在 Boot Code 寫入更新期間，同時對 Device 發出多種不同類型的 Host Command
（WRITE/READ/UNMAP/FORMAT UNIT/FFU/SSU/QUERY/Idle）時，WriteBooster Buffer Flush
機制能正確運作，Boot Code 資料不產生損毀。此 Pattern 首先透過大量 Sequential Write
觸發 BG GC，使 WriteBooster Buffer 填滿後觸發 Flush 通知（wExceptionEventStatus
Bit[2]），再於 Power Cycle 後驗證 Flush 完成的資料正確性。最後在 Disable WB 後執行
Boot Code 更新，並於更新期間交錯執行所有 Host Command 排序組合，搭配 8 小時 Burn-in
確保長時間穩定性。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | 確認測試 IC + NAND 是否為 8317 BICS5, UFS 版本 3.1 或 2.2 | Step 0.1 |
| Step 2 | Config WriteBooster, Shared mode, max buffer, 預期 success | Step 1.1 |
| Step 3 | Set flag fWriteBoosterEn=1, 預期 success | Step 1.2 |
| Step 4 | Sequential Write 15 TLC VB data to Boot LU A/B (Trigger BG GC), expect success | Step 1.3, 1.4 |
| Step 5 | Power Cycle, 預期 success | Step 2.1 |
| Step 6 | Set flag fWriteBoosterBufferFlushEn=1, expect success | Step 2.2 |
| Step 7 | Check wExceptionEventStatus Bit[2]==1, expect success | Step 2.3 |
| Step 8 | Read Boot W-LU (LUN=B0h) and compare step 4 data, 預期 success | Step 3.1 |
| Step 9 | Set flag fWriteBoosterEn=0 (Disable WB), 預期 success | Step 3.2 |
| Step 10 | Sequential Write 15 TLC VB data to Boot LU A/B (Update Boot Code), expect success | Step 4.1, 4.2 |
| Step 11 | 確保所有 Host Command 排序都執行過一次: (1)WRITE 1GB non-active Boot LU (2)READ (3)UNMAP non-Boot LU (4)FORMAT UNIT non-Boot LU (5)FFU (6)SSU (7)QUERY (8)Idle >500ms | Step 4.3–4.10 |
| Step 12 | Burn in 8hr | Burn-in Note |

---

## 測試架構（Tree Diagram）

```
PF002_0993 Test Flow
│
├── Phase 0: Pre-condition — 硬體相容性檢查
│   └── Step 0.1: HW Check — IC/NAND/Version 確認
│
├── Phase 1: WriteBooster Configuration & GC Trigger
│   ├── Step 1.1: WRITE DESCRIPTOR (0x08) — Config WB Shared Mode, Max Buffer → Expected: device response success
│   ├── Step 1.2: SET FLAG (0x02) — fWriteBoosterEn=1 → Expected: device response success
│   ├── Step 1.3: WRITE(10) (0x2A) — 15 TLC VB to Boot LU A (W-LUN B0h) → Expected: device response success
│   └── Step 1.4: WRITE(10) (0x2A) — 15 TLC VB to Boot LU B (W-LUN B1h) → Expected: device response success
│
├── Phase 2: Power Cycle & Flush Verification
│   ├── Step 2.1: Power Cycle → Expected: device response success
│   ├── Step 2.2: SET FLAG (0x02) — fWriteBoosterBufferFlushEn=1 → Expected: device response success
│   └── Step 2.3: READ ATTRIBUTE (0x03) — wExceptionEventStatus Bit[2] → Expected: Bit[2]==1
│
├── Phase 3: Data Integrity Check & WB Disable
│   ├── Step 3.1: READ(10) (0x28) — Boot W-LUN B0h, Compare Step 1.3/1.4 Data → Expected: device response success, Data Match
│   └── Step 3.2: SET FLAG (0x02) — fWriteBoosterEn=0 → Expected: device response success
│
└── Phase 4: Boot Code Update with Multi-Command Interleaving
    ├── Step 4.1: WRITE(10) (0x2A) — 15 TLC VB to Boot LU A (W-LUN B0h) → Expected: device response success
    ├── Step 4.2: WRITE(10) (0x2A) — 15 TLC VB to Boot LU B (W-LUN B1h) → Expected: device response success
    │
    └── Sub-Phase 4.X: Interleaved Host Commands（所有排序組合）
        ├── Step 4.3: WRITE(10) (0x2A) — 1GB to non-active Boot LU
        ├── Step 4.4: READ(10) (0x28) — Read from any LU
        ├── Step 4.5: UNMAP (0x42) — non-Boot LU range
        ├── Step 4.6: FORMAT UNIT (0x04) — non-Boot LU
        ├── Step 4.7: WRITE BUFFER (0x3B) — FFU Download & Save
        ├── Step 4.8: START STOP UNIT (0x1B) — SSU
        ├── Step 4.9: QUERY REQUEST — Generic Query (READ FLAG/ATTRIBUTE/DESCRIPTOR)
        └── Step 4.10: IDLE — >500ms

Burn-in Duration: 8 hours
```

---

## Phase 0 — Pre-condition：硬體相容性檢查

### Step 0.1: 裝置相容性檢查

**目的**: 確認測試對象的 IC、NAND 及 UFS 版本符合 Pattern 要求的配置。不符合時應判定為 `NOT SUPPORTED` 並終止測試。

**Check**: IC=8317, NAND=BICS5 (for KIC), UFS Version ≥ 3.1 or 2.2

**Branch Logic**: 若不支援 → 判定 `NOT SUPPORTED`，終止測試。

**UFS SPEC Reference**: JESD220H Section 10.7.9 (Device Descriptor — bDeviceVersion)

---

## Phase 1 — WriteBooster Configuration & GC Trigger

### Step 1.1: Config WriteBooster — Shared Mode with Max Buffer

**UFS QUERY**: `WRITE DESCRIPTOR (0x08)` — Configuration Descriptor

**目的**: 設定 WriteBooster 為 Shared Buffer 模式並配置最大 Buffer 容量，為後續 GC 觸發 Flush 做準備。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| Descriptor IDN | 0x01 (Configuration Descriptor) |
| bWriteBoosterBufferType | 0x01 (Shared Buffer) |
| dLUNumWriteBoosterBufferAllocUnits | Max (依 Device 支援上限) |

**Expected**: device response success。

**UFS SPEC Reference**: JESD220H Section 10.7.9, 14.4 (Configuration Descriptor), 6.2 (WriteBooster)

---

### Step 1.2: Enable WriteBooster

**UFS QUERY**: `SET FLAG (0x02)` — fWriteBoosterEn

**目的**: 啟用 WriteBooster 功能，使後續 Host Write 資料經過 WB Buffer。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| Flag IDN | 0x0E (fWriteBoosterEn) |

**Expected**: device response success。

**UFS SPEC Reference**: JESD220H Section 10.7.8, 14.2 (fWriteBoosterEn)

---

### Step 1.3: Sequential Write to Boot LU A — Trigger GC

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 對 Boot LU A 寫入 15 個 TLC VB 的 Sequential Data，填入 WriteBooster Buffer 並觸發 Background GC。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | W-LUN B0h (Boot LU A) |
| LBA | 0x00000000 |
| Transfer Length | 15 TLC VB (依 LU block size 換算) |
| FUA | 0 |

**Expected**: device response success。

**UFS SPEC Reference**: JESD220H Section 10.9 (WRITE(10)), 12.3 (Boot LU)

---

### Step 1.4: Sequential Write to Boot LU B — Trigger GC

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 對 Boot LU B 寫入 15 個 TLC VB 的 Sequential Data，持續填入 WB Buffer 以最大化 GC 壓力。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | W-LUN B1h (Boot LU B) |
| LBA | 0x00000000 |
| Transfer Length | 15 TLC VB (依 LU block size 換算) |
| FUA | 0 |

**Expected**: device response success。

**UFS SPEC Reference**: JESD220H Section 10.9 (WRITE(10)), 12.3 (Boot LU)

---

## Phase 2 — Power Cycle & Flush Verification

### Step 2.1: Power Cycle

**操作**: `Power Cycle`

**目的**: 執行裝置電源關閉後重新啟動，觸發 WriteBooster Buffer 中未 Flush 資料的 Background Flush 程序。

| Field | Value |
|-------|-------|
| 操作類型 | Power Cycle (VCC off → VCC on) |

**Expected**: device response success（Power Cycle 完成，Device 重新就緒）。

**UFS SPEC Reference**: JESD220H Section 11.1 (Power On/Off Sequences)

---

### Step 2.2: Enable WriteBooster Buffer Flush

**UFS QUERY**: `SET FLAG (0x02)` — fWriteBoosterBufferFlushEn

**目的**: 啟用 WB Buffer Flush 功能，允許 Device 在 Buffer 滿載時觸發 Flush。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| Flag IDN | 0x0F (fWriteBoosterBufferFlushEn) |

**Expected**: device response success。

**UFS SPEC Reference**: JESD220H Section 10.7.8, 14.2 (fWriteBoosterBufferFlushEn)

---

### Step 2.3: Check Exception Event Status — WB Flush Notification

**UFS QUERY**: `READ ATTRIBUTE (0x03)` — wExceptionEventStatus

**目的**: 讀取 Exception Event Status，確認 Bit[2] 已置起，表示 WriteBooster Buffer Flush 通知已被 Device 觸發。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| Attribute IDN | 0x0D (wExceptionEventStatus, lower 16-bit of dExceptionEventStatus) |
| Check | Bit[2] == 1 |

**Expected**: wExceptionEventStatus Bit[2]==1。

**UFS SPEC Reference**: JESD220H Section 10.7.8, 14.3 (wExceptionEventStatus)

---

## Phase 3 — Data Integrity Check & WB Disable

### Step 3.1: Read Back & Compare Boot LU Data

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 讀回 Boot W-LUN B0h 中的資料，與 Step 1.3/1.4 寫入的資料進行比對，確認經 Power Cycle 與 Flush 後資料完整性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | W-LUN B0h (Boot LU A) |
| LBA | 0x00000000 |
| Transfer Length | 15 TLC VB (與 Step 1.3 相同) |

**Expected**: device response success, Data Match。

**UFS SPEC Reference**: JESD220H Section 10.9 (READ(10)), 12.3 (Boot LU)

---

### Step 3.2: Disable WriteBooster

**UFS QUERY**: `SET FLAG (0x02)` — fWriteBoosterEn = 0

**目的**: 關閉 WriteBooster 功能，為後續 Boot Code 更新做準備（更新期間不使用 WB Buffer）。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| Flag IDN | 0x0E (fWriteBoosterEn) |
| Set Value | 0 (Clear) |

> **Note**: 此處使用 SET FLAG 將值設為 0（等同 CLEAR FLAG 效果；亦可使用 CLEAR FLAG (0x05), Flag IDN 0x0E）。

**Expected**: device response success。

**UFS SPEC Reference**: JESD220H Section 10.7.8, 14.2 (fWriteBoosterEn)

---

## Phase 4 — Boot Code Update with Multi-Command Interleaving

> **JIRA Step 11 說明**: 在 Boot Code 寫入期間，確保以下所有 Host Command 的排序組合
> 至少都執行過一次。各命令之間可交錯穿插於 Boot Code Write 之間執行。

### Step 4.1: Boot Code Write to Boot LU A

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 在 WriteBooster 已關閉的狀態下，對 Boot LU A 寫入 15 TLC VB 的 Boot Code 更新資料。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | W-LUN B0h (Boot LU A) |
| LBA | 0x00000000 |
| Transfer Length | 15 TLC VB (依 LU block size 換算) |
| FUA | 0 |

**Expected**: device response success。

**UFS SPEC Reference**: JESD220H Section 10.9 (WRITE(10)), 12.3 (Boot LU)

---

### Step 4.2: Boot Code Write to Boot LU B

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 在 WriteBooster 已關閉的狀態下，對 Boot LU B 寫入 15 TLC VB 的 Boot Code 更新資料。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | W-LUN B1h (Boot LU B) |
| LBA | 0x00000000 |
| Transfer Length | 15 TLC VB (依 LU block size 換算) |
| FUA | 0 |

**Expected**: device response success。

**UFS SPEC Reference**: JESD220H Section 10.9 (WRITE(10)), 12.3 (Boot LU)

---

### Step 4.3: Interleaved — WRITE 1GB to Non-Active Boot LU

**SCSI CMD**: `WRITE(10) (0x2A)` or `WRITE(16) (0x8A)` (依 LBA 範圍)

**目的**: 在 Boot Code 更新期間，交錯對非當前 Active 的 Boot LU 寫入 1GB 資料。

| Field | Value |
|-------|-------|
| Opcode | 0x2A / 0x8A |
| LUN | 非 Active Boot LU (B0h or B1h) |
| LBA | 0x00000000 |
| Transfer Length | 1GB 對應的 Block Count (依 LU block size 換算) |
| FUA | 0 |

**UFS SPEC Reference**: JESD220H Section 10.9 (WRITE(10)/WRITE(16)), 12.3 (Boot LU)

---

### Step 4.4: Interleaved — READ Command

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 Boot Code 更新期間，交錯執行 READ 命令讀取任意 LU 資料。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 任意 LU |
| LBA | 0x00000000 |
| Transfer Length | 任意 (1~max) |

**UFS SPEC Reference**: JESD220H Section 10.9 (READ(10))

---

### Step 4.5: Interleaved — UNMAP (Non-Boot LU)

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 在 Boot Code 更新期間，交錯對非 Boot LU 範圍執行 UNMAP 操作。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | 非 Boot LU (非 B0h / B1h) |
| UNMAP Parameter List | UNMAP Block Descriptor (LBA + Block Count) |

**UFS SPEC Reference**: JESD220H Section 10.9 (UNMAP)

---

### Step 4.6: Interleaved — FORMAT UNIT (Non-Boot LU)

**SCSI CMD**: `FORMAT UNIT (0x04)`

**目的**: 在 Boot Code 更新期間，交錯對非 Boot LU 執行 FORMAT UNIT。

| Field | Value |
|-------|-------|
| Opcode | 0x04 |
| LUN | 非 Boot LU (非 B0h / B1h) |
| FmtData | 0 (無參數格式) |
| CmpList | 0 |
| Defect List Format | 0x00 |

**UFS SPEC Reference**: JESD220H Section 10.9 (FORMAT UNIT)

---

### Step 4.7: Interleaved — FFU (Field Firmware Update)

**SCSI CMD**: `WRITE BUFFER (0x3B)` — Mode = FFU Download & Save

**目的**: 在 Boot Code 更新期間，交錯執行 FFU 下載並儲存操作。

| Field | Value |
|-------|-------|
| Opcode | 0x3B |
| Mode | 0x0E (Download with Offset & Save, per JESD220H 11.6.7) |
| Buffer ID | 0x00 |
| Buffer Offset | 0x000000 |
| Parameter List Length | Firmware Image Size |

**UFS SPEC Reference**: JESD220H Section 11.6.7 (Field Firmware Update)

---

### Step 4.8: Interleaved — SSU (START STOP UNIT)

**SCSI CMD**: `START STOP UNIT (0x1B)`

**目的**: 在 Boot Code 更新期間，交錯執行 START STOP UNIT 進行 Power Condition 切換。

| Field | Value |
|-------|-------|
| Opcode | 0x1B |
| START | 1 (Active) or 0 (Stop) |
| Power Condition | 0x01 (Active) or 0x02 (Sleep) |

**UFS SPEC Reference**: JESD220H Section 10.9 (START STOP UNIT)

---

### Step 4.9: Interleaved — QUERY Request

**UFS QUERY**: `QUERY REQUEST` — Generic (READ FLAG / READ ATTRIBUTE / READ DESCRIPTOR)

**目的**: 在 Boot Code 更新期間，交錯執行任意 UFS Query Request（如讀取 Flag、Attribute 或 Descriptor）。

| Field | Value |
|-------|-------|
| Query Opcode | 0x01 (READ FLAG) / 0x03 (READ ATTRIBUTE) / 0x07 (READ DESCRIPTOR) |
| Target IDN | 任意有效 IDN |

**UFS SPEC Reference**: JESD220H Section 10.7.8, 10.7.9 (Query Request)

---

### Step 4.10: Interleaved — Idle > 500ms

**操作**: `IDLE`

**目的**: 在 Boot Code 更新期間，交錯插入超過 500ms 的 Idle 等待，模擬 Host 間歇性無操作情境。

| Field | Value |
|-------|-------|
| 操作類型 | Host Idle (no command sent) |
| Duration | > 500 ms |

**UFS SPEC Reference**: N/A (Host-side timing)

---

### Burn-in：8 小時持續執行

**目的**: 在完成所有排序組合至少一次後，持續以 Burn-in 模式執行 Phase 4 的 Boot Code Update
+ Multi-Command Interleaving 流程共 8 小時，驗證長時間穩定性。

| Field | Value |
|-------|-------|
| 持續時間 | 8 hours (28800 seconds) |
| 執行內容 | Phase 4 Step 4.1–4.10 反覆執行 |

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x02 | SET FLAG | 設定 fWriteBoosterEn / fWriteBoosterBufferFlushEn |
| 0x03 | READ ATTRIBUTE | 讀取 wExceptionEventStatus (Bit[2]) |
| 0x08 | WRITE DESCRIPTOR | 配置 Configuration Descriptor (WB Shared + Max Buffer) |
| 0x01/0x03/0x07 | READ FLAG / READ ATTRIBUTE / READ DESCRIPTOR | 交錯 Query (Step 4.9) |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x0E | fWriteBoosterEn | Volatile (Set/Clear) | 啟用/關閉 WriteBooster (Step 1.2, 3.2) |
| 0x0F | fWriteBoosterBufferFlushEn | Volatile (Set/Clear) | 啟用 WB Buffer Flush (Step 2.2) |

### Attribute IDN

| IDN | 名稱 | Size | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|:---|
| 0x0D | wExceptionEventStatus | 2 | Read-Only | 檢查 WB Flush 通知 Bit[2] (Step 2.3) |

### Descriptor IDN

| IDN | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x01 | Configuration Descriptor | 設定 bWriteBoosterBufferType (Shared) + Buffer 配置 (Step 1.1) |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB Size | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x04 | FORMAT UNIT | 6 | 格式化非 Boot LU (Step 4.6) |
| 0x1B | START STOP UNIT | 6 | Power Condition 切換 (Step 4.8) |
| 0x28 | READ(10) | 10 | 讀取 Boot LU 資料比對 / 交錯 Read (Step 3.1, 4.4) |
| 0x2A | WRITE(10) | 10 | 寫入 Boot LU / 交錯 Write (Step 1.3, 1.4, 4.1, 4.2, 4.3) |
| 0x3B | WRITE BUFFER | 10 | FFU Download & Save (Step 4.7) |
| 0x42 | UNMAP | 10 | 非 Boot LU UNMAP (Step 4.5) |
| 0x8A | WRITE(16) | 16 | 1GB 寫入 (Step 4.3, 依 LBA 範圍選用) |

---

## 附錄 C — 本 Pattern 使用的特殊操作

| 操作 | 說明 | 本 Pattern 用途 |
|:---|:---|:---|
| Power Cycle | VCC off → VCC on, 重新初始化 Device | 觸發 WB Buffer Flush 程序 (Step 2.1) |
| Idle | Host 無 Command 發送，等待指定時間 | 模擬 Host 間歇 (Step 4.10) |
| Burn-in | 長時間壓力測試，反覆執行指定流程 | 8hr 穩定性驗證 |

---

## 自我驗證

- Tree Diagram leaf steps: **20**（Phase 0: 1 (0.1), Phase 1: 4 (1.1~1.4), Phase 2: 3 (2.1~2.3), Phase 3: 2 (3.1~3.2), Phase 4: 10 (4.1~4.10) → Total: 20）
- `### Step` sections: **20** ✓
- `→ Expected:` 來自 JIRA 原文的 Step: **11**（1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 3.2, 4.1, 4.2）
- 無 `→ Expected:`（JIRA 未明確指出預期結果）的 Step: **9**（0.1, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文：Step 2, 3, 4, 5, 6, 7, 8, 9, 10）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
