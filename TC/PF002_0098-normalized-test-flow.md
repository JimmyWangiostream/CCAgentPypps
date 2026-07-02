---
title: PF002_0098_Boot_Stress_Test-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_0098, scsi-cmd, boot-lun, reset, stress-test]
description: >
  驗證 Boot LUN 資料在隨機 Reset 壓力下的完整性。兩回合測試，每回合先配置並啟用 Boot LUN、
  寫入測試資料，然後進行 100 次隨機 Reset（HW_RESET / RST_n / EndPoint / UniPro），
  每次 Reset 後重新初始化裝置並比對 Boot LUN 資料。
sources:
  - JIRA: PF002_0098 (SYSTCUFS-107)
  - UFS Spec: JESD220H Section 10.6.5, 10.7.8, 10.7.9, 10.8, 11.4, 14.2, 14.3, 14.5.1
---

# PF002_0098 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

在 Boot LUN 寫入已知資料後，透過兩回合、每回合 100 次隨機 Reset 的壓力測試，
驗證 Reset 後裝置能正確初始化並完整保留 Boot LUN 的寫入資料，確保 Boot 路徑
在不同 Reset 類型下的資料完整性。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1, 7 | Config device with boot LUN is needed | Step 0.1, Step 0.2 (Phase 0, 外層迴圈每回合執行) |
| Step 2, 8 | Enable Boot LUN | Step 0.2 (WRITE ATTRIBUTE bBootLunEn) |
| Step 3, 9 | Write data to Boot LUN | Step 0.3 (WRITE(10) to Boot W-LUN) |
| Step 4, 10 | With random reset (HW_RESET / RESET_N / ENDPOINT_RESET / UNIPRO_RESET) | Step 1.1 (Phase 1, 內層迴圈每回合執行) |
| Step 5, 11 | Reboot and read compare boot data | Step 2.1 + Step 2.2 (Phase 2) |
| Step 6, 12 | loop step 4, 100 times | 內層 Loop（100 次） |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF002_0098 Test Flow
│
└── Loop（2 回合，Round 1 & Round 2）
    │
    ├── Phase 0: Boot LUN 組態配置
    │   ├── Step 0.1: QUERY WRITE DESCRIPTOR (Device Descriptor) — 配置 Boot 參數
    │   ├── Step 0.2: QUERY WRITE ATTRIBUTE (bBootLunEn) — 啟用 Boot LUN
    │   └── Step 0.3: WRITE(10) — 寫入測試資料至 Boot W-LUN
    │
    └── Loop（100 次）
        ├── Phase 1: 隨機 Reset
        │   └── Step 1.1: Reset — 隨機選取 Reset 類型執行
        │
        └── Phase 2: Boot Data 讀取驗證
            ├── Step 2.1: QUERY READ FLAG (fDeviceInit) — 確認裝置初始化完成
            └── Step 2.2: READ(10) — 讀取 Boot W-LUN 並比對資料
