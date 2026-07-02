---
title: PF002_1745_D_Boot_Data_Cmp_With_Init_Done-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_1745, scsi-cmd, boot, spor, hw-reset, device-init]
description: >
  驗證 Boot Data 在 SPOR + HW Reset 後、Device Init 前後（設定 fDeviceInit 前後）
  的資料完整性比對。透過 DCMD7 嘗試觸發 SPOR、寫入 Boot LUN 資料、HW Reset +
  Link Startup 後讀取比較（Pre-Init）、再設定 fDeviceInit 後讀取比較（Post-Init），
  最後確認 Normal LUN 仍可正常回應。以 3 小時 Loop 執行壓力驗證。
sources:
  - JIRA: PF002_1745 (SYSTCUFS-2024)
  - UFS Spec: JESD220H Section 7.3, 10.7.2, 10.7.8, 10.11, 10.13.3, 12.2, 14.2
---

# PF002_1745 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證在 SPOR（Sudden Power Off Recovery）與 HW Reset 發生後，Boot LUN 上的資料
在 Device Init（fDeviceInit Flag 被設定）前後是否均能正確保留並讀出比對成功。
測試以 3 小時 Loop 方式持續驗證資料完整性與裝置穩定性。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 0 | Precondition: Host issue set boot lunA | Phase 0 Step 0.1 |
| Step 1 | Write all full card on normal lun | Phase 0 Step 0.2 |
| Step 2 | dcmd7 to trigger SPOR (rsp_detect_cnt = random 1~8) | Phase 1 Step 1.1 |
| Step 3 | Random write on boot A, FUA=1, start LBA=0, chunk 512KB, total=boot lun capacity | Phase 1 Step 1.2 |
| Step 4 | HW reset + link startup + NOP OUT + TUR on Boot lun | Phase 2 Step 2.1~2.4 |
| Step 5 | Read boot data (start LBA=0, chunk 512KB, total=boot lun capacity) + read compare pass | Phase 2 Step 2.5 |
| Step 6 | Set init flag + poll until init flow finished | Phase 3 Step 3.1~3.2 |
| Step 7 | Read boot data (start LBA=0, chunk 512KB, total=boot lun capacity) | Phase 3 Step 3.3 |
| Step 8 | Read compare data pass | Phase 3 Step 3.3（合併為比對驗證） |
| Step 9 | TEST UNIT READY on normal lun | Phase 4 Step 4.1 |
| Step 10 | Loop step2~step9 3HRs | Loop 結構 |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF002_1745 Test Flow
│
├── Phase 0: Pre-condition — Boot LUN 設定與初始寫入
│   ├── Step 0.1: WRITE ATTRIBUTE (bBootLunEn) — 啟用 Boot LUN
│   └── Step 0.2: WRITE(10) — 對 Normal LUN 寫滿整張卡（Burn-in Pre-condition）
│
└── Loop（3 小時）
    │
    ├── Phase 1: SPOR 觸發與 Boot Data 寫入
    │   ├── Step 1.1: DCMD7 — 觸發 SPOR 偵測（rsp_detect_cnt = random 1~8）
    │   └── Step 1.2: WRITE(10) FUA=1 — 對 Boot WLUN 寫入測試資料（LBA=0, chunk=512KB, total=boot capacity）
    │
    ├── Phase 2: 裝置重置與 Pre-Init Boot Data 比對
    │   ├── Step 2.1: HW Reset — 硬體重置 → Expected: Reset device success
    │   ├── Step 2.2: Link Startup — M-PHY / UniPro 鏈路初始化 → Expected: Reset device success
    │   ├── Step 2.3: NOP OUT — 確認 UFS 鏈路正常
    │   ├── Step 2.4: TEST UNIT READY — Boot WLUN 就緒檢查
    │   └── Step 2.5: READ(10) + Compare — 讀取 Boot Data 並比對 → Expected: GOOD Status, Data Match
    │
    ├── Phase 3: Device Init 與 Post-Init Boot Data 比對
    │   ├── Step 3.1: SET FLAG (fDeviceInit) — 觸發裝置初始化流程
    │   ├── Step 3.2: READ FLAG (fDeviceInit) — 輪詢等待初始化完成 → Expected: fDeviceInit == 0
    │   └── Step 3.3: READ(10) + Compare — 讀取 Boot Data 並比對 → Expected: GOOD Status, Data Match
    │
    └── Phase 4: Normal LUN 就緒驗證
        └── Step 4.1: TEST UNIT READY — Normal LUN 就緒檢查
