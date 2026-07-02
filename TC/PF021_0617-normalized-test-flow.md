---
title: PF021_0617_CMD_History_SSU-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf021_0617, scsi-cmd, cmd-history, ssu, error-injection]
description: >
  驗證 UFS 裝置在 SSU Sleep/VCC off 狀態下，錯誤 CMD 與正常 CMD 的
  CMD History 記錄行為：Flash CMD History 不記錄錯誤 CMD（A == C），
  RAM CMD History 記錄所有 CMD（B 包含 Step 2~6）。適用於 UFS 3.1 + 8318 BICS5 (OPPO)。
sources:
  - JIRA: PF021_0617 (SYSTCUFS-765)
  - UFS Spec: JESD220H Section 10.7.8, 11.4.5, 11.6.4, 11.6.5
---

# PF021_0617 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 UFS 裝置 CMD History 在 SSU Sleep 狀態下的正確性：
- **Flash CMD History** 不應記錄 Sleep 期間的 Error CMD（A == C）
- **RAM CMD History** 應記錄包含 Error CMD 在內的所有命令（B 包含 Step 2~6）

## JIRA Step 對照

| JIRA Step | 原始描述 | 正規化後對應 |
|-----------|---------|-------------|
| Step 1 | IC/NAND 檢查 (8318 BICS5, UFS 3.1) | Phase 0 Step 0.1 |
| Step 2 | 記錄 Flash CMD History A | Phase 1 Step 1.1 ~ 1.2 |
| Step 3 | SSU Sleep + VCC off | Phase 2 Step 2.1 (Loop 內) |
| Step 4 | Error Cases (9 種) | Phase 3 Step 3.1 ~ 3.9 (Loop 內，Branch) |
| Step 5 | SSU Active + VCC on | Phase 4 Step 4.1 (Loop 內) |
| Step 6 | 記錄 RAM CMD History B | Phase 5 Step 5.1 ~ 5.2 (Loop 內) |
| Step 7 | 記錄 Flash CMD History C | Phase 6 Step 6.1 ~ 6.2 (Loop 內) |
| Step 8 | 驗證 CMD History (B 含 Step 2~6, A == C) | Phase 7 Step 7.1 ~ 7.2 (Loop 內) |
| Step 9 | Loop Step 3~8 N 次 | Loop 包裝 |
| Step 10 | Read compare all | Phase 8 Step 8.1 |

---

## 測試架構（Tree Diagram — 含 Expected）

