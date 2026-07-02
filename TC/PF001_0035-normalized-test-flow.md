---
title: PF001_0035_BKOPS-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf001_0035, scsi-cmd, bkops, exception-event, event-alert]
description: >
  驗證 UFS 裝置在 URGENT_BKOPS 例外事件觸發時的狀態機行為：
  停用 fBackgroundOpsEn 後觸發 URGENT_BKOPS，檢查 bBackgroundOpStatus 與
  RESPONSE UPIU 中的 EVENT_ALERT 位元是否正確反映 BKOPS 狀態，
  最後恢復 fBackgroundOpsEn 並確認裝置回到 Idle。
sources:
  - JIRA: PF001_0035 (SYSTCUFS-51)
  - UFS Spec: JESD220H Section 10.7.8, 11.2.4.2, 14.2, 14.3
---

# PF001_0035 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置在 URGENT_BKOPS 例外事件觸發時的背景操作狀態機：
1. 裝置從 Idle 狀態開始，停用背景操作後透過寫入壓力觸發 URGENT_BKOPS
2. 驗證 URGENT_BKOPS 觸發時 bBackgroundOpStatus 狀態正確
3. 驗證 URGENT_BKOPS 觸發期間，任何 SCSI WRITE 的 RESPONSE UPIU 中 EVENT_ALERT 位元被設為 1
4. 恢復背景操作後確認裝置可正常完成 BKOPS 並回到 Idle

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | Keep polling URGENT_BKOPS(BIT2) in wExceptionEventStatus every 10 seconds until URGENT_BKOPS(BIT2) = 0 within 5 minutes | Step 0.1 |
| Step 2 | Disable fBackgroundOpsEn | Step 1.1 |
| Step 3 | Set wExceptionEventControl URGENT_BKOPS_EN(Bit2) = 1 | Step 1.2 |
| Step 4 | Erase purge write all | Step 1.3 ~ 1.5 |
| Step 5 | Issue Random Write until URGENT_BKOPS(BIT2) in wExceptionEventStatus is raised | Step 2.1 ~ 2.2 |
| Step 6 | Check if URGENT_BKOPS(BIT2) in wExceptionEventStatus is raised if not, return to step3 | Loop 回到 Step 1.2 |
| Step 7 | Read bBackgroundOpStatus while URGENT_BKOPS(BIT2) in wExceptionEventStatus is raised… | Step 3.1 |
| Step 8 | Issue normal write 4k | Step 4.1 |
| Step 9 | Read EVENT_ALERT bit in the Device Information field of the RESPONSE UPIU | Step 4.1（合併檢查） |
| Step 10 | Check if URGENT_BKOPS(BIT2) in wExceptionEventStatus is raised… expect EVENT_ALERT bit… is set to one | Step 4.2 |
| Step 11 | Enable fBackgroundOpsEn | Step 5.1 |
| Step 12 | polling bBackgroundOpStatus to 01h or 00h… | Step 5.2 |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF001_0035 Test Flow
│
├── Phase 0: Pre-condition — 確保裝置處於 Idle 狀態
│   └── Step 0.1: READ ATTRIBUTE (wExceptionEventStatus) — 輪詢確認 URGENT_BKOPS = 0
│
├── Phase 1: Configuration — 停用 BKOPS、啟用例外事件、清除裝置
│   ├── Step 1.1: CLEAR FLAG (fBackgroundOpsEn) — 停用背景操作
│   ├── Step 1.2: WRITE ATTRIBUTE (wExceptionEventControl) — 啟用 URGENT_BKOPS 例外事件通知
│   ├── Step 1.3: UNMAP — 清除所有 LUN 資料
│   ├── Step 1.4: SET FLAG (fPurgeEnable) — 觸發 Purge 安全清除
│   └── Step 1.5: READ ATTRIBUTE (bPurgeStatus) — 輪詢確認 Purge 完成
│
├── Loop (直到 URGENT_BKOPS 被觸發；若未觸發，回到 Step 1.2 重試)
│   └── Phase 2: Trigger URGENT_BKOPS — 隨機寫入觸發 BKOPS
│       ├── Step 2.1: WRITE(10) — 隨機寫入大量資料
│       └── Step 2.2: READ ATTRIBUTE (wExceptionEventStatus) — 檢查 URGENT_BKOPS 是否觸發
│
├── Phase 3: Verify BKOPS Status During URGENT_BKOPS
│   └── Step 3.1: READ ATTRIBUTE (bBackgroundOpStatus) — 讀取 BKOPS 狀態
│       Branch:
│       ├── bBackgroundOpStatus = 02h or 03h → Expected: PASS（BKOPS 正在執行）
│       ├── bBackgroundOpStatus = 00h or 01h, URGENT_BKOPS = 0 → Expected: PASS（BKOPS 已完成）
│       └── bBackgroundOpStatus = 00h or 01h, URGENT_BKOPS = 1 → Expected: FAIL
│
├── Phase 4: Verify EVENT_ALERT During URGENT_BKOPS
│   ├── Step 4.1: WRITE(10) — 寫入 4KB，檢查 RESPONSE UPIU 中的 EVENT_ALERT 位元
│   │   (若 URGENT_BKOPS raised → Expected: EVENT_ALERT = 1)
│   └── Step 4.2: READ ATTRIBUTE (wExceptionEventStatus) — 驗證 URGENT_BKOPS 與 EVENT_ALERT 一致性
│
└── Phase 5: Recovery — 恢復背景操作並等待回到 Idle
    ├── Step 5.1: SET FLAG (fBackgroundOpsEn) — 重新啟用背景操作
    └── Step 5.2: READ ATTRIBUTE (bBackgroundOpStatus) — 輪詢等待 BKOPS 回到 Idle
        Branch:
        ├── URGENT_BKOPS not raised → Expected: PASS
        ├── URGENT_BKOPS raised, bBackgroundOpStatus = 02h or 03h → Expected: PASS
        └── URGENT_BKOPS raised, bBackgroundOpStatus = 00h or 01h → Expected: FAIL
