---
title: PF002_1913_D_BootLun_Diff_AU_Memory_Type_POR_SPOR-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf002_1913, scsi-cmd, boot-lun, por, spor, unmap]
description: >
  驗證在不同 Boot LUN 配置（Diff AU、不同 Memory Type）下，經過多次 POR Reset（Power Cycle / Reset_N / Endpoint / Unipro）後 Boot Data 的資料完整性，
  以及 UNMAP 操作在 POR 前後的正確性，最後透過 DCMD7 進行 SPOR Detect 與 Reinit 測試。
sources:
  - JIRA: PF002_1913 (SYSTCUFS-2218)
  - UFS Spec: JESD220H Sections 10.5, 10.7.8–10.7.9, 11.6, 14.2–14.3
---

# PF002_1913 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置在不同 Boot LUN 配置（不同 LUN 數量、不同 Boot A/B 指派、不同 Memory Type）下，
經過多次 POR Reset 後的 Boot Data 完整性及 UNMAP 行為正確性。
最終階段透過 DCMD7 觸發 SPOR Detect，在隨機 Write/Read 混合壓力下驗證裝置的 SPOR 恢復能力。

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | Check IC + NAND (8363 BICS8/BiCS9 KIC)，若不支援則 non support | Phase 0 Step 0.1 |
| Step 2 | Config BootLU（LUN → Boot A / Boot B / 0 對照表） | Phase 1 Steps 1.1–1.2 |
| Step 3 | Random write 5GB，random LUN/chunksize/LBA/FUA | Phase 1 Step 1.3 |
| Step 4 | Do POR reset（Power Cycle / Reset_N / Endpoint / Unipro） | Phase 2 Step 2.1 |
| Step 5 | Read compare step3 data | Phase 2 Step 2.2 |
| Step 6 | Do POR reset | Phase 2 Step 2.3 |
| Step 7 | Random unmap 1GB | Phase 2 Step 2.4 |
| Step 8 | Do POR reset | Phase 2 Step 2.5 |
| Step 9 | Read compare step3 data | Phase 2 Step 2.6 |
| Step 10 | Loop step3~step9, 10 times | Loop (10×) 包裹 Phase 2 |
| Step 11 | Enable DCMD7 detect（random reset type / detect cnt / delay） | Phase 3 Step 3.1 |
| Step 12 | Random write + read × 256 cmds | Phase 3 Steps 3.2–3.3 |
| Step 13 | Handle SPOR reinit — reinit device after SPOR | Phase 3 Step 3.4 |
| Step 14 | Loop step11~step13, 10 times | Loop (10×) 包裹 Phase 3 |
| Step 15 | Loop step2~step14 until case11 test done | 最外層 Loop（直到 DCMD7 detect 測試完成） |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF002_1913 Test Flow
│
├── Phase 0: Pre-condition（裝置相容性檢查）
│   └── Step 0.1: 裝置相容性檢查 — IC/NAND 檢查（8363 BICS8/BiCS9 KIC）
│
└── Loop（Boot LUN Config Iterations，直到 DCMD7 Detect 測試完成）
    │
    ├── Phase 1: Boot LUN 配置與初始資料寫入
    │   ├── Step 1.1: WRITE ATTRIBUTE (bBootLunEn) — 設定 Boot LUN Enable 位元遮罩
    │   ├── Step 1.2: WRITE DESCRIPTOR (Unit Descriptor) — 設定各 LUN 的 Boot LUN 類型（Boot A / Boot B）
    │   └── Step 1.3: WRITE(10) — 隨機寫入 5GB 測試資料 → Expected: GOOD Status
    │
    ├── Loop（10 次）：POR Reset + Read Compare + Unmap
    │   │
    │   ├── Phase 2: POR Reset 與資料完整性驗證循環
    │   │   ├── Step 2.1: POR Reset（Power Cycle / Reset_N / Endpoint / Unipro 擇一）
    │   │   ├── Step 2.2: READ(10) + Compare — 讀取並比對 Step 1.3 寫入的資料 → Expected: GOOD Status, Data Match
    │   │   ├── Step 2.3: POR Reset（Power Cycle / Reset_N / Endpoint / Unipro 擇一）
    │   │   ├── Step 2.4: UNMAP — 隨機 UNMAP 1GB → Expected: GOOD Status
    │   │   ├── Step 2.5: POR Reset（Power Cycle / Reset_N / Endpoint / Unipro 擇一）
    │   │   └── Step 2.6: READ(10) + Compare — 讀取並比對 Step 1.3 未 UNMAP 區域的資料 → Expected: GOOD Status, Data Match
    │
    └── Loop（10 次）：DCMD7 / SPOR Detect 與重啟
        │
        └── Phase 3: DCMD7 SPOR 偵測與恢復
            ├── Step 3.1: Enable DCMD7 Detect — 設定 SPOR 偵測參數（reset type / detect count / delay）
            ├── Step 3.2: WRITE(10) — 隨機寫入（總命令數 256） → Expected: GOOD Status
            ├── Step 3.3: READ(10) — 隨機讀取（總命令數 256） → Expected: GOOD Status
            └── Step 3.4: SPOR Reinit — 裝置 SPOR 恢復後重新初始化