```

**Expected 說明**：原始 JIRA Pattern（SYSTCUFS-107）未明確指出任何步驟的預期結果，因此本 Tree Diagram 不包含 `→ Expected:` 標註。

---

## Phase 0 — Boot LUN 組態配置

> **執行時機**：外層迴圈每回合開始時執行一次。

### Step 0.1: 配置 Device Descriptor Boot 參數

**UFS QUERY**: `WRITE DESCRIPTOR` — Device Descriptor (IDN 0x00)

**目的**: 設定 Device Descriptor 中的 Boot 相關欄位（bBootEnable），使裝置支援 Boot 功能。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| Descriptor IDN | 0x00 (Device Descriptor) |
| bBootEnable | 0x01 (Boot Enable) |

**UFS SPEC Reference**: JESD220H Section 10.7.9 (WRITE DESCRIPTOR), Section 14.5.1 (Device Descriptor)

---

### Step 0.2: 啟用 Boot LUN

**UFS QUERY**: `WRITE ATTRIBUTE` — bBootLunEn (IDN 0x00)

**目的**: 設定 bBootLunEn Attribute，將目標 LUN 標示為 Boot LUN，使其可透過 Boot W-LUN 存取。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| Attribute IDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |
| Value | 依據目標 Boot LUN 設定對應 bit（bit 0 = Boot LU A, bit 1 = Boot LU B） |

**UFS SPEC Reference**: JESD220H Section 10.7.8 (WRITE ATTRIBUTE), Section 14.3 (bBootLunEn)

---

### Step 0.3: 寫入測試資料至 Boot W-LUN

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 將已知測試 Pattern 資料寫入 Boot W-LUN，作為後續 Reset 壓力後的比對基準。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | Boot W-LUN（0xB0 = BOOT_WELL_KNOWN_LU_A 或 0xB1 = BOOT_WELL_KNOWN_LU_B） |
| LBA | 0x00000000 |
| Transfer Length | 依據測試資料大小（N blocks） |
| DPO | 0 |
| FUA | 0 |
| FUA_NV | 0 |

**備註**: Boot W-LUN 位址參照 JESD220H Section 10.6.5（Well-Known Logical Units）。

**UFS SPEC Reference**: JESD220H Section 11.4.2 (WRITE(10)), Section 10.6.5 (Boot W-LUN)

---

## Phase 1 — 隨機 Reset

### Step 1.1: 執行隨機 Reset

**UFS OPERATION**: Reset

**目的**: 對裝置執行隨機選取的 Reset 類型，模擬真實應用中可能遇到的各種 Reset 情境，驗證 Boot 資料的持久性。

| Field | Value |
|-------|-------|
| Reset Type | 隨機選取：HW_RESET / RST_n / EndPoint Reset / UniPro Reset |
| 選取方式 | 每次迴圈迭代從四種 Reset 類型中均勻隨機選取 |

**Reset 類型說明**：

| Reset 類型 | 說明 |
|:---|:---|
| HW_RESET | 硬體電源重置（Power cycle），模擬斷電重啟 |
| RST_n | 硬體 Reset 腳位觸發 |
| EndPoint Reset | UFS EndPoint 層級 Reset（DME_ENDPOINTRESET） |
| UniPro Reset | UniPro 鏈路層級 Reset（DME_LINKSTARTUP / DME_RESET） |

**UFS SPEC Reference**: JESD220H Section 10.8 (Reset), Section 10.4 (UFS Transport Protocol)

---

## Phase 2 — Boot Data 讀取驗證

> **執行時機**：每次 Reset 後執行。

### Step 2.1: 確認裝置初始化完成

**UFS QUERY**: `READ FLAG` — fDeviceInit (IDN 0x01)

**目的**: Reset 後查詢 fDeviceInit 旗標，確認裝置已完成初始化並進入就緒狀態，再進行後續 Boot 資料存取。

| Field | Value |
|-------|-------|
| Query Opcode | 0x01 (READ FLAG) |
| Flag IDN | 0x01 (fDeviceInit) |
| Selector | 0x00 |

**備註**: 若 fDeviceInit == 1，表示裝置仍在初始化中，需等待後重新查詢。建議以 polling 方式等待至 fDeviceInit == 0。

**UFS SPEC Reference**: JESD220H Section 10.7.8.1 (READ FLAG), Section 14.2 (fDeviceInit)

---

### Step 2.2: 讀取 Boot W-LUN 並比對資料

**SCSI CMD**: `READ(10) (28h)`

**目的**: 讀取 Boot W-LUN 中的資料，與 Step 0.3 寫入的原始測試 Pattern 進行逐 byte 比對，確認 Reset 後資料完整性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | Boot W-LUN（與 Step 0.3 相同） |
| LBA | 0x00000000 |
| Transfer Length | 與 Step 0.3 相同（N blocks） |
| RARC | 0 |

**比對邏輯**: 將 READ(10) 回傳的資料與 Step 0.3 寫入的原始測試 Pattern 逐 byte 比對。

**UFS SPEC Reference**: JESD220H Section 11.4.1 (READ(10)), Section 10.6.5 (Boot W-LUN)

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x01 | READ FLAG | 查詢 fDeviceInit 確認裝置就緒 |
| 0x04 | WRITE ATTRIBUTE | 寫入 bBootLunEn 啟用 Boot LUN |
| 0x08 | WRITE DESCRIPTOR | 寫入 Device Descriptor 配置 Boot 參數 |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x01 | fDeviceInit | Read-Only（No） | Reset 後確認裝置初始化完成 |

### Attribute IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x00 | bBootLunEn | Read-Write | 設定目標 LUN 為 Boot LUN |

### Descriptor IDN

| IDN | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x00 | Device Descriptor | 配置 bBootEnable 等 Boot 相關參數 |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | Reset 後讀取 Boot W-LUN 驗證資料完整性 |
| 0x2A | WRITE(10) | 10 | 寫入測試 Pattern 至 Boot W-LUN |

---

## 附錄 C — 本 Pattern 使用的 Reset 類型

| Reset 類型 | SPEC Reference | 說明 |
|:---|:---|:---|
| HW_RESET | JESD220H Section 10.8.1 | 硬體電源重置，模擬完整斷電重啟流程 |
| RST_n | JESD220H Section 10.8.2 | 硬體 Reset 腳位觸發 |
| EndPoint Reset | JESD220H Section 10.8.3 | UFS EndPoint 層級重置，不影響 UniPro 鏈路 |
| UniPro Reset | JESD220H Section 10.8.4 | UniPro 鏈路層級重置，重新建立 M-PHY 鏈路 |

---

## 自我驗證

- Tree Diagram leaf steps: **6**（Phase 0: 3 (0.1~0.3), Phase 1: 1 (1.1), Phase 2: 2 (2.1~2.2) → Total: 6）
- `### Step` sections: **6** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（JIRA SYSTCUFS-107 無任何步驟提及預期結果，故本文件 0 個 Expected）
- 無憑空生成的 Expected 值 ✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