```

---

## Phase 0 — Pre-condition

### Step 0.1: 輪詢確認 URGENT_BKOPS = 0

**UFS QUERY**: `READ ATTRIBUTE (wExceptionEventStatus)`

**目的**: 確保測試開始前裝置未處於 URGENT_BKOPS 狀態，BKOPS 已在 5 分鐘內完成。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | 0x12 (wExceptionEventStatus) |
| Size | 2 bytes |
| Check | Bit 2 (URGENT_BKOPS) == 0 |
| Poll Interval | 10 seconds |
| Timeout | 5 minutes |

**UFS SPEC Reference**: JESD220H Section 14.3.1 — wExceptionEventStatus Attribute

---

## Phase 1 — Configuration

### Step 1.1: 停用背景操作

**UFS QUERY**: `CLEAR FLAG (fBackgroundOpsEn)`

**目的**: 停用背景操作，使 BKOPS 不會在背景自動執行，確保後續可手動觸發 URGENT_BKOPS。

| Field | Value |
|-------|-------|
| Query Opcode | 0x05 (CLEAR FLAG) |
| IDN | 0x03 (fBackgroundOpsEn) |
| Target Value | 0x00 |

**UFS SPEC Reference**: JESD220H Section 14.2.1 — fBackgroundOpsEn Flag

---

### Step 1.2: 啟用 URGENT_BKOPS 例外事件通知

**UFS QUERY**: `WRITE ATTRIBUTE (wExceptionEventControl)`

**目的**: 將 URGENT_BKOPS_EN (Bit 2) 設為 1，使裝置在 BKOPS 達緊急等級時透過 wExceptionEventStatus 回報。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x13 (wExceptionEventControl) |
| Size | 2 bytes |
| Value | Bit 2 (URGENT_BKOPS_EN) = 1；其餘位元保持原值 |

**UFS SPEC Reference**: JESD220H Section 14.3.1 — wExceptionEventControl Attribute

---

### Step 1.3: 清除所有 LUN 資料 (UNMAP)

**SCSI CMD**: `UNMAP (42h)`

**目的**: 清除裝置上所有已寫入的資料，為後續 Purge 做準備。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | 0x00 (或所有已配置 LUN) |
| UNMAP Block Descriptor Data Length | 依 LUN 容量計算 |
| UNMAP Block Descriptor | LBA = 0x0000000000000000, Logical Block Count = LUN 總容量 |

**UFS SPEC Reference**: JESD220H Section 12.2 (參照 SBC-4 UNMAP command)

---

### Step 1.4: 觸發 Purge 安全清除

**UFS QUERY**: `SET FLAG (fPurgeEnable)`

**目的**: 設定 fPurgeEnable 旗標，觸發裝置執行安全清除 (Purge)，將所有已 UNMAP 的區塊永久清除。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| IDN | 0x06 (fPurgeEnable) |
| Target Value | 0x01 |

**UFS SPEC Reference**: JESD220H Section 14.2.1 — fPurgeEnable Flag

---

### Step 1.5: 輪詢確認 Purge 完成

**UFS QUERY**: `READ ATTRIBUTE (bPurgeStatus)`

**目的**: 輪詢 Purge 狀態，確認安全清除作業已完成後才進入後續寫入測試。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | bPurgeStatus（待確認，請參照 JESD220H Section 14.3） |
| Size | 1 byte |
| Poll Condition | bPurgeStatus == 0x00（Purge 完成） |
| Poll Interval | 依實作定義 |

**UFS SPEC Reference**: JESD220H Section 14.3 — Purge Status Attribute

---

## Loop — 觸發 URGENT_BKOPS 迴圈

**迴圈邏輯**: 執行 Phase 2（Step 2.1 → Step 2.2）直到 URGENT_BKOPS 被觸發。若 URGENT_BKOPS 未觸發，回到 Step 1.2（重新啟用例外事件）→ Step 1.3（UNMAP）→ Step 1.4（Purge）→ Step 1.5（等 Purge 完成）→ 再次嘗試寫入。（對應 JIRA Step 6: "return to step3"）

## Phase 2 — Trigger URGENT_BKOPS

### Step 2.1: 隨機寫入大量資料

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 持續隨機寫入大量資料，使裝置 NAND 資源耗盡，觸發 URGENT_BKOPS 例外事件。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | Random (0x00000000 ~ LUN 最大 LBA) |
| Transfer Length | Variable（大量寫入，如 256KB ~ 1MB per command） |
| Data Pattern | Random / Pseudo-random |

**UFS SPEC Reference**: JESD220H Section 12.2 (參照 SBC-4 WRITE(10) command)

---

### Step 2.2: 檢查 URGENT_BKOPS 是否觸發

**UFS QUERY**: `READ ATTRIBUTE (wExceptionEventStatus)`

**目的**: 讀取例外事件狀態，檢查 URGENT_BKOPS (Bit 2) 是否已被裝置設為 1。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | 0x12 (wExceptionEventStatus) |
| Size | 2 bytes |
| Check | Bit 2 (URGENT_BKOPS) |

**UFS SPEC Reference**: JESD220H Section 14.3.1 — wExceptionEventStatus Attribute

---

## Phase 3 — Verify BKOPS Status During URGENT_BKOPS

### Step 3.1: 讀取 BKOPS 狀態

**UFS QUERY**: `READ ATTRIBUTE (bBackgroundOpStatus)`

**目的**: 在 URGENT_BKOPS 觸發後立即讀取 bBackgroundOpStatus，驗證背景操作狀態與例外事件的一致性。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | 0x14 (bBackgroundOpStatus) |
| Size | 1 byte |

**Branch Logic** (per JIRA Step 7):

| 條件 | 判定 | 說明 |
|:---|:---|:---|
| bBackgroundOpStatus == 0x02 (Performance Impact) or 0x03 (Critical) | **Expected: PASS** | BKOPS 正在執行中，與 URGENT_BKOPS 一致 |
| bBackgroundOpStatus == 0x00 (No BKOPS) or 0x01 (Not Critical)，且 URGENT_BKOPS == 0 | **Expected: PASS** | BKOPS 在檢查瞬間已完成（時序競合，FW 已處理完畢） |
| bBackgroundOpStatus == 0x00 (No BKOPS) or 0x01 (Not Critical)，且 URGENT_BKOPS == 1 | **Expected: FAIL** | 狀態矛盾：例外事件仍在但背景操作閒置 |

**UFS SPEC Reference**: JESD220H Section 14.3.1 — bBackgroundOpStatus Attribute

---

## Phase 4 — Verify EVENT_ALERT During URGENT_BKOPS

### Step 4.1: 寫入 4KB 並檢查 RESPONSE UPIU EVENT_ALERT

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 在 URGENT_BKOPS 觸發期間發送一個一般寫入命令，檢查裝置是否透過 RESPONSE UPIU 的 EVENT_ALERT 位元通知主機有擱置的例外事件。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 |
| LBA | 0x00000000（或任意有效 LBA） |
| Transfer Length | 8 (4KB = 8 sectors × 512B) |
| Data Pattern | 任意 |

**注意**: 此 Step 同時檢查 RESPONSE UPIU header byte 8 (Device Information) 的 EVENT_ALERT 位元 (Bit 2)。若此時 URGENT_BKOPS 仍觸發中，EVENT_ALERT 應被設為 1。此檢查對應 JIRA Step 8+9+10 的合併邏輯。

**UFS SPEC Reference**: JESD220H Section 11.2.4.2 — Response UPIU, Device Information Field

---

### Step 4.2: 驗證 URGENT_BKOPS 與 EVENT_ALERT 一致性

**UFS QUERY**: `READ ATTRIBUTE (wExceptionEventStatus)`

**目的**: 再次讀取 wExceptionEventStatus，與 Step 4.1 中 RESPONSE UPIU 的 EVENT_ALERT 位元交叉比對，確認例外事件狀態與 UPIU 通知一致。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | 0x12 (wExceptionEventStatus) |
| Size | 2 bytes |
| Check | Bit 2 (URGENT_BKOPS) |

**驗證邏輯** (per JIRA Step 10):
- 若 wExceptionEventStatus Bit 2 (URGENT_BKOPS) == 1，則 Step 4.1 的 RESPONSE UPIU EVENT_ALERT 位元必須為 1
- 若 URGENT_BKOPS == 0（BKOPS 已完成），EVENT_ALERT 可為 0 或 1

**UFS SPEC Reference**: JESD220H Section 14.3.1 — wExceptionEventStatus Attribute

---

## Phase 5 — Recovery

### Step 5.1: 重新啟用背景操作

**UFS QUERY**: `SET FLAG (fBackgroundOpsEn)`

**目的**: 恢復背景操作功能，讓裝置可正常排程與執行 BKOPS。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| IDN | 0x03 (fBackgroundOpsEn) |
| Target Value | 0x01 |

**UFS SPEC Reference**: JESD220H Section 14.2.1 — fBackgroundOpsEn Flag

---

### Step 5.2: 輪詢等待 BKOPS 回到 Idle

**UFS QUERY**: `READ ATTRIBUTE (bBackgroundOpStatus)`

**目的**: 在啟用背景操作後輪詢 bBackgroundOpStatus，確認裝置可正常完成剩餘的 BKOPS 並回到閒置狀態。同時檢查 URGENT_BKOPS 是否解除。

| Field | Value |
|-------|-------|
| Query Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | 0x14 (bBackgroundOpStatus) |
| Size | 1 byte |

**Branch Logic** (per JIRA Step 12):

| 條件 | 判定 | 說明 |
|:---|:---|:---|
| URGENT_BKOPS not raised | **Expected: PASS** | 背景操作完成且例外事件解除 |
| URGENT_BKOPS raised, bBackgroundOpStatus == 0x02 or 0x03 | **Expected: PASS** | BKOPS 仍在執行中（合理過渡狀態） |
| URGENT_BKOPS raised, bBackgroundOpStatus == 0x00 or 0x01 | **Expected: FAIL** | 狀態矛盾：例外事件存在但無背景操作 |

**UFS SPEC Reference**: JESD220H Section 14.3.1 — bBackgroundOpStatus Attribute

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x02 | SET FLAG | 設定 fPurgeEnable、設定 fBackgroundOpsEn |
| 0x03 | READ ATTRIBUTE | 讀取 wExceptionEventStatus、bBackgroundOpStatus、bPurgeStatus |
| 0x04 | WRITE ATTRIBUTE | 設定 wExceptionEventControl (URGENT_BKOPS_EN) |
| 0x05 | CLEAR FLAG | 清除 fBackgroundOpsEn |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x03 | fBackgroundOpsEn | Volatile (Set/Clear) | 停用/啟用背景操作 |
| 0x06 | fPurgeEnable | Volatile (Set only) | 觸發安全清除 (Purge) |

### Attribute IDN

| IDN | 名稱 | Size | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|:---|
| 0x12 | wExceptionEventStatus | 2 bytes | Read-Only | 輪詢 URGENT_BKOPS (Bit 2) 狀態 |
| 0x13 | wExceptionEventControl | 2 bytes | Read-Write | 設定 URGENT_BKOPS_EN (Bit 2) |
| 0x14 | bBackgroundOpStatus | 1 byte | Read-Only | 讀取 BKOPS 執行狀態 (00h/01h/02h/03h) |
| (待確認) | bPurgeStatus | 1 byte | Read-Only | 輪詢 Purge 完成狀態 |

### bBackgroundOpStatus 狀態值

| 值 | 名稱 | 說明 |
|:---|:---|:---|
| 0x00 | No BKOPS | 無需執行的背景操作 |
| 0x01 | Not Critical | 有背景操作但效能影響不大 |
| 0x02 | Performance Impact | 背景操作對效能有明顯影響 |
| 0x03 | Critical | 背景操作已達緊急等級（觸發 URGENT_BKOPS） |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x2A | WRITE(10) | 10 bytes | 隨機大量寫入觸發 BKOPS；小量寫入驗證 EVENT_ALERT |
| 0x42 | UNMAP | 10 bytes | 清除所有 LUN 資料，為 Purge 做準備 |

---

## 附錄 C — RESPONSE UPIU EVENT_ALERT 欄位說明

| 欄位 | 位置 | 位元 | 說明 |
|:---|:---|:---|:---|
| Device Information | RESPONSE UPIU Byte 8 | Bit 2 | EVENT_ALERT：裝置有擱置的例外事件需主機處理 |

**JESD220H Reference**: Section 11.2.4.2 — Response UPIU Format

---

## 自我驗證

- Tree Diagram leaf steps: **13**（Phase 0: 1 (0.1), Phase 1: 5 (1.1~1.5), Phase 2: 2 (2.1~2.2), Phase 3: 1 (3.1), Phase 4: 2 (4.1~4.2), Phase 5: 2 (5.1~5.2) → Total: 13）
- `### Step` sections: **13** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（共 3 個 leaf step 有 Expected：Step 3.1 / Step 5.2 來自 JIRA Step 7 及 Step 12 的 PASS/FAIL 判定；Step 4.1 因 JIRA Step 10 明確要求 EVENT_ALERT=1 而間接有預期）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