```

**Expected 來源對照（僅 JIRA 原文有明確 expect 才填入）：**

| Step | Expected | JIRA 來源 |
|------|----------|----------|
| 1.3 | GOOD Status | "expect response successful" |
| 2.2 | GOOD Status, Data Match | "expect response successful expect compare pass" |
| 2.4 | GOOD Status | "expect response successful" |
| 2.6 | GOOD Status, Data Match | "expect response successful expect compare pass" |
| 3.2 | GOOD Status | "expect response successful" |
| 3.3 | GOOD Status | "expect response successful" |
| 2.1, 2.3, 2.5 | Reset device success | 使用者指定：所有 Reset 類型統一使用此格式 |
| 0.1, 1.1, 1.2, 3.1, 3.4 | （無 Expected） | JIRA 未描述預期結果 |

---

## Phase 0 — Pre-condition（裝置相容性檢查）

### Step 0.1: 裝置相容性檢查

**目的**: 確認 IC / NAND 組合為此 Pattern 支援的配置。

| Field | Value |
|-------|-------|
| IC | 8363 |
| NAND | BICS8 或 BiCS9 |
| Vendor | KIC |

**若不支援**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

**UFS SPEC Reference**: 此為 Vendor-Specific 硬體檢查，非 UFS SPEC 定義。

---

## Phase 1 — Boot LUN 配置與初始資料寫入

### Step 1.1: WRITE ATTRIBUTE (bBootLunEn) — 設定 Boot LUN Enable

**UFS QUERY**: `WRITE ATTRIBUTE (0x04)` — bBootLunEn

**目的**: 設定 Boot LUN Enable 位元遮罩，指定哪些 LUN 作為 Boot LUN。

| Field | Value |
|-------|-------|
| Query Opcode | 0x04 (WRITE ATTRIBUTE) |
| bAttrIDN | 0x00 (bBootLunEn) |
| Selector | 0x00 |
| Attribute Value | 依當前 Boot LUN 配置決定（bitmask：bit[0]=LUN0, bit[1]=LUN1, bit[2]=LUN2） |

**配置規則**（來自 JIRA Step 2 Boot LUN 對照表）：

Boot LUN 配置會依照 JIRA 對照表迭代，共 10 組配置：

| 迭代 | LUN 數量 | LUN0 | LUN1 | LUN2 | bBootLunEn 值 |
|------|---------|------|------|------|--------------|
| 1 | 2 | Boot A | Boot B | — | 0x03 |
| 2 | 2 | Boot A | Boot B | — | 0x03 |
| 3 | 2 | Boot B | Boot A | — | 0x03 |
| 4 | 2 | Boot B | Boot A | — | 0x03 |
| 5 | 2 | Boot A | Boot B | — | 0x03 |
| 6 | 2 | Boot A | Boot B | — | 0x03 |
| 7 | 2 | Boot A | Boot B | — | 0x03 |
| 8 | 3 | 0（非 Boot） | Boot A | Boot B | 0x06 |
| 9 | 3 | 0（非 Boot） | Boot A | Boot B | 0x06 |
| 10 | 3 | 0（非 Boot） | Boot A | Boot B | 0x06 |

**UFS SPEC Reference**: JESD220H Section 14.3 (Attributes — bBootLunEn)

---

### Step 1.2: WRITE DESCRIPTOR (Unit Descriptor) — 設定 Boot LUN 類型

**UFS QUERY**: `WRITE DESCRIPTOR (0x08)` — Unit Descriptor (IDN 0x02)

**目的**: 對每個 Boot-enabled LUN，設定其 Boot LUN 類型（Boot A = 0x00, Boot B = 0x01）。

| Field | Value |
|-------|-------|
| Query Opcode | 0x08 (WRITE DESCRIPTOR) |
| Descriptor IDN | 0x02 (Unit Descriptor) |
| Selector | 對應的 LUN 編號（0 / 1 / 2） |
| Descriptor Field | bBootLunID |
| 設定值 | 0x00 = Boot A, 0x01 = Boot B |

**操作順序**: 對表中有 Boot 指派的每個 LUN 逐一呼叫 WRITE DESCRIPTOR，寫入對應的 bBootLunID。

**UFS SPEC Reference**: JESD220H Section 14.2 (Unit Descriptor — bBootLunID), Section 10.7.9 (WRITE DESCRIPTOR)

---

### Step 1.3: WRITE(10) — 隨機寫入 5GB 測試資料

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 寫入初始測試資料，供後續 POR Reset 後的 Read Compare 驗證。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | random（已啟用的 LUN 中隨機選擇） |
| LBA | random(0, LUN capacity − chunksize) |
| Transfer Length | random(4K, 16M) |
| FUA | random(0, 1) |
| 總寫入量 | 5 GB（透過多次 WRITE(10) 累計） |

**Expected**: GOOD Status（JIRA: "expect response successful"）

**Branch Logic**（per JIRA random）:
- 每次 WRITE(10) 的 chunksize 在 4K ~ 16M 範圍內隨機
- LBA 在可用範圍內隨機
- FUA 隨機啟用或關閉

**UFS SPEC Reference**: JESD220H Section 10.9.x (WRITE(10) — SBC-4), SBC-4 Section 5.42

---

## Phase 2 — POR Reset 與資料完整性驗證循環

> **Loop**: 本 Phase 全部 Step（2.1–2.6）重複執行 **10 次**。

### Step 2.1: POR Reset（Round 1）

**操作類型**: `POR Reset`

**目的**: 執行 POR Reset，觸發裝置重新上電初始化。

| Field | Value |
|-------|-------|
| Reset 類型 | 以下擇一：Power Cycle / Reset_N / Endpoint Reset / Unipro Reset |
| Reset 來源 | JIRA Step 4 所列的 4 種 Reset 方法 |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 10.5 (Power Management — POR / Reset行为)

---

### Step 2.2: READ(10) + Compare — 讀取並比對 Step 1.3 資料（Round 1）

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 POR Reset 後讀回 Step 1.3 寫入的資料，驗證資料完整性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 對應 Step 1.3 寫入的 LUN |
| LBA | 對應 Step 1.3 寫入的 LBA 範圍 |
| Transfer Length | 對應 Step 1.3 寫入的 chunksize |

**Expected**: GOOD Status, Data Match（JIRA: "expect response successful expect compare pass"）

**備註**: 步驟執行 READ(10) 讀取資料後，進行 Host 端資料比對，確認讀回資料與原始寫入資料一致。

**UFS SPEC Reference**: JESD220H Section 10.9.x (READ(10) — SBC-4), SBC-4 Section 5.17

---

### Step 2.3: POR Reset（Round 2）

**操作類型**: `POR Reset`

**目的**: 執行第二次 POR Reset。

| Field | Value |
|-------|-------|
| Reset 類型 | 以下擇一：Power Cycle / Reset_N / Endpoint Reset / Unipro Reset |
| Reset 來源 | JIRA Step 6 所列的 4 種 Reset 方法 |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 10.5

---

### Step 2.4: UNMAP — 隨機 UNMAP 1GB

**SCSI CMD**: `UNMAP (0x42)`

**目的**: 對 Step 1.3 寫入的 LBA 範圍中，隨機選取共 1GB 進行 UNMAP（trim / unmap）。

| Field | Value |
|-------|-------|
| Opcode | 0x42 |
| LUN | 對應 Step 1.3 寫入的 LUN |
| UNMAP LBA 範圍 | random（從 Step 1.3 寫入範圍中選取） |
| UNMAP chunksize | random(4K, 16M) |
| 總 UNMAP 量 | 1 GB（透過多次 UNMAP 累計） |

**Expected**: GOOD Status（JIRA: "expect response successful"）

**UFS SPEC Reference**: JESD220H Section 10.9.x (UNMAP), SBC-4 Section 5.32

---

### Step 2.5: POR Reset（Round 3）

**操作類型**: `POR Reset`

**目的**: 執行第三次 POR Reset。

| Field | Value |
|-------|-------|
| Reset 類型 | 以下擇一：Power Cycle / Reset_N / Endpoint Reset / Unipro Reset |
| Reset 來源 | JIRA Step 8 所列的 4 種 Reset 方法 |

**Expected**: Reset device success

**UFS SPEC Reference**: JESD220H Section 10.5

---

### Step 2.6: READ(10) + Compare — 讀取並比對 Step 1.3 資料（Round 2）

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 UNMAP + POR Reset 後讀回 Step 1.3 寫入但未被 UNMAP 的資料，驗證未 UNMAP 區域的資料完整性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | 對應 Step 1.3 寫入的 LUN |
| LBA | Step 1.3 寫入範圍中未被 Step 2.4 UNMAP 的部分 |
| Transfer Length | 對應原始寫入的 chunksize |

**Expected**: GOOD Status, Data Match（JIRA: "expect response successful expect compare pass"）

**備註**: 已被 UNMAP 的 LBA 區域不進行比對。僅比對未受 UNMAP 影響的資料區域。

**UFS SPEC Reference**: JESD220H Section 10.9.x (READ(10) — SBC-4), SBC-4 Section 5.17

---

## Phase 3 — DCMD7 SPOR 偵測與恢復

> **Loop**: 本 Phase 全部 Step（3.1–3.4）重複執行 **10 次**。

### Step 3.1: Enable DCMD7 Detect — 設定 SPOR 偵測參數

**操作類型**: `DCMD7 Configuration`（Vendor-Specific Diagnostic）

**目的**: 啟用 DCMD7 SPOR（Sudden Power Off Recovery）偵測機制，設定偵測類型與參數。

| Field | Value |
|-------|-------|
| Detect Type | Response Detect |
| Reset Type | random(Power Cycle, Reset_N, Endpoint Reset, Unipro Reset) |
| rsp_detect_cnt | random(0, 256) |
| rsp_detect_delay | random(1, 1000) µs |

**Branch Logic**:
- Reset Type 在 4 種類型中隨機選擇
- 偵測次數 (rsp_detect_cnt) 在 0~256 範圍內隨機
- 偵測延遲 (rsp_detect_delay) 在 1~1000 µs 範圍內隨機

**UFS SPEC Reference**: 此為 Vendor-Specific Diagnostic 操作（DCMD7），非 UFS SPEC 標準定義。

---

### Step 3.2: WRITE(10) — 隨機寫入（DCMD7 壓力寫入）

**SCSI CMD**: `WRITE(10) (0x2A)`

**目的**: 在 SPOR 偵測啟用狀態下執行隨機寫入，模擬正常 I/O 壓力。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| LUN | random（已啟用的 LUN 中隨機選擇） |
| LBA | random(0, LUN capacity − chunksize) |
| Transfer Length | random(4K, 16M) |
| FUA | random(0, 1) |
| 總命令數 | Step 3.2 + Step 3.3 合計 256 條 SCSI 命令 |

**Expected**: GOOD Status（JIRA: "expect response successful"）

**UFS SPEC Reference**: JESD220H Section 10.9.x (WRITE(10) — SBC-4), SBC-4 Section 5.42

---

### Step 3.3: READ(10) — 隨機讀取（DCMD7 壓力讀取）

**SCSI CMD**: `READ(10) (0x28)`

**目的**: 在 SPOR 偵測啟用狀態下執行隨機讀取，與 Step 3.2 交錯執行。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| LUN | random（已啟用的 LUN 中隨機選擇） |
| LBA | random(0, LUN capacity − chunksize) |
| Transfer Length | random(4K, 16M) |
| 總命令數 | Step 3.2 + Step 3.3 合計 256 條 SCSI 命令 |

**Expected**: GOOD Status（JIRA: "expect response successful"）

**備註**: Step 3.2 與 Step 3.3 交錯執行，直到總命令數達到 256 條。

**UFS SPEC Reference**: JESD220H Section 10.9.x (READ(10) — SBC-4), SBC-4 Section 5.17

---

### Step 3.4: SPOR Reinit — 裝置 SPOR 恢復後重新初始化

**操作類型**: `SPOR Reinit`

**目的**: 在 SPOR（Sudden Power Off Recovery）被 DCMD7 觸發後，對裝置進行重新初始化。

| Field | Value |
|-------|-------|
| 操作 | 裝置重啟 + 重新初始化 |
| 觸發條件 | DCMD7 Detect 觸發 SPOR 後 |
| 初始化範圍 | Link Startup → Device Init → LU Ready |

**UFS SPEC Reference**: JESD220H Section 10.5 (Power Management — SPOR), Section 10.4 (UFS Initialization Flow)

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x04 | WRITE ATTRIBUTE | Step 1.1 — 寫入 bBootLunEn 設定 Boot LUN Enable |
| 0x08 | WRITE DESCRIPTOR | Step 1.2 — 寫入 Unit Descriptor 設定 bBootLunID |

### Attribute IDN

| IDN | 名稱 | Size | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|:---|
| 0x00 | bBootLunEn | 1 | Write-Once | Step 1.1 — 設定哪些 LUN 作為 Boot LUN（bitmask） |

### Descriptor IDN

| IDN | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x02 | Unit Descriptor | Step 1.2 — 設定各 LUN 的 bBootLunID（0x00=Boot A, 0x01=Boot B） |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB Size | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x28 | READ(10) | 10 | Steps 2.2, 2.6, 3.3 — 讀取資料並比對驗證 |
| 0x2A | WRITE(10) | 10 | Steps 1.3, 3.2 — 寫入測試資料 |
| 0x42 | UNMAP | 10 | Step 2.4 — 隨機 UNMAP / Trim |

---

## 附錄 C — 本 Pattern 使用的 Reset 類型

| Reset 類型 | JIRA 步驟 | SPEC Reference | Tree Diagram Expected |
|:---|:---|:---|:---|
| Power Cycle (POR) | Steps 4, 6, 8, 11 | JESD220H §10.5 | Reset device success |
| Reset_N (Hardware Reset) | Steps 4, 6, 8, 11 | JESD220H §10.5 | Reset device success |
| Endpoint Reset | Steps 4, 6, 8, 11 | JESD220H §10.5 (UniPro) | Reset device success |
| Unipro Reset | Steps 4, 6, 8, 11 | JESD220H §10.5 (UniPro) | Reset device success |
| SPOR Reinit | Step 13 | JESD220H §10.5 | （JIRA 未描述預期結果） |

---

## 自我驗證

- Tree Diagram leaf steps: **14**（Phase 0: 1 (0.1), Phase 1: 3 (1.1~1.3), Phase 2: 6 (2.1~2.6), Phase 3: 4 (3.1~3.4) → Total: 14）
- `### Step` sections: **14** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（有 Expected 的 step: 9 個 — 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.2, 3.3）
- 無憑空生成的 Expected 值（2.1/2.3/2.5 的 Expected 來自使用者對 Reset 步驟的統一規範，1.3/2.2/2.4/2.6/3.2/3.3 的 Expected 可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
