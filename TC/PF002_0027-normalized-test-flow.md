---
title: PF002_0027-Boot-Process-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_0027, scsi-cmd, boot-lun, bBootLunEn]
description: >
  驗證 UFS 裝置的 Boot Logical Unit 配置與資料完整性。測試流程包含：
  關閉 Boot 功能後寫入測試資料至普通 LUN，接著分別配置 Boot LU A / Boot LU B
  並透過 Reset 觸發 LUN 角色切換，再讀回 Boot Data 驗證資料一致性與
  bBootLunEn 屬性值正確性。最後測試無效 bBootLunEn 值與寫入 Boot LUN 的
  負向行為（錯誤回應碼與 SENSE KEY）。整個流程執行兩輪以驗證重複配置的穩定性。
sources:
  - JIRA: PF002_0027 (SYSTCUFS-160)
  - UFS Spec: JESD220H Section 11.1 (Boot Logical Units), Section 14.3 (Attributes)
---

# PF002_0027 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 Boot Logical Unit 的完整生命週期：關閉 Boot → 寫入測試資料 → 配置 Boot LU A → Reset → 驗證 Boot Data 與 bBootLunEn → 配置 Boot LU B → Reset → 驗證 → 再執行無效值寫入與 Boot LUN 寫入保護的負向測試。整個流程重複兩輪，確保 Boot LUN 配置在多次切換後仍維持資料完整性與正確的錯誤行為。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | Set bBootLunEn = 00h (disable boot) | Step 1.1 |
| Step 2 | Write data to normal LUN, and then read data after the lun is transfer to Boot LU A/B | Step 1.2（Write）、Steps 2.3, 3.3（Read） |
| Step 3 | Set bBootLunEn = 01h (Boot LU A) → Reset → Read Boot Data → Read bBootLunEn Attribute | Steps 2.1, 2.2, 2.3, 2.4 |
| Step 4 | Compare boot data and bBootLunEn Attribute is correct | Step 2.3 Expected + Step 2.4 Expected |
| Step 5 | Set bBootLunEn = 02h (Boot LU B) → Reset → Read Boot Data → Read bBootLunEn Attribute | Steps 3.1, 3.2, 3.3, 3.4 |
| Step 6 | Compare boot data and bBootLunEn Attribute is correct | Step 3.3 Expected + Step 3.4 Expected |
| Step 7 | Send QUERY REQUEST write attribute - bBootLunEn with invalid value, the query response shall be FAh(Invalid value) | Step 4.1 |
| Step 8 | Set bBootLunEn = 01h (Boot LU A) and Write data to Well-known Boot LUN then response shall fail and sense key=05h(ILLEGAL REQUEST) | Steps 4.2, 4.3 |
| Step 9 | Set bBootLunEn = 00h (disable boot) — second pass | Loop Iteration 2 → Step 1.1 |
| Steps 10–16 | Repeat of Steps 2–8 | Loop Iteration 2 → Steps 1.2–4.3 |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF002_0027 Test Flow
│
└── Loop (2 iterations)
    │
    ├── Phase 1: Initialization & Write Test Data
    │   ├── Step 1.1: WRITE ATTRIBUTE(bBootLunEn = 00h) — 關閉 Boot 功能
    │   └── Step 1.2: WRITE(10) — 寫入測試資料至普通 LUN
    │
    ├── Phase 2: Boot LU A Configuration & Data Verification
    │   ├── Step 2.1: WRITE ATTRIBUTE(bBootLunEn = 01h) — 配置 Boot LU A
    │   ├── Step 2.2: HW_RESET — 觸發 LUN 角色切換 → Expected: Reset device success
    │   ├── Step 2.3: READ(10) — 讀取 Boot LU A 的 Boot Data → Expected: GOOD Status, Data Match
    │   └── Step 2.4: READ ATTRIBUTE(bBootLunEn) — 驗證 bBootLunEn 值 → Expected: QUERY RESPONSE Success, bBootLunEn == 0x01
    │
    ├── Phase 3: Boot LU B Configuration & Data Verification
    │   ├── Step 3.1: WRITE ATTRIBUTE(bBootLunEn = 02h) — 配置 Boot LU B
    │   ├── Step 3.2: HW_RESET — 觸發 LUN 角色切換 → Expected: Reset device success
    │   ├── Step 3.3: READ(10) — 讀取 Boot LU B 的 Boot Data → Expected: GOOD Status, Data Match
    │   └── Step 3.4: READ ATTRIBUTE(bBootLunEn) — 驗證 bBootLunEn 值 → Expected: QUERY RESPONSE Success, bBootLunEn == 0x02
    │
    └── Phase 4: Error Handling & Negative Tests
        ├── Step 4.1: WRITE ATTRIBUTE(bBootLunEn = invalid) — 寫入無效值 → Expected: QUERY RESPONSE Code 0xFA (Invalid value)
        ├── Step 4.2: WRITE ATTRIBUTE(bBootLunEn = 01h) — 配置 Boot LU A（準備負向測試）
        └── Step 4.3: WRITE(10) to Boot LUN — 寫入 Boot LUN 應被拒絕 → Expected: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h)