```
PF021_0617 Test Flow
│
├── Phase 0: Pre-condition — 裝置相容性檢查
│   └── Step 0.1: Hardware Gate — IC=8318, NAND=BICS5, UFS=3.1
│
├── Phase 1: 記錄 Flash CMD History A（Sleep 前 Baseline）
│   ├── Step 1.1: WRITE BUFFER (VU, Mode=E1h) — 設定 Flash CMD History 讀取目標 → Expected: GOOD Status
│   └── Step 1.2: READ BUFFER (VU, Mode=01h) — 讀取 Flash CMD History 並記錄 Trans Code / Task Tag → Expected: GOOD Status
│
└── Loop (N 次，每次選一種 Error Case)
    ├── Phase 2: SSU Sleep + VCC off
    │   └── Step 2.1: START STOP UNIT — SSU Sleep
    │
    ├── Phase 3: Error Case（每次選一種，共 9 種）
    │   ├── Branch Case 1 (Out of Range Write):
    │   │   └── Step 3.1: WRITE(10) — LBA=capacity+1, LEN=5 → Expected: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)
    │   ├── Branch Case 2 (Write Protected):
    │   │   └── Step 3.2: WRITE(10) — LUN=1, LBA=0, LEN=5 → Expected: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)
    │   ├── Branch Case 3 (Invalid CDB):
    │   │   └── Step 3.3: WRITE BUFFER — LUN=0, Mode=0xF (Invalid) → Expected: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)
    │   ├── Branch Case 4 (Query Error — Flag Not Readable):
    │   │   └── Step 3.4: READ FLAG — IDN=fRefreshEnable(0x07) → Expected: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)
    │   ├── Branch Case 5 (MODE_SENSE Invalid Page):
    │   │   └── Step 3.5: MODE SENSE(10) — Page=0x02, PC=CUR_VALUE(0) → Expected: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)
    │   ├── Branch Case 6 (Vendor CMD 0xFF):
    │   │   └── Step 3.6: Vendor CMD — Opcode=0xFF → Expected: response failure (res_failure)
    │   ├── Branch Case 7 (Write Buffer Vendor CMD Error):
    │   │   └── Step 3.7: WRITE BUFFER — Mode=E1h, BufferID=0xFF, VU payload → Expected: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)
    │   ├── Branch Case 8 (Read Buffer Vendor CMD Error, 2 sub-steps):
    │   │   ├── Step 3.8a: WRITE BUFFER — Mode=E1h, VU payload (get smart info) → Expected: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)
    │   │   └── Step 3.8b: READ BUFFER — Mode=01h, BufferID=0xFF → Expected: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)
    │   └── Branch Case 9 (No Error):
    │       └── Step 3.9: NOP — 不發送任何命令
    │
    ├── Phase 4: SSU Active + VCC on
    │   └── Step 4.1: START STOP UNIT — SSU Active
    │
    ├── Phase 5: 記錄 RAM CMD History B
    │   ├── Step 5.1: WRITE BUFFER (VU, Mode=E1h) — 設定 RAM CMD History 讀取目標 → Expected: GOOD Status
    │   └── Step 5.2: READ BUFFER (VU, Mode=01h) — 讀取 RAM CMD History 並記錄 Trans Code / Task Tag → Expected: GOOD Status
    │
    ├── Phase 6: 記錄 Flash CMD History C
    │   ├── Step 6.1: WRITE BUFFER (VU, Mode=E1h) — 設定 Flash CMD History 讀取目標 → Expected: GOOD Status
    │   └── Step 6.2: READ BUFFER (VU, Mode=01h) — 讀取 Flash CMD History 並記錄 Trans Code / Task Tag → Expected: GOOD Status
    │
    └── Phase 7: 驗證 CMD History
        ├── Step 7.1: Verify — CMD History B 包含 Step 2~6 CMD → Expected: CMD history B contains Step 2~6 CMDs
        └── Step 7.2: Verify — CMD History A == CMD History C → Expected: CMD history A == CMD history C

└── Phase 8: Post-Loop — 資料完整性驗證
    └── Step 8.1: READ(10) — Read compare all → Expected: GOOD Status (Data Match)
```

---

## Phase 0 — Pre-condition（裝置相容性檢查）

### Step 0.1: 裝置相容性檢查

**目的**: 確認 IC / NAND / UFS 版本為支援的配置，若非支援的配置則終止測試。

| Field | Value |
|-------|-------|
| IC | 8318 |
| NAND | BICS5 |
| Vendor | OPPO |
| UFS Version | 3.1 |

**若不支援**: Pattern 判定為 `NOT SUPPORTED`，終止測試。

---

## Phase 1 — 記錄 Flash CMD History A（Sleep 前 Baseline）

### Step 1.1: WRITE BUFFER — 設定 Flash CMD History 讀取目標（VU, Mode=E1h）

**SCSI CMD**: `WRITE BUFFER (3Bh)` — Mode = Vendor Specific (E1h)

**目的**: 透過 Vendor Unique WRITE BUFFER 命令設定 Flash CMD History 的讀取參數，為後續 READ BUFFER 擷取 CMD History 做準備。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| Byte 1 (Mode + Buffer ID) | 0xE1 | Mode=E1h (Vendor Specific) |
| Transfer Length | 0x000004 | 4 bytes (VU payload) |
| VU Payload byte[0] | 0xF9 | CMD index (Flash CMD History target) |
| VU Payload byte[1] | 0x40 | CMD index |
| VU Payload byte[2] | 0x14 | Read length LSB |
| VU Payload byte[3] | 0x14 | Read length MSB |

**Expected**: GOOD Status（JIRA: "expect device rsp pass"）。

