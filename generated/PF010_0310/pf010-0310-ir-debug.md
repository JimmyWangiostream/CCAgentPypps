# PF010_0310 IR Debug Report

**Pattern**: PF010_0310_WriteBooster_SSU_Rst-Normalized-TestFlow
**Pattern ID**: PF010_0310

---

## Stage 1 — Rule-based 解析結果

| Phase | Type | Steps | Loop Info |
|-------|------|-------|-----------|
| phase_0 | sequential | 6 |  |
| loop_4 | loop | 14 | until: None |

**Fail Condition 識別**:

- `step_1_4`: Expected ``GOOD Status`, `Data Match`` → 含條件式關鍵字 → `fail_condition` 加入
- `step_2_3`: Expected ``GOOD Status`, `Data Match`` → 含條件式關鍵字 → `fail_condition` 加入

---

## Stage 2 — Wiki 查詢結果

### phase_0 — WB 初始化配置

| 參考 Wiki Chapter | 標題 |
|------------------|------|
| `concepts/ffu.md` | FFU — Field Firmware Update |
| `concepts/psa.md` | PSA — Production State Awareness |
| `concepts/exception-events.md` | Exception Events |
| `concepts/thin-provisioning.md` | Thin Provisioning and UNMAP |
| `concepts/refresh.md` | Refresh Operation |
| `concepts/pattern-health-report.md` | Pattern: Health Report Implementation Guide |
| `entities/lun.md` | LUN — Logical Unit Number |
| `entities/scsi-commands.md` | UFS SCSI Commands (UCS) |
| `entities/device-descriptor.md` | Device Descriptor (IDN 00h) |
| `entities/unit-descriptor.md` | Unit Descriptor (IDN 02h) |
| `entities/configuration-descriptor.md` | Configuration Descriptor (IDN 01h) |
| `entities/rpmb.md` | RPMB — Replay Protected Memory Block |

### loop_4 — Burn-in

| 參考 Wiki Chapter | 標題 |
|------------------|------|
| `concepts/refresh.md` | Refresh Operation |
| `concepts/ffu.md` | FFU — Field Firmware Update |
| `concepts/psa.md` | PSA — Production State Awareness |
| `concepts/exception-events.md` | Exception Events |
| `concepts/pattern-inhibition-time.md` | Pattern: Inhibition Time Implementation Guide |
| `concepts/pattern-rpmb.md` | Pattern: RPMB Implementation Guide |
| `entities/flags.md` | UFS Flags |
| `entities/scsi-commands.md` | UFS SCSI Commands (UCS) |
| `entities/device-health-descriptor.md` | Device Health Descriptor (IDN 09h) |
| `entities/unit-descriptor.md` | Unit Descriptor (IDN 02h) |
| `entities/device-descriptor.md` | Device Descriptor (IDN 00h) |
| `entities/upiu.md` | UPIU Types |

---

## Stage 3 — LLM 標注決策

### 資料流 (data_flow per edge)

| Edge | data_flow |
|------|-----------|
| phase_0 → loop_4 | max_lba |

### Phase inputs / outputs

| Phase | inputs | outputs |
|-------|--------|---------|
| phase_0 | — | max_lba |
| loop_4 | max_lba | — |

### Step-level data flow (produces / consumes)

| Step | produces | consumes |
|------|----------|----------|
| step_0_1 | — | — |
| step_0_2 | max_lba | — |
| step_0_3 | wb_supported | — |
| step_0_4 | max_alloc_units | — |
| step_0_5 | config_descriptor_data | — |
| step_0_6 | — | max_alloc_units, config_descriptor_data |
| step_1_1 | — | — |
| step_1_2 | — | — |
| step_1_3 | write_lba, write_length, write_pattern | max_lba |
| step_1_4 | — | write_lba, write_length, write_pattern |
| step_1_5 | reset_type | — |
| step_1_6 | — | reset_type |
| step_2_1 | write_lba, write_length, write_pattern | max_lba |
| step_2_2 | — | — |
| step_2_3 | — | write_lba, write_length, write_pattern |
| step_2_4 | reset_type | — |
| step_2_5 | — | — |
| step_3_3 | — | — |
| step_3_4 | reset_type | — |
| step_3_5 | — | reset_type |