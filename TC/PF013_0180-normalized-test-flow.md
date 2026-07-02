---
title: PF013_0180_Reliable_Normal_Write_All_Reset-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf013_0180, scsi-cmd, data-reliability, reset, fua]
description: >
  驗證 Data Reliability 類型 LU 與 Normal 類型 LU 在 FUA=1 寫入後，
  經由 6 種不同 Reset 模式（POR / SPOR / Sleep+Awake / Hibernate / Sleep+POR / Sleep+SPOR）
  後資料完整性（Read & Compare）。
sources:
  - JIRA: PF013_0180 (SYSTCUFS-12)
  - UFS Spec: JESD220H Section 10.2, 10.7, 11.3
---

# PF013_0180 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證在 Data Reliability 類型 LU 與 Normal 類型 LU 上以 FUA=1 進行寫入後，
經過多種 Reset 模式（Normal POR、SPOR、Sleep+Awake、Hibernate enter+exit、
Sleep+POR、Sleep+SPOR）後，資料能否正確讀回並比對一致。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | Config LUN into data_reliability type (FUA = 1) & normal type (FUA = 1) | Phase 0 (Step 0.1, 0.2) |
| Step 2 | Random normal write or reliability write operation (No Overlap) | Phase 1 (Step 1.1) |
| Step 3 | Random reset mode (Normal POR, SPOR, Sleep+Awake, Hibernate enter+exit, Sleep+POR, Sleep+SPOR) | Phase 2 (Step 2.1) |
| Step 4 | Read & Compare as expected | Phase 3 (Step 3.1) |
| Step 5 | Loop 2~4 [Detailed Test Steps] | Inner Loop |
| Step 6 | Config LUN into data_reliability type (FUA = 1) & normal type (FUA = 1) | Phase 0 (Step 0.1, 0.2) — 外層 Loop 第 2 次 |
| Step 7 | Random normal write or reliability write operation (No Overlap) | Phase 1 (Step 1.1) |
| Step 8 | Random reset mode (Normal POR, SPOR, Sleep+Awake, Hibernate enter+exit, Sleep+POR, Sleep+SPOR) | Phase 2 (Step 2.1) |
| Step 9 | Read & Compare as expected | Phase 3 (Step 3.1) |
| Step 10 | Loop 2~4 | Inner Loop（外層第 2 次） |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF013_0180 Test Flow
│
└── Loop（外層迴圈，2 次反覆，對應 JIRA Step 5 與 Step 10）
    │
    ├── Phase 0: LUN Configuration（JIRA Step 1 / Step 6）
    │   ├── Step 0.1: MODE SELECT(10) — Configure LU as Data Reliability Type (WCE=0)
    │   └── Step 0.2: MODE SELECT(10) — Configure LU as Normal Type (WCE=1)
    │
    └── Loop（內層迴圈，多次隨機反覆，對應 JIRA Step 5: Loop 2~4）
        ├── Phase 1: Random Write（No Overlap）（JIRA Step 2 / Step 7）
        │   └── Step 1.1: WRITE(10) — Random Write with FUA=1（隨機選 Reliability LU 或 Normal LU）
        │       ├── Case A: Write to Reliability LU (LBA Range A)
        │       └── Case B: Write to Normal LU (LBA Range B)
        │
        ├── Phase 2: Random Reset（JIRA Step 3 / Step 8）
        │   └── Step 2.1: Random Reset — 6 種 Reset 模式隨機選擇
        │       ├── Case 1: Normal POR
        │       ├── Case 2: SPOR
        │       ├── Case 3: Sleep + Awake
        │       ├── Case 4: Hibernate Enter + Exit
        │       ├── Case 5: Sleep + POR
        │       └── Case 6: Sleep + SPOR
        │
        └── Phase 3: Read & Compare（JIRA Step 4 / Step 9）
            └── Step 3.1: READ(10) — Read Back & Compare → Expected: GOOD Status, Data Match
