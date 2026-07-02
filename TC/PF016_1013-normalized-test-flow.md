---
title: PF016_1013_D_Idle_Power_Write_Read_Smart_info-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf016_1013, scsi-cmd, power, writebooster, hibernate, smart-info, burn-in]
description: >
  驗證 UFS 裝置在 WriteBooster + Hibernate 循環下的 Idle Power 行為。
  透過 24 小時燒機循環（隨機讀寫 → Hibernate Enter/Exit → Smart Info 比對 →
  混合隨機操作 → Suspend → 電流測量），確認 VCCQ 待機電流不超標，且
  Smart Info 計數器（h8_trigger_bkops_cnt、cache_not_data_trigger_suspend_cnt）
  在燒機期間正常遞增。
sources:
  - JIRA: PF016_1013 (SYSTCUFS-1295)
  - UFS Spec: JESD220H Section 10.7, 11.6, 14.2, 14.3
---

# PF016_1013 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置在 WriteBooster 啟用狀態下，經過長時間 Random Write/Read +
Hibernate 循環後，Auto Standby 下的 VCCQ 電流仍維持在規範內（≤ 2mA），
且 Smart Info 計數器正常遞增。測試以 24 小時燒機循環執行。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 3 | Clear WRITE_BOOSTER_EN, Clear WRITE_BOOSTER_BUFF_FLUSH_EN, Enable WRITE_BOOSTER_BUFF_FLUSH_DURINGHIB | Phase 0 (Step 0.1~0.3) |
| Step 5 | VU cmd get smart info h8_trigger_bkops_cnt, expect success | Phase 1 (Step 1.1) |
| Step 6 | Push Random write cmd ×10 | Phase 2 (Step 2.1) |
| Step 7 | Push Random read cmd ×10 | Phase 2 (Step 2.2) |
| Step 8 | Push hibernate enter cmd | Phase 2 (Step 2.3) |
| Step 9 | Execute Cmd Sequence | Phase 2 (Step 2.4) |
| Step 10 | Idle 1s & hibernate exit | Phase 2 (Step 2.5) |
| Step 11 | VU cmd get smart info h8_trigger_bkops_cnt, expect > Step 5 | Phase 3 (Step 3.1) |
| Step 12 | VU cmd get smart info cache_not_data_trigger_suspend_cnt, expect success | Phase 3 (Step 3.2) |
| Step 13 | 隨機插入 RPMB write / Boot LUN write / FUA write | Phase 4 (Step 4.1) |
| Step 14 | Idle until bkops status = 0 | Phase 5 (Step 5.1) |
| Step 15 | 量測 Auto standby 後的電流 | Phase 5 (Step 5.2) |
| Step 16 | VCCQ 電流不應超過 2mA，超過則 Fail | Phase 6 (Step 6.1) |
| Step 17 | VU cmd get smart info cache_not_data_trigger_suspend_cnt, expect > Step 12 | Phase 6 (Step 6.2) |
| Step 18 | Loop Step 4 to step 15 until 燒機滿 24 小時 | Loop 包裝 Phase 2~5 |