**UFS SPEC Reference**: JESD220H Section 11.6.5（WRITE BUFFER）；Mode=E1h 為 Vendor Specific，非 SPEC 定義。

---

### Step 1.2: READ BUFFER — 讀取 Flash CMD History（VU, Mode=01h）

**SCSI CMD**: `READ BUFFER (3Ch)` — Mode = 01h

**目的**: 讀取 Flash CMD History 內容，記錄其中每個 CMD 的 Trans Code 與 Task Tag 作為 CMD History A（Baseline）。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3C | READ BUFFER |
| Byte 1 (Mode + Buffer ID) | 0x01 | Mode=01h, Buffer ID=0 |
| Transfer Length | 0x001414 | 0x1414 bytes |

**Expected**: GOOD Status（JIRA: "expect device rsp pass"）。記錄回傳的 Trans Code 與 Task Tag 作為 **CMD History A**。

**UFS SPEC Reference**: JESD220H Section 11.6.4（READ BUFFER）；Mode=01h 為 Vendor Specific。

---

## Loop（N 次，每次選一種 Error Case）

### Phase 2 — SSU Sleep + VCC off

#### Step 2.1: START STOP UNIT — SSU Sleep + VCC off

**SCSI CMD**: `START STOP UNIT (1Bh)`

**目的**: 將裝置切換至 SSU Sleep 低功耗狀態，並關閉 VCC 電源（VCC off 為外部硬體操作，非 SCSI CMD）。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x1B | START STOP UNIT |
| START | 0 | Stop |
| POWER CONDITION | 0x02 | Sleep |
| IMMED | 0 | Return after operation complete |

**UFS SPEC Reference**: JESD220H Section 11.4.5（START STOP UNIT / Power Management）。

---

### Phase 3 — Error Case（每次選一種，共 9 種）

**Branch Logic** (per JIRA)：每次 Loop 迭代從以下 9 種 Error Case 中選一種執行。記錄每個 Error CMD 的 Trans Code 與 Task Tag 以供後續 CMD History 驗證。

---

#### Step 3.1: WRITE(10) — Case 1: Out of Range Write

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對超出容量範圍的 LBA 發送 Write 命令，驗證裝置回應 NOT_READY 錯誤。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x2A | WRITE(10) |
| LBA | capacity + 1 | 超出最大 LBA |
| Transfer Length | 5 | 5 blocks |
| WRPROTECT | 0 | No write protect |

**Expected**: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)（JIRA: "expect Sense Key = SK_NOT_READY"）。

**UFS SPEC Reference**: JESD220H Section 11.2.5（WRITE(10)）。

---

#### Step 3.2: WRITE(10) — Case 2: Write Protected LUN

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 對 Write Protected 的 LUN 發送 Write 命令（LUN=1），驗證裝置回應 NOT_READY 錯誤。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x2A | WRITE(10) |
| LUN | 1 | Write-Protected LUN |
| LBA | 0 | LBA 0 |
| Transfer Length | 5 | 5 blocks |
| WRPROTECT | 0 | No write protect |

**Expected**: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)（JIRA: "expect Sense Key = SK_NOT_READY"）。

**UFS SPEC Reference**: JESD220H Section 11.2.5（WRITE(10)）。

---

#### Step 3.3: WRITE BUFFER — Case 3: Invalid CDB Mode

**SCSI CMD**: `WRITE BUFFER (3Bh)` — Mode = 0xF (Invalid)

**目的**: 以無效的 Mode=0xF 發送 WRITE BUFFER，驗證裝置回應 NOT_READY 錯誤。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| LUN | 0 | LUN 0 |
| Byte 1 (Mode + Buffer ID) | 0x0F | Mode=0xF (Invalid Mode) |
| Transfer Length | 4096 | 4KB |

**Expected**: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)（JIRA: "expect Sense Key = SK_NOT_READY"）。

**UFS SPEC Reference**: JESD220H Section 11.6.5（WRITE BUFFER）；Mode=0xF 不在標準定義範圍內。

---

#### Step 3.4: READ FLAG — Case 4: Query Error (Flag Not Readable)

