# PF010_0310 IR Debug Report

**Pattern**: PF010_0310_Write-Booster-SSU-Rst-Normalized-TestFlow
**Pattern ID**: PF010_0310

---

## Stage 1 — Rule-based 解析結果

| Phase | Type | Steps | Loop Info |
|-------|------|-------|-----------|
| phase_0 | sequential | 2 |  |
| loop_1 | loop | 13 | until: None |

**Fail Condition 識別**:


---

## Stage 2 — Wiki 查詢結果

### phase_0 — Pre-condition: Write Booster Buffer Configuration

| 參考 Wiki Chapter | 標題 |
|------------------|------|
| `concepts/ffu.md` | FFU — Field Firmware Update |
| `concepts/thin-provisioning.md` | Thin Provisioning and UNMAP |
| `entities/device-descriptor.md` | Device Descriptor (IDN 00h) |
| `entities/unit-descriptor.md` | Unit Descriptor (IDN 02h) |
| `entities/configuration-descriptor.md` | Configuration Descriptor (IDN 01h) |

### loop_1 — Burn-in Loop

| 參考 Wiki Chapter | 標題 |
|------------------|------|
| `concepts/refresh.md` | Refresh Operation |
| `concepts/ffu.md` | FFU — Field Firmware Update |
| `concepts/thin-provisioning.md` | Thin Provisioning and UNMAP |
| `concepts/background-operations.md` | Background Operations (BKOPS) |
| `concepts/pattern-rpmb.md` | Pattern: RPMB Implementation Guide |
| `entities/flags.md` | UFS Flags |
| `entities/attributes.md` | UFS Attributes |
| `entities/scsi-commands.md` | UFS SCSI Commands (UCS) |
| `entities/unit-descriptor.md` | Unit Descriptor (IDN 02h) |
| `entities/write-booster.md` | Write Booster |
| `entities/inhibition-timeout.md` | Inhibition Timeout |
| `entities/device-descriptor.md` | Device Descriptor (IDN 00h) |

---

## Stage 3 — LLM 標注決策

### 資料流 (data_flow per edge)

| Edge | data_flow |
|------|-----------|
| phase_0 → loop_1 | max_capacity_lun, max_alloc_units |

### Phase inputs / outputs

| Phase | inputs | outputs |
|-------|--------|---------|
| phase_0 | — | max_capacity_lun, wb_support, config_descriptor_data, max_alloc_units |
| loop_1 | max_capacity_lun, max_alloc_units | — |

### Step-level data flow (produces / consumes)

| Step | produces | consumes |
|------|----------|----------|
| step_0_1 | max_capacity_lun, wb_support | — |
| step_0_2 | config_descriptor_data, max_alloc_units | max_capacity_lun, wb_support |
| step_1_1 | — | max_capacity_lun |
| step_1_2 | write_record_p1 | max_capacity_lun |
| step_1_3 | — | write_record_p1 |
| step_1_4 | — | — |
| step_2_1 | — | max_capacity_lun |
| step_2_2 | write_record_p2 | max_capacity_lun |
| step_2_3 | — | write_record_p2 |
| step_2_4 | — | — |
| step_3_1 | — | max_capacity_lun |
| step_3_2 | — | — |
| step_3_3 | — | — |
| step_3_4 | — | max_capacity_lun |
| step_3_5 | — | — |