```

**Expected 格式說明：**
- Reset: `→ Expected: Reset device success`
- Read Compare: `→ Expected: GOOD Status, Data Match`
- Query Response: `→ Expected: QUERY RESPONSE Success, bBootLunEn == 0xNN`
- Error Response: `→ Expected: QUERY RESPONSE Code 0xFA (Invalid value)`
- SCSI Error: `→ Expected: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h)`

---

## Phase 1 — Initialization & Write Test Data

### Step 1.1: 關閉 Boot 功能

**UFS QUERY**: `WRITE ATTRIBUTE (bBootLunEn)`

**目的**: 將 bBootLunEn 設為 00h 以關閉 Boot Logical Unit 功能，確保後續 LUN 以普通模式運作。

| Field | Value |
|-------|-------|
| Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |
| Value | 0x00 (Disable Boot) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.5 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn Attribute, IDN 0x00)

---

### Step 1.2: 寫入測試資料至普通 LUN

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 將已知的測試 Pattern 資料寫入普通 LUN，作為後續 Boot LUN 切換後驗證資料完整性的基準。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | Normal LUN |
| LBA | 0x00000000 |
| Transfer Length | 測試 Pattern 大小（依測試需求） |
| Data | 已知測試 Pattern |

**UFS SPEC Reference**: JESD220H Section 10.9.4 (WRITE(10))

---

## Phase 2 — Boot LU A Configuration & Data Verification

### Step 2.1: 配置 Boot LU A

**UFS QUERY**: `WRITE ATTRIBUTE (bBootLunEn)`

**目的**: 將 bBootLunEn 設為 01h 以啟用 Boot LU A，使普通 LUN 在 Reset 後轉換為 Boot Logical Unit A。

| Field | Value |
|-------|-------|
| Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |
| Value | 0x01 (Boot LU A Enabled) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.5 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn), Section 11.1 (Boot Logical Units)

---

### Step 2.2: 執行 Hardware Reset

**UFS OPERATION**: `HW_RESET`

**目的**: 觸發 Hardware Reset（或 EndPoint Reset / UniPro Reset）使 UFS 裝置重新初始化，LUN 依據 bBootLunEn 配置切換為 Boot LU A。

| Field | Value |
|-------|-------|
| Reset Type | HW_RESET / EndPoint Reset / UniPro Reset |
| Post-Reset | 等待 fDeviceInit Flag 為 1（裝置初始化完成） |

**Expected**: Reset device success。

**UFS SPEC Reference**: JESD220H Section 10.7.1 (Reset), Section 11.1 (Boot Logical Units)

---

### Step 2.3: 讀取 Boot LU A 的 Boot Data

**SCSI CMD**: `READ(10) (28h)`

**目的**: 從已切換為 Boot LU A 的 LUN 讀取 Boot Data，並與 Step 1.2 寫入的測試 Pattern 進行比對，驗證 LUN 角色切換後資料完整性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LU A (原普通 LUN) |
| LBA | 0x00000000 |
| Transfer Length | 等同 Step 1.2 寫入大小 |

**Expected**: GOOD Status, Data Match（讀取資料與 Step 1.2 寫入的測試 Pattern 完全一致）。

**UFS SPEC Reference**: JESD220H Section 10.9.4 (READ(10)), Section 11.1 (Boot Logical Units)

---

### Step 2.4: 讀取並驗證 bBootLunEn 屬性值

**UFS QUERY**: `READ ATTRIBUTE (bBootLunEn)`

**目的**: 讀取 bBootLunEn 屬性，確認 Reset 後其值仍為 0x01（Boot LU A Enabled）。

| Field | Value |
|-------|-------|
| Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |

**Expected**: QUERY RESPONSE Success，bBootLunEn == 0x01。

**UFS SPEC Reference**: JESD220H Section 10.7.8.3 (READ ATTRIBUTE), Section 14.3 (bBootLunEn)

---

## Phase 3 — Boot LU B Configuration & Data Verification

### Step 3.1: 配置 Boot LU B

**UFS QUERY**: `WRITE ATTRIBUTE (bBootLunEn)`

**目的**: 將 bBootLunEn 設為 02h 以啟用 Boot LU B，準備將 LUN 切換為 Boot Logical Unit B。

| Field | Value |
|-------|-------|
| Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |
| Value | 0x02 (Boot LU B Enabled) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.5 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn), Section 11.1 (Boot Logical Units)

---

### Step 3.2: 執行 Hardware Reset

**UFS OPERATION**: `HW_RESET`

**目的**: 觸發 Reset 使 LUN 依據新的 bBootLunEn 配置切換為 Boot LU B。

| Field | Value |
|-------|-------|
| Reset Type | HW_RESET / EndPoint Reset / UniPro Reset |
| Post-Reset | 等待 fDeviceInit Flag 為 1 |

**Expected**: Reset device success。

**UFS SPEC Reference**: JESD220H Section 10.7.1 (Reset), Section 11.1 (Boot Logical Units)

---

### Step 3.3: 讀取 Boot LU B 的 Boot Data

**SCSI CMD**: `READ(10) (28h)`

**目的**: 從已切換為 Boot LU B 的 LUN 讀取 Boot Data，與 Step 1.2 寫入的測試 Pattern 比對，驗證切換至 Boot LU B 後資料仍完整。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot LU B (原普通 LUN) |
| LBA | 0x00000000 |
| Transfer Length | 等同 Step 1.2 寫入大小 |

**Expected**: GOOD Status, Data Match（讀取資料與 Step 1.2 寫入的測試 Pattern 完全一致）。

**UFS SPEC Reference**: JESD220H Section 10.9.4 (READ(10)), Section 11.1 (Boot Logical Units)

---

### Step 3.4: 讀取並驗證 bBootLunEn 屬性值

**UFS QUERY**: `READ ATTRIBUTE (bBootLunEn)`

**目的**: 讀取 bBootLunEn 屬性，確認 Reset 後其值仍為 0x02（Boot LU B Enabled）。

| Field | Value |
|-------|-------|
| Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |

**Expected**: QUERY RESPONSE Success，bBootLunEn == 0x02。

**UFS SPEC Reference**: JESD220H Section 10.7.8.3 (READ ATTRIBUTE), Section 14.3 (bBootLunEn)

---

## Phase 4 — Error Handling & Negative Tests

### Step 4.1: 寫入無效 bBootLunEn 值

**UFS QUERY**: `WRITE ATTRIBUTE (bBootLunEn, Invalid Value)`

**目的**: 對 bBootLunEn 寫入無效值，驗證 UFS 裝置正確回傳錯誤碼 0xFA（Invalid value）。

| Field | Value |
|-------|-------|
| Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |
| Value | Invalid（非 0x00 / 0x01 / 0x02 之任意值，例如 0xFF） |

**Expected**: QUERY RESPONSE Code 0xFA (Invalid value)。

**UFS SPEC Reference**: JESD220H Section 10.7.8.5 (WRITE ATTRIBUTE), Section 10.7.10 (QUERY RESPONSE Codes), Section 14.3 (bBootLunEn — 有效值僅 00h/01h/02h)

---

### Step 4.2: 配置 Boot LU A（準備負向寫入測試）

**UFS QUERY**: `WRITE ATTRIBUTE (bBootLunEn)`

**目的**: 將 bBootLunEn 設回 01h（Boot LU A），使 LUN 處於 Boot 模式，以測試對 Boot LUN 寫入的保護機制。

| Field | Value |
|-------|-------|
| Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |
| Value | 0x01 (Boot LU A Enabled) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.5 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn), Section 11.1 (Boot Logical Units)

---

### Step 4.3: 對 Boot LUN 執行 WRITE（應被拒絕）

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 在 Boot LUN 啟用狀態下，對 Well-known Boot Logical Unit 執行 WRITE 操作，驗證裝置正確拒絕寫入並回傳 CHECK_CONDITION 狀態，SENSE KEY 為 ILLEGAL REQUEST (05h)。這是 Boot LUN 的寫入保護機制驗證。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | Boot LU A (Well-known Boot LUN) |
| LBA | 0x00000000 |
| Transfer Length | 任意大小（例如 1 block） |
| Data | 任意測試資料 |

**Expected**: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h)。

**UFS SPEC Reference**: JESD220H Section 10.9.4 (WRITE(10)), Section 10.10.2 (SENSE KEY), Section 11.1 (Boot Logical Units — Boot LUN 資料區域為唯讀)

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x03 | READ ATTRIBUTE | 讀取 bBootLunEn 屬性值以驗證配置正確性（Steps 2.4, 3.4） |
| 0x04 | WRITE ATTRIBUTE | 寫入 bBootLunEn 屬性以設定 Boot 模式與無效值測試（Steps 1.1, 2.1, 3.1, 4.1, 4.2） |

### Attribute IDN

| IDN | 名稱 | Size | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|:---|
| 0x00 | bBootLunEn | 1 byte | Read-Write | 控制 Boot Logical Unit 的啟用狀態：00h=Disable, 01h=Boot LU A, 02h=Boot LU B |

### QUERY RESPONSE Codes

| Code | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0xFA | Invalid value | Step 4.1：寫入無效 bBootLunEn 值時的回應碼 |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB Size | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 bytes | 從 Boot LU A / Boot LU B 讀取 Boot Data，驗證資料完整性（Steps 2.3, 3.3） |
| 0x2A | WRITE(10) | 10 bytes | 寫入測試資料至普通 LUN（Step 1.2）；嘗試對 Boot LUN 寫入以觸發錯誤（Step 4.3） |

### SENSE KEY

| Value | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 05h | ILLEGAL REQUEST | Step 4.3：對 Boot LUN 寫入時的回應 SENSE KEY |

---

## 附錄 C — UFS Reset 類型說明

| Reset 類型 | 說明 | SPEC Reference | 本 Pattern 用途 |
|:---|:---|:---|:---|
| HW_RESET | Hardware Reset — 透過硬體訊號重置 UFS 裝置 | JESD220H Section 10.7.1 | Steps 2.2, 3.2：觸發 LUN 角色切換為 Boot LU |
| EndPoint Reset | 透過 UniPro EndPoint 重置 | JESD220H Section 10.7.1 | Steps 2.2, 3.2（可替代 HW_RESET） |
| UniPro Reset | 重置 UniPro 鏈路 | JESD220H Section 10.7.1 | Steps 2.2, 3.2（可替代 HW_RESET） |

> **備註**：JIRA 原文指定三種 Reset 型態（HW-Reset / End-Point-Reset / UniPro Reset）任選其一執行即可。

---

## 自我驗證

- Tree Diagram leaf steps: **13**（Phase 1: 2 (1.1~1.2), Phase 2: 4 (2.1~2.4), Phase 3: 4 (3.1~3.4), Phase 4: 3 (4.1~4.3) → Total: 13）
- `### Step` sections: **13** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（共 8 個 Expected：Step 2.2 Reset 預期、Step 2.3 Data Match、Step 2.4 bBootLunEn==0x01、Step 3.2 Reset 預期、Step 3.3 Data Match、Step 3.4 bBootLunEn==0x02、Step 4.1 QUERY RESPONSE 0xFA、Step 4.3 CHECK_CONDITION ILLEGAL_REQUEST）
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
  - Step 2.2 / 3.2: Reset device success ← 使用者明確指定 Reset step 統一格式
  - Step 2.3 / 3.3: GOOD Status, Data Match ← JIRA Step 4/6 "Compare boot data ... is correct"
  - Step 2.4 / 3.4: QUERY RESPONSE Success, bBootLunEn == 0x01/0x02 ← JIRA Step 4/6 "Compare bBootLunEn Attribute is correct"
  - Step 4.1: QUERY RESPONSE Code 0xFA ← JIRA Step 7 "the query response shall be FAh(Invalid value)"
  - Step 4.3: CHECK_CONDITION, SENSE_KEY=ILLEGAL_REQUEST(05h) ← JIRA Step 8 "response shall fail and sense key=05h(ILLEGAL REQUEST)"
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