**UFS QUERY**: `READ FLAG (01h)` — fRefreshEnable (IDN 0x07)

**目的**: 對不可讀取的 Flag 發送 READ FLAG 查詢，驗證裝置回應 NOT_READY 錯誤。

| Field | Value | Description |
|-------|-------|-------------|
| Query Opcode | 0x01 | READ FLAG |
| Flag IDN | 0x07 | fRefreshEnable |
| Selector | 0x00 | Default |

**Expected**: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)（JIRA: "expect Sense Key = SK_NOT_READY"）。

**UFS SPEC Reference**: JESD220H Section 10.7.8.1（READ FLAG）；Section 14.2（Flag IDN 0x07）。

---

#### Step 3.5: MODE SENSE(10) — Case 5: MODE_SENSE Invalid Page (ILLEGAL_REQUEST)

**SCSI CMD**: `MODE SENSE(10) (5Ah)`

**目的**: 以無效的 Page Code=0x02 發送 MODE SENSE，驗證裝置回應 NOT_READY 錯誤。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x5A | MODE SENSE(10) |
| LUN | 0 | LUN 0 |
| DBD | 0 | Disable Block Descriptor = not disabled |
| PC (Page Control) | 0 (00b) | Current Values |
| Page Code | 0x02 | Invalid Page (per this test context) |
| Allocation Length | 4096 | 4KB |

**Expected**: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)（JIRA: "expect device rsp Sense Key = SK_NOT_READY"）。

**UFS SPEC Reference**: JESD220H Section 11.4.3（MODE SENSE(10)）。

---

#### Step 3.6: Vendor CMD — Case 6: Invalid Vendor Command 0xFF

**目的**: 發送無效的 Vendor Command Opcode=0xFF，驗證裝置回應 failure。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0xFF | Invalid / Vendor specific (undefined) |

**Expected**: response failure (res_failure)（JIRA: "expect rsp res_failure"）。

**UFS SPEC Reference**: JESD220H Section 7.1（Command UFS Protocol Information Unit）；Opcode 0xFF 不在標準定義中。

---

#### Step 3.7: WRITE BUFFER — Case 7: Write Buffer Vendor CMD Error

**SCSI CMD**: `WRITE BUFFER (3Bh)` — Mode=E1h, BufferID=0xFF, Invalid VU Payload

**目的**: 以無效的 BufferID=0xFF 和無效 VU payload 發送 WRITE BUFFER，驗證裝置回應 NOT_READY 錯誤。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| LUN | 0 | LUN 0 |
| Byte 1 (Mode + Buffer ID) | 0xFF | Mode=E1h, BufferID=0xFF (Invalid) |
| Transfer Length | 0x000004 | 4 bytes |
| VU Payload byte[0] | 0xFF | Invalid CMD index |
| VU Payload byte[1] | 0xFF | Invalid CMD index |
| VU Payload byte[2] | 0xFF | Invalid |
| VU Payload byte[3] | 0xFF | Invalid |

**Expected**: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)（JIRA: "expect rsp Sense Key = SK_NOT_READY"）。

**UFS SPEC Reference**: JESD220H Section 11.6.5（WRITE BUFFER）。

---

#### Step 3.8a: WRITE BUFFER — Case 8a: Write Buffer Vendor CMD Error (get smart info)

**SCSI CMD**: `WRITE BUFFER (3Bh)` — Mode=E1h, VU Payload (get smart info)

**目的**: 以 get smart info 的 VU payload 發送 WRITE BUFFER（此操作在當前狀態下為非法），驗證裝置回應 NOT_READY 錯誤。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| LUN | 0 | LUN 0 |
| Byte 1 (Mode + Buffer ID) | 0xE1 | Mode=E1h |
| Transfer Length | 4096 | 4KB |
| VU Payload byte[0] | 0xBB | CMD index (get smart info) |
| VU Payload byte[1] | 0x40 | CMD index |
| VU Payload byte[2] | 0x10 | Length |
| VU Payload byte[3] | 0x00 | Length |