```

---

## Phase 0 — Pre-condition：Boot LUN 設定與初始寫入

### Step 0.1: 啟用 Boot LUN（Set Boot LUN A）

**UFS QUERY**: `WRITE ATTRIBUTE (bBootLunEn)`

**目的**: 設定 Boot LUN 為啟用狀態，使後續 Boot WLUN 可被存取。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x00 (bBootLunEn) |
| Index | 0x00 |
| Selector | 0x00 |
| Value | 0x01 (Enable) |

**UFS SPEC Reference**: JESD220H Section 10.7.8.4, 14.3

---

### Step 0.2: 對 Normal LUN 寫滿整張卡（Burn-in Pre-condition）

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對 Normal LUN 執行全碟寫入（Burn-in Pre-condition），建立裝置初始磨損狀態後再進入主測試 Loop。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0x00 (Normal LUN) |
| LBA | 0x00000000 |
| Transfer Length | N blocks（總容量；chunk = 512KB / 128 blocks） |
| FUA | 0 |
| Control | 0x00 |

**UFS SPEC Reference**: JESD220H Section 10.11

---

## Phase 1 — SPOR 觸發與 Boot Data 寫入

### Step 1.1: 透過 DCMD7 觸發 SPOR 偵測

**Device Operation**: DCMD7（DME Command）SPOR Trigger

**目的**: 嘗試透過 DME DCMD7 觸發裝置 SPOR（Sudden Power Off Recovery）機制。
SPOR 偵測次數為亂數 1~8 次。

| Field | Value |
|-------|-------|
| Operation | DCMD7 (DME Command) |
| SPOR Detect Type | DCMD7_RSP_DETECT |
| rsp_detect_cnt | random(1, 8) |

> **附註**: DCMD7 為 UFS DME 層操作，非標準 SCSI CMD 亦非 UFS Query。
> 此步驟僅嘗試觸發 SPOR，不保證實際觸發（JIRA: "No matter whether device has triggered or not"）。

**UFS SPEC Reference**: JESD220H Section 12.2 (DME)

---

### Step 1.2: 對 Boot WLUN 寫入測試資料（FUA=1）

**SCSI CMD**: `WRITE(10) (2Ah)` — FUA=1

**目的**: 在 SPOR 觸發嘗試後，對 Boot WLUN 寫入已知測試資料，作為後續 Pre-Init 與 Post-Init 讀取比對的基準資料。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | 0xB0 (Boot WLUN, Boot LUN A) |
| LBA | 0x00000000 |
| Transfer Length | Variable（chunk size = 512KB / 128 blocks per chunk；total = Boot LUN capacity） |
| FUA | 1（Force Unit Access） |
| RDPROTECT | 0x00 |
| Control | 0x00 |

**UFS SPEC Reference**: JESD220H Section 10.11

---

## Phase 2 — 裝置重置與 Pre-Init Boot Data 比對

### Step 2.1: HW Reset（硬體重置）

**Device Operation**: Hardware Reset

**目的**: 對 UFS 裝置執行硬體重置（HW Reset），無論 SPOR 是否觸發成功都執行，
使裝置回到已知初始狀態。

| Field | Value |
|-------|-------|
| Reset Type | HW Reset（Hardware Reset） |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 7.3

---

### Step 2.2: Link Startup（鏈路初始化）

**Device Operation**: M-PHY / UniPro Link Startup

**目的**: 在 HW Reset 後重新啟動 M-PHY 與 UniPro 鏈路，建立 Host 與 Device 之間的通訊。

| Field | Value |
|-------|-------|
| Operation | Link Startup（M-PHY + UniPro） |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 6 (M-PHY), Section 7 (UniPro)

---

### Step 2.3: NOP OUT（確認鏈路正常）

**UFS UPIU**: `NOP OUT`

**目的**: 發送 NOP OUT UPIU 以確認 UFS 鏈路已正常建立、雙向通訊無誤。

| Field | Value |
|-------|-------|
| UPIU Transaction Type | NOP OUT |
| Flags | 0x00 |
| Task Tag | 0x00 |

**UFS SPEC Reference**: JESD220H Section 10.7.2

---

### Step 2.4: Boot WLUN 就緒檢查

**SCSI CMD**: `TEST UNIT READY (00h)`

**目的**: 對 Boot WLUN 發出 TEST UNIT READY，確認 Boot LUN 處於可操作狀態。

| Field | Value |
|-------|-------|
| Opcode | 0x00 |
| LUN | 0xB0 (Boot WLUN) |

**UFS SPEC Reference**: JESD220H Section 10.11

---

### Step 2.5: Pre-Init Boot Data 讀取與比對

**SCSI CMD**: `READ(10) (28h)` + Host-side Data Compare

**目的**: 在 Device Init（fDeviceInit）尚未設定的情況下，讀取 Boot WLUN 上的資料
並與 Step 1.2 寫入的資料比對，驗證 Reset 後資料完整性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0xB0 (Boot WLUN) |
| LBA | 0x00000000 |
| Transfer Length | Variable（chunk size = 512KB / 128 blocks per chunk；total = Boot LUN capacity） |
| RDPROTECT | 0x00 |
| Control | 0x00 |

**Expected**: GOOD Status, Data Match（讀取資料與寫入資料完全一致）

**UFS SPEC Reference**: JESD220H Section 10.11

---

## Phase 3 — Device Init 與 Post-Init Boot Data 比對

### Step 3.1: 觸發裝置初始化流程（Set fDeviceInit）

**UFS QUERY**: `SET FLAG (fDeviceInit)`

**目的**: 設定 fDeviceInit Flag 以觸發 UFS 裝置初始化流程。

| Field | Value |
|-------|-------|
| Query Opcode | 0x02 (SET FLAG) |
| IDN | 0x01 (fDeviceInit) |
| Index | 0x00 |
| Selector | 0x00 |

**UFS SPEC Reference**: JESD220H Section 10.7.8.2, 14.2

---

### Step 3.2: 輪詢等待初始化完成（Poll fDeviceInit）

**UFS QUERY**: `READ FLAG (fDeviceInit)`

**目的**: 輪詢讀取 fDeviceInit Flag，等待裝置初始化流程完成（fDeviceInit == 0）。

| Field | Value |
|-------|-------|
| Query Opcode | 0x01 (READ FLAG) |
| IDN | 0x01 (fDeviceInit) |
| Index | 0x00 |
| Selector | 0x00 |

**Expected**: fDeviceInit == 0（裝置初始化完成）

**UFS SPEC Reference**: JESD220H Section 10.7.8.1, 14.2

---

### Step 3.3: Post-Init Boot Data 讀取與比對

**SCSI CMD**: `READ(10) (28h)` + Host-side Data Compare

**目的**: 在 Device Init 完成後（fDeviceInit == 0），再次讀取 Boot WLUN 上的資料
並與 Step 1.2 寫入的資料比對，驗證 Init 過程中資料未被破壞。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 0xB0 (Boot WLUN) |
| LBA | 0x00000000 |
| Transfer Length | Variable（chunk size = 512KB / 128 blocks per chunk；total = Boot LUN capacity） |
| RDPROTECT | 0x00 |
| Control | 0x00 |

**Expected**: GOOD Status, Data Match（讀取資料與寫入資料完全一致）

**UFS SPEC Reference**: JESD220H Section 10.11

---

## Phase 4 — Normal LUN 就緒驗證

### Step 4.1: Normal LUN 就緒檢查

**SCSI CMD**: `TEST UNIT READY (00h)`

**目的**: 對 Normal LUN 發出 TEST UNIT READY，確認 Normal LUN 在整個 Boot + Init 流程後仍能正常回應。

| Field | Value |
|-------|-------|
| Opcode | 0x00 |
| LUN | 0x00 (Normal LUN) |

**UFS SPEC Reference**: JESD220H Section 10.11

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x01 | READ FLAG | Step 3.2：輪詢 fDeviceInit 等待初始化完成 |
| 0x02 | SET FLAG | Step 3.1：設定 fDeviceInit 觸發初始化 |
| 0x04 | WRITE ATTRIBUTE | Step 0.1：設定 bBootLunEn 啟用 Boot LUN |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x01 | fDeviceInit | No（Non-Volatile） | Step 3.1 / 3.2：設定並輪詢裝置初始化完成 |

### Attribute IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x00 | bBootLunEn | Read-Write | Step 0.1：啟用 Boot LUN |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x00 | TEST UNIT READY | 6 | Step 2.4 / 4.1：Boot WLUN 與 Normal LUN 就緒檢查 |
| 0x28 | READ(10) | 10 | Step 2.5 / 3.3：Boot Data 讀取與比對 |
| 0x2A | WRITE(10) | 10 | Step 0.2：Normal LUN 全碟寫入；Step 1.2：Boot WLUN 測試資料寫入（FUA=1） |

---

## 附錄 C — 本 Pattern 使用的 UFS Reset / Link 操作

| 操作 | 類型 | 本 Pattern 用途 | SPEC Reference |
|:---|:---|:---|:---|
| DCMD7 SPOR Trigger | DME Command | Step 1.1：嘗試觸發 SPOR | JESD220H Section 12.2 |
| HW Reset | Hardware Reset | Step 2.1：硬體重置 | JESD220H Section 7.3 |
| Link Startup | M-PHY / UniPro | Step 2.2：鏈路初始化 | JESD220H Section 6, 7 |
| NOP OUT | UFS UPIU | Step 2.3：鏈路確認 | JESD220H Section 10.7.2 |

---

## 自我驗證

- Tree Diagram leaf steps: **13**（Phase 0: 2 (0.1~0.2), Phase 1: 2 (1.1~1.2), Phase 2: 5 (2.1~2.5), Phase 3: 3 (3.1~3.3), Phase 4: 1 (4.1) → Total: 13）
- `### Step` sections: **13** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（含 Expected 的 step: 5 個 — Step 2.1, 2.2, 2.5, 3.2, 3.3）
  - Step 2.1 (HW Reset) → Reset device success：使用者約定 Reset 類型統一使用此 Expected
  - Step 2.2 (Link Startup) → Reset device success：同上
  - Step 2.5 (Pre-Init READ) → GOOD Status, Data Match：JIRA Step 5 "read compare data pass"
  - Step 3.2 (READ FLAG fDeviceInit) → fDeviceInit == 0：JIRA Step 6 "until init flow has finished"
  - Step 3.3 (Post-Init READ) → GOOD Status, Data Match：JIRA Step 8 "read compare data pass"
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文或用戶約定）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