```

---

## Phase 0 — LUN Configuration（JIRA Step 1 / Step 6）

### Step 0.1: Configure LU as Data Reliability Type (WCE=0)

**SCSI CMD**: `MODE SELECT(10) (0x55)`

**目的**: 將指定的 LU 設定為 Data Reliability 類型，關閉 Write Cache（WCE=0），
確保所有寫入（即使未設定 FUA）也強制寫入非揮發性記憶體。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x55 | MODE SELECT(10) |
| PF | 0 | Page Format = 0（current values） |
| SP | 1 | Save Pages = 1（儲存至 NVRAM，確保 Reset 後維持） |
| Parameter List Length | 0x14 | Mode Parameter Header (8B) + Page (12B) |
| LUN | Reliability LU | 指定為 Data Reliability 類型的 Logical Unit |
| Page Code | 0x08 | Caching Mode Page |
| SubPage Code | 0x00 | |
| Page Length | 0x12 | |
| WCE | 0 | Write Cache Enable = 0（Disable，Data Reliability） |
| RCD | 0 | Read Cache Disable = 0（Read Cache Enabled） |

**UFS SPEC Reference**: JESD220H Section 10.2 (SCSI Command Support), SBC-4 Caching Mode Page

---

### Step 0.2: Configure LU as Normal Type (WCE=1)

**SCSI CMD**: `MODE SELECT(10) (0x55)`

**目的**: 將指定的 LU 設定為 Normal 類型，啟用 Write Cache（WCE=1），
允許寫入先暫存於快取（但 FUA=1 的寫入仍會強制寫入非揮發性記憶體）。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x55 | MODE SELECT(10) |
| PF | 0 | Page Format = 0（current values） |
| SP | 1 | Save Pages = 1（儲存至 NVRAM，確保 Reset 後維持） |
| Parameter List Length | 0x14 | Mode Parameter Header (8B) + Page (12B) |
| LUN | Normal LU | 指定為 Normal 類型的 Logical Unit |
| Page Code | 0x08 | Caching Mode Page |
| SubPage Code | 0x00 | |
| Page Length | 0x12 | |
| WCE | 1 | Write Cache Enable = 1（Enable，Normal） |
| RCD | 0 | Read Cache Disable = 0（Read Cache Enabled） |

**UFS SPEC Reference**: JESD220H Section 10.2 (SCSI Command Support), SBC-4 Caching Mode Page

---

## Phase 1 — Random Write（JIRA Step 2 / Step 7）

### Step 1.1: Random Write with FUA=1（No Overlap）

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 以 FUA=1 對隨機選擇的 LU（Reliability 或 Normal）進行隨機 LBA 寫入，
兩 LU 的 LBA 範圍不重疊（No Overlap），確保後續比對時可明確辨別寫入對象。

**Branch Logic**（per JIRA random）:
- **Case A**: Write to Reliability LU — LBA Range A（e.g., LBA 0x0000 ~ LBA Range_A_End）
- **Case B**: Write to Normal LU — LBA Range B（e.g., LBA Range_A_End+1 ~ LBA Range_B_End）

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x2A | WRITE(10) |
| FUA | 1 | Force Unit Access — 強制寫入非揮發性記憶體 |
| LUN | Reliability LU or Normal LU | 隨機選擇 |
| LBA | Random（within target LU range） | 隨機 LBA，依 Case A/B 決定範圍 |
| Transfer Length | Random（依測試資料大小） | 每次隨機決定寫入長度 |
| Data | Random pattern | 隨機資料，需記錄以供後續比對 |

**UFS SPEC Reference**: JESD220H Section 10.2, SBC-4 WRITE(10) CDB

---

## Phase 2 — Random Reset（JIRA Step 3 / Step 8）

### Step 2.1: Execute Random Reset Mode

**操作類型**: UFS Device Reset（非單一 SCSI CMD）

**目的**: 在寫入完成後，從 6 種 Reset 模式中隨機選擇一種執行，
驗證不同層級的 Reset 後資料完整性。

**Branch Logic**（per JIRA random，6 種模式各等機率）:

#### Case 1: Normal POR（Power-On Reset）
以完整 power cycle 重置裝置。操作順序：
1. START STOP UNIT (0x1B) — POWER CONDITION=0x03（PowerDown），START=0
2. 等待電源關閉完成
3. 重新供電（VCC ON）
4. 裝置初始化完成（等待 fDeviceInit == 0）

#### Case 2: SPOR（Sudden Power-Off Recovery）
模擬非預期斷電後恢復。操作順序：
1. 直接切斷 VCC 電源（不經正常關機流程）
2. 等待放電完成
3. 重新供電（VCC ON）
4. 裝置執行 SPOR 流程後初始化完成（等待 fDeviceInit == 0）

#### Case 3: Sleep + Awake
進入 Sleep 模式後喚醒。操作順序：
1. START STOP UNIT (0x1B) — POWER CONDITION=0x02（Sleep），START=0
2. START STOP UNIT (0x1B) — POWER CONDITION=0x01（Active），START=1

#### Case 4: Hibernate Enter + Exit
進入 Hibernate 模式後退出。操作順序：
1. UFS Transport Protocol: HIBERNATE_ENTER
2. GPIO / REF_CLK 關閉（依 UFS 平台實作）
3. UFS Transport Protocol: HIBERNATE_EXIT
4. 等待裝置初始化完成（等待 fDeviceInit == 0）

#### Case 5: Sleep + POR
先進入 Sleep，再執行 POR。操作順序：
1. START STOP UNIT (0x1B) — POWER CONDITION=0x02（Sleep），START=0
2. 執行 Case 1 的 POR 流程（PowerDown → 重新供電 → 初始化）

#### Case 6: Sleep + SPOR
先進入 Sleep，再執行 SPOR。操作順序：
1. START STOP UNIT (0x1B) — POWER CONDITION=0x02（Sleep），START=0
2. 執行 Case 2 的 SPOR 流程（直接斷電 → 重新供電 → SPOR 恢復）

| 參數 | 值 | 說明 |
|-------|-------|------|
| 選擇方式 | Random（6 種等機率） | 每次內層迴圈隨機選一種 |
| 重置後驗證 | 等待 fDeviceInit == 0 | 確認裝置 Ready 後才進入 Phase 3 |

**UFS SPEC Reference**: JESD220H Section 10.7.2 (Power Management), 11.3 (Reset), 10.7.3 (Hibernate)

---

## Phase 3 — Read & Compare（JIRA Step 4 / Step 9）

### Step 3.1: Read Back & Data Compare

**SCSI CMD**: `READ(10) (0x28)`

**目的**: Reset 後讀回對應 LU 的 LBA 範圍，並與寫入時的隨機資料進行比對，
確認 Reset 未導致資料遺失或損毀。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x28 | READ(10) |
| LUN | 與 Step 1.1 相同 | 讀回寫入時選擇的 LU |
| LBA | 與 Step 1.1 相同 | 讀回寫入時的 LBA 位置 |
| Transfer Length | 與 Step 1.1 相同 | 讀回與寫入相同的長度 |

**Expected**: GOOD Status, Data Match（來自 JIRA Step 4 / Step 9：「Read & Compare as expected」）

**UFS SPEC Reference**: JESD220H Section 10.2, SBC-4 READ(10) CDB

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x01 | fDeviceInit | Read-Only | Reset 後檢查裝置初始化完成（Phase 2 各 Reset Case） |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x1B | START STOP UNIT | 6 | Sleep / PowerDown 電源狀態轉換（Phase 2） |
| 0x28 | READ(10) | 10 | Read Back & Compare（Phase 3） |
| 0x2A | WRITE(10) | 10 | Random Write FUA=1（Phase 1） |
| 0x55 | MODE SELECT(10) | 10 | LU Caching Mode 設定（Phase 0） |

---

## 附錄 C — 本 Pattern 使用的 UFS Reset 類型說明

| Reset 類型 | SPEC 章節 | 說明 | 本 Pattern Case |
|:---|:---|:---|:---|
| Normal POR | JESD220H 11.3.1 | 正常供電週期的 Power-On Reset | Case 1 |
| SPOR | JESD220H 11.3.2 | 非預期斷電後的 Sudden Power-Off Recovery | Case 2 |
| Sleep + Awake | JESD220H 10.7.2.1 | 進入 Sleep Power Condition 後返回 Active | Case 3 |
| Hibernate Enter + Exit | JESD220H 10.7.3 | UFS Hibernate 進入與退出 | Case 4 |
| Sleep + POR | JESD220H 10.7.2.1 + 11.3.1 | Sleep 後執行 POR | Case 5 |
| Sleep + SPOR | JESD220H 10.7.2.1 + 11.3.2 | Sleep 後執行 SPOR | Case 6 |

---

## 自我驗證

- Tree Diagram leaf steps: **5**（Phase 0: 2 (0.1, 0.2), Phase 1: 1 (1.1), Phase 2: 1 (2.1), Phase 3: 1 (3.1) → Total: 5）
- `### Step` sections: **5** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（1 個 step 有 Expected: Step 3.1）
- 有 Expected 的 step 均來源於 JIRA 原文：Step 3.1 `→ Expected: GOOD Status, Data Match` ← JIRA Step 4/Step 9「Read & Compare as expected」✓
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