**Expected**: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)（JIRA: "expect rsp Sense Key = SK_NOT_READY"）。

**UFS SPEC Reference**: JESD220H Section 11.6.5（WRITE BUFFER）。

---

#### Step 3.8b: READ BUFFER — Case 8b: Read Buffer Vendor CMD Error

**SCSI CMD**: `READ BUFFER (3Ch)` — Mode=01h, BufferID=0xFF

**目的**: 以無效的 BufferID=0xFF 發送 READ BUFFER，驗證裝置回應 NOT_READY 錯誤。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3C | READ BUFFER |
| LUN | 0 | LUN 0 |
| Byte 1 (Mode + Buffer ID) | 0xFF | Mode=01h, BufferID=0xFF (Invalid) |
| Transfer Length | 1024 | 1KB |

**Expected**: CHECK_CONDITION, SENSE_KEY=NOT_READY(02h)（JIRA: "expect rsp Sense Key = SK_NOT_READY"）。

**UFS SPEC Reference**: JESD220H Section 11.6.4（READ BUFFER）。

---

#### Step 3.9: NOP — Case 9: No Error (Do Nothing)

**目的**: 不發送任何 Error CMD，作為對照組（確認無 Error 時的 CMD History 記錄行為）。

此 Case 不發送任何 SCSI CMD 或 UFS Query。

---

### Phase 4 — SSU Active + VCC on

#### Step 4.1: START STOP UNIT — SSU Active + VCC on

**SCSI CMD**: `START STOP UNIT (1Bh)`

**目的**: 將裝置從 Sleep 狀態喚醒至 Active 狀態，並開啟 VCC 電源（VCC on 為外部硬體操作，非 SCSI CMD）。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x1B | START STOP UNIT |
| START | 1 | Start |
| POWER CONDITION | 0x01 | Active |
| IMMED | 0 | Return after operation complete |

**UFS SPEC Reference**: JESD220H Section 11.4.5（START STOP UNIT / Power Management）。

---

### Phase 5 — 記錄 RAM CMD History B

#### Step 5.1: WRITE BUFFER — 設定 RAM CMD History 讀取目標（VU, Mode=E1h）

**SCSI CMD**: `WRITE BUFFER (3Bh)` — Mode = Vendor Specific (E1h)

**目的**: 透過 Vendor Unique WRITE BUFFER 命令設定 RAM CMD History 的讀取參數（CMD index 0xF840 指向 RAM CMD History，區別於 Flash 的 0xF940）。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| Byte 1 (Mode + Buffer ID) | 0xE1 | Mode=E1h (Vendor Specific) |
| Transfer Length | 0x000004 | 4 bytes (VU payload) |
| VU Payload byte[0] | 0xF8 | CMD index (RAM CMD History target) |
| VU Payload byte[1] | 0x40 | CMD index |
| VU Payload byte[2] | 0x14 | Read length LSB |
| VU Payload byte[3] | 0x14 | Read length MSB |

**Expected**: GOOD Status（JIRA: "expect device rsp pass"）。

**UFS SPEC Reference**: JESD220H Section 11.6.5（WRITE BUFFER）；Mode=E1h 為 Vendor Specific。

---

#### Step 5.2: READ BUFFER — 讀取 RAM CMD History（VU, Mode=01h）

**SCSI CMD**: `READ BUFFER (3Ch)` — Mode = 01h

**目的**: 讀取 RAM CMD History 內容，記錄其中每個 CMD 的 Trans Code 與 Task Tag 作為 CMD History B。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3C | READ BUFFER |
| Byte 1 (Mode + Buffer ID) | 0x01 | Mode=01h, Buffer ID=0 |
| Transfer Length | 0x001414 | 0x1414 bytes |

**Expected**: GOOD Status（JIRA: "expect device rsp pass"）。記錄回傳的 Trans Code 與 Task Tag 作為 **CMD History B**。

**UFS SPEC Reference**: JESD220H Section 11.6.4（READ BUFFER）。

---

### Phase 6 — 記錄 Flash CMD History C