> **注意**：原始 JIRA 缺少 Step 4。Loop 敘述為「Loop Step 4 to step 15」，
> 本正規化以 Step 5（首次 Smart Info 讀取後）至 Step 15（電流測量）作為 Loop 主體。
> Step 3（WB Config）為一次性初始設定，不納入 Loop。
> Step 16~17 為燒機完成後的最終驗證。

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF016_1013 Test Flow
│
├── Phase 0: Pre-condition — WriteBooster 組態設定
│   ├── Step 0.1: CLEAR FLAG — fWriteBoosterEn (0x0E)
│   ├── Step 0.2: CLEAR FLAG — fWriteBoosterBufferFlushEn (0x0F)
│   └── Step 0.3: SET FLAG — fWriteBoosterBufferFlushDuringHibernate (0x10)
│
├── Phase 1: 初始 Smart Info 擷取（Baseline）
│   └── Step 1.1: VU READ BUFFER — 取得 h8_trigger_bkops_cnt → Expected: device response success
│
└── Loop (24hr burn-in, JIRA Step 5~15)
    │
    ├── Phase 2: Random Write/Read + Hibernate 循環
    │   ├── Step 2.1: WRITE(10) — Random Write ×10（Exe_cmd_seq push）
    │   ├── Step 2.2: READ(10) — Random Read ×10（Exe_cmd_seq push）
    │   ├── Step 2.3: START STOP UNIT — Hibernate Enter
    │   ├── Step 2.4: Execute Command Sequence（執行已推送的 CMD queue）
    │   └── Step 2.5: START STOP UNIT — Hibernate Exit
    │
    ├── Phase 3: Post-Hibernate Smart Info 驗證
    │   ├── Step 3.1: VU READ BUFFER — h8_trigger_bkops_cnt → Expected: 計數值 > Step 1.1 記錄值
    │   └── Step 3.2: VU READ BUFFER — cache_not_data_trigger_suspend_cnt → Expected: device response success
    │
    ├── Phase 4: 混合隨機操作（Branch）
    │   └── Step 4.1: Random Branch — RPMB Write / Boot LUN Write / FUA Write
    │
    └── Phase 5: Suspend 等待 + 電流測量
        ├── Step 5.1: READ ATTRIBUTE — bBackgroundOpStatus (Poll until 0)
        └── Step 5.2: 硬體量測 — Auto Standby 電流

└── Phase 6: 燒機後最終驗證
    ├── Step 6.1: VCCQ 電流檢查 → Expected: VCCQ ≤ 2mA, 超過則判定 Fail
    └── Step 6.2: VU READ BUFFER — cache_not_data_trigger_suspend_cnt → Expected: 計數值 > Step 3.2 記錄值
