# PF002_0098 IR Debug Report

**Pattern**: PF002_0098_Boot_Stress_Test-Normalized-TestFlow
**Pattern ID**: PF002_0098

---

## Stage 1 — Rule-based 解析結果

| Phase | Type | Steps | Loop Info |
|-------|------|-------|-----------|
| loop_0 | loop | 6 | until: None |

**Fail Condition 識別**:


---

## Stage 2 — Wiki 查詢結果

### loop_0 — Burn-in Loop

| 參考 Wiki Chapter | 標題 |
|------------------|------|
| `concepts/ffu.md` | FFU — Field Firmware Update |
| `concepts/refresh.md` | Refresh Operation |
| `concepts/thin-provisioning.md` | Thin Provisioning and UNMAP |
| `concepts/exception-events.md` | Exception Events |
| `concepts/pattern-rpmb.md` | Pattern: RPMB Implementation Guide |
| `entities/unit-descriptor.md` | Unit Descriptor (IDN 02h) |
| `entities/attributes.md` | UFS Attributes |
| `entities/flags.md` | UFS Flags |
| `entities/scsi-commands.md` | UFS SCSI Commands (UCS) |
| `entities/configuration-descriptor.md` | Configuration Descriptor (IDN 01h) |
| `entities/write-booster.md` | Write Booster |
| `entities/inhibition-timeout.md` | Inhibition Timeout |

---

## Stage 3 — LLM 標注決策

### 資料流 (data_flow per edge)

| Edge | data_flow |
|------|-----------|
| phase_0 → phase_1 | boot_lun_id, write_pattern, written_lba_start, written_transfer_length |
| phase_1 → phase_2 | boot_lun_id, write_pattern, written_lba_start, written_transfer_length |

### Phase inputs / outputs

| Phase | inputs | outputs |
|-------|--------|---------|
| loop_0 | — | — |

### Step-level data flow (produces / consumes)

| Step | produces | consumes |
|------|----------|----------|
| step_0_1 | — | — |
| step_0_2 | — | — |
| step_0_3 | — | — |
| step_1_1 | — | — |
| step_2_1 | — | — |
| step_2_2 | — | — |