#### Step 6.1: WRITE BUFFER — 設定 Flash CMD History 讀取目標（VU, Mode=E1h）

**SCSI CMD**: `WRITE BUFFER (3Bh)` — Mode = Vendor Specific (E1h)

**目的**: 與 Step 1.1 相同，透過 VU WRITE BUFFER 設定 Flash CMD History 讀取參數（CMD index 0xF940）。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3B | WRITE BUFFER |
| Byte 1 (Mode + Buffer ID) | 0xE1 | Mode=E1h (Vendor Specific) |
| Transfer Length | 0x000004 | 4 bytes (VU payload) |
| VU Payload byte[0] | 0xF9 | CMD index (Flash CMD History target) |
| VU Payload byte[1] | 0x40 | CMD index |
| VU Payload byte[2] | 0x14 | Read length LSB |
| VU Payload byte[3] | 0x14 | Read length MSB |

**Expected**: GOOD Status（JIRA: "expect device rsp pass"）。

**UFS SPEC Reference**: JESD220H Section 11.6.5（WRITE BUFFER）；Mode=E1h 為 Vendor Specific。

---

#### Step 6.2: READ BUFFER — 讀取 Flash CMD History（VU, Mode=01h）

**SCSI CMD**: `READ BUFFER (3Ch)` — Mode = 01h

**目的**: 讀取 Flash CMD History 內容，記錄其中每個 CMD 的 Trans Code 與 Task Tag 作為 CMD History C。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x3C | READ BUFFER |
| Byte 1 (Mode + Buffer ID) | 0x01 | Mode=01h, Buffer ID=0 |
| Transfer Length | 0x001414 | 0x1414 bytes |

**Expected**: GOOD Status（JIRA: "expect device rsp pass"）。記錄回傳的 Trans Code 與 Task Tag 作為 **CMD History C**。

**UFS SPEC Reference**: JESD220H Section 11.6.4（READ BUFFER）。

---

### Phase 7 — 驗證 CMD History

#### Step 7.1: Verify — CMD History B 包含 Step 2~6 CMD

**目的**: 驗證 RAM CMD History（B）包含了 Step 2（Phase 1 WRITE/READ BUFFER）至 Step 6（Phase 5 WRITE/READ BUFFER）之間的所有 CMD，包括 Error CMD 和正常 CMD。

**驗證項目**:
- CMD History B (RAM) 的 Trans Code / Task Tag 清單應包含 Phase 1 ~ Phase 5 所有發送過的 CMD

**Expected**: CMD history B contains Step 2~6 CMDs（JIRA: "CMD history B 包含step2~6 CMD"）。

---

#### Step 7.2: Verify — CMD History A == CMD History C

**目的**: 驗證 Flash CMD History 在 Sleep 前（A）與 Sleep 後（C）內容相同，確認 Error CMD 未被寫入 Flash CMD History。

**驗證項目**:
- CMD History A (Pre-Sleep Flash) 的 Trans Code / Task Tag 清單應與 CMD History C (Post-Sleep Flash) 完全相同

**Expected**: CMD history A == CMD history C（JIRA: "CMD history A 與 CMD history C相同"）。

---

## Phase 8 — Post-Loop: Read Compare All（資料完整性驗證）

### Step 8.1: READ(10) — Read Compare All

**SCSI CMD**: `READ(10) (28h)`

**目的**: 在所有 Error Case Loop 完成後，對整個 LUN 進行 Read Compare，確保裝置的資料完整性未受 Error Injection 影響。

| Field | Value | Description |
|-------|-------|-------------|
| Opcode | 0x28 | READ(10) |
| LUN | 0 | LUN 0 |
| LBA | 0 | Start LBA |
| Transfer Length | (full LBA range) | 讀取整個 LUN |
| RDPROTECT | 0 | No read protect |

**Expected**: GOOD Status（Data Match）（JIRA: "Read compare all, expect device rsp pass"）。

**UFS SPEC Reference**: JESD220H Section 11.2.3（READ(10)）。

---

## 附錄 A — 本 Pattern 使用的 UFS Query 對照表

### Query Opcode