```

**Expected 統計**：此 Pattern 共有 5 個 Step 在原始 JIRA 中明確指出預期結果。
Step 0.1~0.3, 2.1~2.5, 4.1, 5.1~5.2 在 JIRA 中無預期結果描述，故不填入 `→ Expected:`。

---

## Phase 0 — Pre-condition：WriteBooster 組態設定

### Step 0.1: CLEAR FLAG fWriteBoosterEn

**UFS QUERY**: `CLEAR FLAG (0x05)` — fWriteBoosterEn (IDN 0x0E)

**目的**: 關閉 WriteBooster 功能，確保從已知初始狀態開始測試。

| Field | Value |
|-------|-------|
| Query Opcode | 0x05 (CLEAR FLAG) |
| bFlagIDN | 0x0E (fWriteBoosterEn) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.5 (CLEAR FLAG), Section 14.2 (Flags)

---

### Step 0.2: CLEAR FLAG fWriteBoosterBufferFlushEn

**UFS QUERY**: `CLEAR FLAG (0x05)` — fWriteBoosterBufferFlushEn (IDN 0x0F)

**目的**: 關閉 WriteBooster Buffer Flush，為後續 Enable Flush During Hibernate 做準備。

| Field | Value |
|-------|-------|
| Query Opcode | 0x05 (CLEAR FLAG) |
| bFlagIDN | 0x0F (fWriteBoosterBufferFlushEn) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.5 (CLEAR FLAG), Section 14.2 (Flags)

---

### Step 0.3: SET FLAG fWriteBoosterBufferFlushDuringHibernate

**UFS QUERY**: `SET FLAG (0x02)` — fWriteBoosterBufferFlushDuringHibernate (IDN 0x10)

**目的**: 啟用 Hibernate 期間的 WriteBooster Buffer Flush。
依 JIRA 說明，h8_trigger_bkops 需要此旗標為 Enable 狀態。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| bFlagIDN | 0x10 (fWriteBoosterBufferFlushDuringHibernate) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.3 (SET FLAG), Section 14.2 (Flags)

---

## Phase 1 — 初始 Smart Info 擷取（Baseline）

### Step 1.1: VU READ BUFFER — 取得 h8_trigger_bkops_cnt Baseline

**SCSI CMD**: `READ BUFFER (3Ch)` — Mode = Vendor Specific

**目的**: 透過 Vendor 專屬指令讀取 Smart Info 中的 h8_trigger_bkops_cnt 計數器，
作為後續比對的 Baseline 值。儲存此值供 Step 3.1 比較使用。

| Field | Value |
|-------|-------|
| Opcode | 0x3C |
| Mode | VU (Vendor Specific, byte-level payload) |
| 讀取目標 | h8_trigger_bkops_cnt (Smart Info counter) |
| LUN | LUN0 |

**Expected**: device response success.

> **VU 細節**：原始 JIRA 以 "Vendor cmd to get smart info" 描述，此處使用
> READ BUFFER (3Ch) VU Mode 實作。實際 byte-level payload 依 Vendor 實作而定，
> 不屬於 SPEC 定義範圍。

**UFS SPEC Reference**: JESD220H Section 10.7 (READ BUFFER)

---

## Loop — 24hr Burn-in 主體

> **Loop 範圍**：重複 Phase 2 ~ Phase 5，直到累計時間達 24 小時。
> 對應原始 JIRA Step 18：「Loop Step 4 to step 15 until 燒機滿24小時」。
> （原始 JIRA 缺少 Step 4，實際 Loop 主體為 Step 5 ~ Step 15。）

---

## Phase 2 — Random Write/Read + Hibernate 循環

### Step 2.1: WRITE(10) — Random Write ×10（Push to Queue）

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 將 10 次隨機寫入指令推入 Command Queue（Exe_cmd_seq），
不立即執行，等待 Step 2.4 統一批次執行。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | LUN0 |
| LBA | Random(0, TotalCapacity - ChunkSize) |
| Transfer Length | Random(4K, 4M) blocks |
| CMD Count | 10 |
| Execution Mode | Push to Queue（Exe_cmd_seq） |

**Branch Logic**（per JIRA）:
- ChunkSize = Random(4K, 4M)
- LBA = Random(0, TotalCapacity - ChunkSize)
- 共推送 10 個獨立 WRITE(10) CMD

**UFS SPEC Reference**: JESD220H Section 10.7 (WRITE(10))

---

### Step 2.2: READ(10) — Random Read ×10（Push to Queue）

**SCSI CMD**: `READ(10) (28h)`

**目的**: 將 10 次隨機讀取指令推入 Command Queue（Exe_cmd_seq），
不立即執行，等待 Step 2.4 統一批次執行。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | LUN0 |
| LBA | Random(0, TotalCapacity - ChunkSize) |
| Transfer Length | Random(4K, 4M) blocks |
| CMD Count | 10 |
| Execution Mode | Push to Queue（Exe_cmd_seq） |

**Branch Logic**（per JIRA）:
- ChunkSize = Random(4K, 4M)
- LBA = Random(0, TotalCapacity - ChunkSize)
- 共推送 10 個獨立 READ(10) CMD

**UFS SPEC Reference**: JESD220H Section 10.7 (READ(10))

---

### Step 2.3: START STOP UNIT — Hibernate Enter

**SCSI CMD**: `START STOP UNIT (1Bh)`

**目的**: 推送 Hibernate Enter 指令至 Command Queue，
裝置將在執行後進入 Hibernate 低功耗狀態。

| Field | Value |
|-------|-------|
| Opcode | 0x1B |
| POWER CONDITION | Hibernate (per UFS power management) |
| START | 0 (Enter low-power state) |
| Execution Mode | Push to Queue（Exe_cmd_seq） |

**UFS SPEC Reference**: JESD220H Section 10.7 (START STOP UNIT), Section 10.6 (Power Management)

---

### Step 2.4: Execute Command Sequence

**UFS Operation**: Execute Command Sequence（Queue Execution）

**目的**: 執行先前 Step 2.1~2.3 推送至 Command Queue 的所有指令。
依序執行：10 × Random Write → 10 × Random Read → Hibernate Enter。

| Field | Value |
|-------|-------|
| 執行模式 | Queue Execution（批次執行所有已推送 CMD） |
| Queue 內容 | 10× WRITE(10) + 10× READ(10) + 1× START STOP UNIT (Hibernate) |

> **說明**：此步驟為 UFS Transport Layer 層級的 Queue Execution 操作，
> 對應原始 JIRA 中的 "Execute Cmd Sequence"。非獨立 SCSI CMD，
> 而是觸發裝置執行已排入 Queue 的指令序列。

**UFS SPEC Reference**: JESD220H Section 10.5 (UTP Command Queue Management)

---

### Step 2.5: START STOP UNIT — Hibernate Exit

**SCSI CMD**: `START STOP UNIT (1Bh)`

**目的**: 裝置從 Hibernate 狀態恢復至 Active 狀態。
JIRA 指定在 Hibernate Enter 後 Idle 1s 再執行 Hibernate Exit。

| Field | Value |
|-------|-------|
| Opcode | 0x1B |
| POWER CONDITION | Active |
| START | 1 (Return to Active) |
| Pre-delay | 1 second idle |

**UFS SPEC Reference**: JESD220H Section 10.7 (START STOP UNIT), Section 10.6 (Power Management)

---

## Phase 3 — Post-Hibernate Smart Info 驗證

### Step 3.1: VU READ BUFFER — h8_trigger_bkops_cnt（比對 Baseline）

**SCSI CMD**: `READ BUFFER (3Ch)` — Mode = Vendor Specific

**目的**: 讀取 Hibernate 循環後的 h8_trigger_bkops_cnt 計數器，
比對是否大於 Phase 1 記錄的 Baseline 值，確認 Hibernate 期間觸發了 BKOPS。

| Field | Value |
|-------|-------|
| Opcode | 0x3C |
| Mode | VU (Vendor Specific) |
| 讀取目標 | h8_trigger_bkops_cnt (Smart Info counter) |
| LUN | LUN0 |

**Expected**: h8_trigger_bkops_cnt 計數值應大於 Step 1.1 記錄之 Baseline 值。

> **VU 細節**：同 Step 1.1，使用 READ BUFFER (3Ch) VU Mode。

**UFS SPEC Reference**: JESD220H Section 10.7 (READ BUFFER)

---

### Step 3.2: VU READ BUFFER — cache_not_data_trigger_suspend_cnt（Baseline）

**SCSI CMD**: `READ BUFFER (3Ch)` — Mode = Vendor Specific

**目的**: 讀取 Smart Info 中的 cache_not_data_trigger_suspend_cnt 計數器，
儲存此值供 Step 6.2 最終比對使用。

| Field | Value |
|-------|-------|
| Opcode | 0x3C |
| Mode | VU (Vendor Specific) |
| 讀取目標 | cache_not_data_trigger_suspend_cnt (Smart Info counter) |
| LUN | LUN0 |

**Expected**: device response success.

> **VU 細節**：同 Step 1.1，使用 READ BUFFER (3Ch) VU Mode。

**UFS SPEC Reference**: JESD220H Section 10.7 (READ BUFFER)

---

## Phase 4 — 混合隨機操作（Branch）

### Step 4.1: Random Branch — RPMB Write / Boot LUN Write / FUA Write

**操作**：隨機選擇下列三種操作之一執行。

**目的**: 在 WriteBooster + Hibernate 循環中插入多樣化的寫入操作，
涵蓋 RPMB、Boot LUN、FUA Write 三種不同 Protocol / LUN 路徑，
以驗證裝置在不同寫入模式下的 Idle Power 行為。

| 分支 | 操作類型 | 詳細參數 |
|:---|:---|:---|
| Branch A | RPMB Authenticated Data Write | Region 0, ChunkSize=512K, LUN=LUN0 |
| Branch B | WRITE(10) to Boot LUN | LUN=LUN1 (Boot LU) |
| Branch C | WRITE(10) with FUA=1 | LUN=LUN0 |

**Branch A: RPMB Authenticated Data Write**

| Field | Value |
|-------|-------|
| SECURITY PROTOCOL OUT Opcode | 0xB5 |
| SECURITY PROTOCOL IN Opcode | 0xA2 |
| SECURITY PROTOCOL | 0x00 (RPMB) |
| RPMB Region | 0 (Region 0) |
| ChunkSize | 512 KB |
| LUN | LUN0 |
| Protocol Flow | 1× OUT + 1× IN (Authenticated Data Write) |

**Branch B: WRITE(10) — Boot LUN Write**

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | LUN1 (Boot LU) |
| LBA | Random |
| Transfer Length | Random(4K, 4M) blocks |

**Branch C: WRITE(10) — FUA Write**

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | LUN0 |
| LBA | Random |
| Transfer Length | Random(4K, 4M) blocks |
| FUA | 1 (Force Unit Access) |

**Branch Logic**（per JIRA）: 每次 Loop 迭代隨機選擇 Branch A、B 或 C 之一執行。

> - Branch A 使用 RPMB Protocol：SECURITY PROTOCOL OUT (B5h) 發送寫入請求，
>   SECURITY PROTOCOL IN (A2h) 接收結果。RPMB Authenticated Data Write 為
>   1× OUT + 1× IN 模式（非 Key Programming 的 2× OUT + 1× IN）。
> - Branch B 對 Boot LU (LUN1) 進行 Random Write。
> - Branch C 對 LUN0 進行 FUA Write。

**UFS SPEC Reference**:
- JESD220H Section 11.6 (RPMB / Security Protocol)
- JESD220H Section 10.7 (WRITE(10))
- JESD220H Section 10.2 (Well-Known LUNs / Boot LU)

---

## Phase 5 — Suspend 等待 + 電流測量

### Step 5.1: READ ATTRIBUTE — bBackgroundOpStatus (Poll until Idle)

**UFS QUERY**: `READ ATTRIBUTE (0x03)` — bBackgroundOpStatus (IDN 0x14)

**目的**: 輪詢 bBackgroundOpStatus 直到值為 0（Idle），
確保所有 Background Operation 已完成，裝置進入 Suspend 狀態。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| bAttrIDN | 0x14 (bBackgroundOpStatus) |
| Poll Condition | bBackgroundOpStatus == 0x00 (Idle) |
| Poll Mechanism | 重複 READ ATTRIBUTE 直到條件滿足 |

**UFS SPEC Reference**: JESD220H Section 10.7.8.4 (READ ATTRIBUTE), Section 14.3 (bBackgroundOpStatus)

---

### Step 5.2: 硬體量測 — Auto Standby 電流

**操作類型**：硬體量測（非 SCSI CMD / UFS Query）

**目的**: 在裝置進入 Auto Standby 狀態後，量測電流值，
供 Step 6.1 進行規格判定。

| Field | Value |
|-------|-------|
| 量測對象 | Auto Standby 狀態下的電流 |
| 量測方式 | 外部硬體儀器（非 SPEC 定義） |
| VCCQ 目標 | 待 Step 6.1 判定 |

> **注意**：此步驟為硬體量測操作，對應原始 JIRA Step 15「量測Auto standby後的電流」。
> 實際實作需搭配測試硬體（如電流計／SMU）進行。

---

## Phase 6 — 燒機後最終驗證

> **Phase 6 位於 24hr Loop 之外**，對應原始 JIRA Step 16~17。
> 在燒機完成後執行最終電流判定與 Smart Info 終值比對。

### Step 6.1: VCCQ 電流檢查

**操作類型**：測試判定（非 SCSI CMD / UFS Query）

**目的**: 檢查燒機期間量測的 VCCQ 電流是否在規範內。
若超過 2mA 則判定測試 Fail。

| Field | Value |
|-------|-------|
| 檢查對象 | VCCQ 電流 |
| 判定條件 | VCCQ ≤ 2mA |
| Fail 條件 | VCCQ > 2mA → 判定 Fail |

**Expected**: VCCQ 電流 ≤ 2mA。若超過則判定 Fail。

> **注意**：原始 JIRA 寫為「2mA1mA」，推測為 HTML rendering artifact，
> 應解讀為 2mA。實際判定值以 JIRA 或測試規範最終確認為準。

---

### Step 6.2: VU READ BUFFER — cache_not_data_trigger_suspend_cnt（最終比對）

**SCSI CMD**: `READ BUFFER (3Ch)` — Mode = Vendor Specific

**目的**: 燒機完成後讀取 cache_not_data_trigger_suspend_cnt 終值，
比對是否大於 Step 3.2 記錄的 Baseline 值（最後一次 Loop 迭代所記錄）。

| Field | Value |
|-------|-------|
| Opcode | 0x3C |
| Mode | VU (Vendor Specific) |
| 讀取目標 | cache_not_data_trigger_suspend_cnt (Smart Info counter) |
| LUN | LUN0 |

**Expected**: cache_not_data_trigger_suspend_cnt 計數值應大於 Step 3.2 記錄之 Baseline 值。

> **VU 細節**：同 Step 1.1，使用 READ BUFFER (3Ch) VU Mode。

**UFS SPEC Reference**: JESD220H Section 10.7 (READ BUFFER)

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x02 | SET FLAG | 啟用 fWriteBoosterBufferFlushDuringHibernate (Step 0.3) |
| 0x03 | READ ATTRIBUTE | 讀取 bBackgroundOpStatus 輪詢 (Step 5.1) |
| 0x05 | CLEAR FLAG | 關閉 fWriteBoosterEn、fWriteBoosterBufferFlushEn (Step 0.1~0.2) |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x0E | fWriteBoosterEn | Volatile (Set/Clear) | 關閉 WB 功能 (Step 0.1) |
| 0x0F | fWriteBoosterBufferFlushEn | Volatile (Set/Clear) | 關閉 WB Buffer Flush (Step 0.2) |
| 0x10 | fWriteBoosterBufferFlushDuringHibernate | Volatile (Set/Clear) | 啟用 Hibernate 期間 Flush (Step 0.3) |

### Attribute IDN

| IDN | 名稱 | Size | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|:---|
| 0x14 | bBackgroundOpStatus | 1 | Read-Only | 輪詢 BKOPS 狀態至 Idle (Step 5.1) |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x1B | START STOP UNIT | 6 | Hibernate Enter (Step 2.3) / Hibernate Exit (Step 2.5) |
| 0x28 | READ(10) | 10 | Random Read ×10 (Step 2.2) |
| 0x2A | WRITE(10) | 10 | Random Write ×10 (Step 2.1)、Boot LUN Write / FUA Write (Step 4.1 Branch) |
| 0x3C | READ BUFFER | 10 | VU Smart Info 讀取 (Step 1.1, 3.1, 3.2, 6.2) |
| 0xA2 | SECURITY PROTOCOL IN | 12 | RPMB Read Result (Step 4.1 Branch A) |
| 0xB5 | SECURITY PROTOCOL OUT | 12 | RPMB Write Request (Step 4.1 Branch A) |

---

## 附錄 C — UFS Power State 對照表

| START STOP UNIT | POWER CONDITION | START | 本 Pattern 用途 |
|:---|:---|:---|:---|
| Hibernate Enter | Hibernate | 0 | Step 2.3 |
| Hibernate Exit | Active | 1 | Step 2.5 |

**UFS SPEC Reference**: JESD220H Section 10.6 (Power Management)

---

## 自我驗證

- Tree Diagram leaf steps: **16**
  Phase 0: 3 (0.1~0.3), Phase 1: 1 (1.1), Phase 2: 5 (2.1~2.5), Phase 3: 2 (3.1~3.2), Phase 4: 1 (4.1), Phase 5: 2 (5.1~5.2), Phase 6: 2 (6.1~6.2) → Total: 16
- `### Step` sections: **16** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（共 5 個 Step：1.1, 3.1, 3.2, 6.1, 6.2）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
  - Step 1.1: JIRA Step 5「expect device response success」
  - Step 3.1: JIRA Step 11「expect 數值應大於 Step 5 數值」
  - Step 3.2: JIRA Step 12「expect device response success」
  - Step 6.1: JIRA Step 16「VCCQ電流不應超過2mA...若超過則判定Fail」
  - Step 6.2: JIRA Step 17「expect 數值應大於 Step 12 數值」
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