| Opcode | 名稱 | 本 Pattern 用途 |
|:---|:---|:---|
| 0x01 | READ FLAG | Case 4: 讀取 fRefreshEnable Flag 進行 Error Injection |

### Flag IDN

| IDN | 名稱 | Access | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x07 | fRefreshEnable | Volatile (Set/Clear) | Case 4: 在 Sleep 狀態下讀取此 Flag 觸發錯誤 |

---

## 附錄 B — 本 Pattern 使用的 SCSI Command 對照表

| Opcode | 命令 | CDB | 本 Pattern 用途 |
|:---|:---|:---|:---|
| 0x1B | START STOP UNIT | 6 | Phase 2: SSU Sleep / Phase 4: SSU Active |
| 0x28 | READ(10) | 10 | Phase 8: Read compare all |
| 0x2A | WRITE(10) | 10 | Case 1: Out of Range Write / Case 2: Write Protected LUN |
| 0x3B | WRITE BUFFER | 10 | Phase 1/5/6: CMD History 讀取目標設定 (VU, Mode=E1h)；Case 3/7/8a: Error Injection |
| 0x3C | READ BUFFER | 10 | Phase 1/5/6: CMD History 讀取 (VU, Mode=01h)；Case 8b: Error Injection |
| 0x5A | MODE SENSE(10) | 10 | Case 5: Invalid Page Error Injection |
| 0xFF | (Vendor Specific) | — | Case 6: 無效 Vendor CMD |

---

## 附錄 C — 本 Pattern 使用的 Reset 類型

本 Pattern 不涉及任何 Reset 操作。

---

## 附錄 D — VU (Vendor Unique) Commands 說明

本 Pattern 大量使用 Vendor Unique WRITE BUFFER / READ BUFFER 命令來讀取 CMD History。以下為 VU payload 語義說明：

### CMD History 讀取目標

WRITE BUFFER (Mode=E1h) 的 VU payload 4 bytes 指定 CMD History 讀取目標：

| VU Payload | 目標 |
|:---|:---|
| `{0xF8, 0x40, 0x14, 0x14}` | RAM CMD History（CMD index 0x40F8，讀取長度 0x1414） |
| `{0xF9, 0x40, 0x14, 0x14}` | Flash CMD History（CMD index 0x40F9，讀取長度 0x1414） |
| `{0xBB, 0x40, 0x10, 0x00}` | Get Smart Info（CMD index 0x40BB，讀取長度 0x0010） |

**注意**: 以上均為 Vendor Unique 定義，非 JESD220H SPEC 定義。在 C++ code generation 階段應以 VU byte-level payload 實作。

---

## 自我驗證

- Tree Diagram leaf steps: **22**（Phase 0: 1 (0.1), Phase 1: 2 (1.1~1.2), Loop 內 — Phase 2: 1 (2.1), Phase 3 Branch: 10 (3.1~3.9, 3.9 為單一 leaf / 3.8a+3.8b 各計), Phase 4: 1 (4.1), Phase 5: 2 (5.1~5.2), Phase 6: 2 (6.1~6.2), Phase 7: 2 (7.1~7.2), Phase 8: 1 (8.1) → Total: 22）
- `### Step` sections: **22** ✓
- `→ Expected:` 僅在原始 JIRA Pattern 有明確指出預期結果時才填入 ✓（共 18 個 Step 有 Expected，4 個無 Expected）
- 有 Expected 的 Step（18 個）: 1.1, 1.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8a, 3.8b, 5.1, 5.2, 6.1, 6.2, 7.1, 7.2, 8.1 — 全部可追溯至 JIRA SYSTCUFS-765 原文
- 無 Expected 的 Step（4 個）: 0.1 (JIRA 僅說若不支援則停止), 2.1 (JIRA 無明確預期), 3.9 (JIRA 說 No error Do nothing), 4.1 (JIRA 無明確預期) — JIRA 未指定預期結果
- 無憑空生成的 Expected 值（所有 Expected 均可追溯到 JIRA 原文）✓
- 無合併多個 SCSI CMD 或 UFS Query 於同一 Step ✓
