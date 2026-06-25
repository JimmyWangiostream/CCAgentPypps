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
| `entities/attributes.md` | UFS Attributes |
| `entities/configuration-descriptor.md` | Configuration Descriptor (IDN 01h) |
| `entities/device-descriptor.md` | Device Descriptor (IDN 00h) |
| `entities/device-health-descriptor.md` | Device Health Descriptor (IDN 09h) |
| `entities/flags.md` | UFS Flags |
| `entities/inhibition-timeout.md` | Inhibition Timeout |
| `entities/lun.md` | LUN — Logical Unit Number |
| `entities/power-modes.md` | UFS Power Modes |
| `entities/psa-state.md` | PSA State |
| `entities/rpmb.md` | RPMB — Replay Protected Memory Block |
| `entities/scsi-commands.md` | UFS SCSI Commands (UCS) |
| `entities/thermal-protection-mode.md` | Thermal Protection Mode |
| `entities/unit-descriptor.md` | Unit Descriptor (IDN 02h) |
| `entities/upiu.md` | UPIU Types |
| `entities/write-booster.md` | Write Booster |
| `concepts/background-operations.md` | Background Operations (BKOPS) |
| `concepts/exception-events.md` | Exception Events |
| `concepts/ffu.md` | FFU — Field Firmware Update |
| `concepts/pattern-apl-rebuild.md` | Pattern: APL System Rebuild Implementation Guide |
| `concepts/pattern-health-report.md` | Pattern: Health Report Implementation Guide |
| `concepts/pattern-inhibition-time.md` | Pattern: Inhibition Time Implementation Guide |
| `concepts/pattern-psa.md` | Pattern: PSA (Pre-Soldering Authentication) Implementation Guide |
| `concepts/pattern-rpmb.md` | Pattern: RPMB Implementation Guide |
| `concepts/pattern-thermal-protection.md` | Pattern: Thermal Protection Implementation Guide |
| `concepts/pattern-wear-leveling.md` | Pattern: Wear Leveling Implementation Guide |
| `concepts/power-management.md` | Power Management |
| `concepts/psa.md` | PSA — Production State Awareness |
| `concepts/refresh.md` | Refresh Operation |
| `concepts/shipping-mode.md` | Shipping Mode |
| `concepts/thin-provisioning.md` | Thin Provisioning and UNMAP |
| `concepts/write-booster.md` | WriteBooster |

### loop_4 — Burn-in

| 參考 Wiki Chapter | 標題 |
|------------------|------|
| `entities/attributes.md` | UFS Attributes |
| `entities/configuration-descriptor.md` | Configuration Descriptor (IDN 01h) |
| `entities/device-descriptor.md` | Device Descriptor (IDN 00h) |
| `entities/device-health-descriptor.md` | Device Health Descriptor (IDN 09h) |
| `entities/flags.md` | UFS Flags |
| `entities/inhibition-timeout.md` | Inhibition Timeout |
| `entities/lun.md` | LUN — Logical Unit Number |
| `entities/psa-state.md` | PSA State |
| `entities/rpmb.md` | RPMB — Replay Protected Memory Block |
| `entities/scsi-commands.md` | UFS SCSI Commands (UCS) |
| `entities/thermal-protection-mode.md` | Thermal Protection Mode |
| `entities/unit-descriptor.md` | Unit Descriptor (IDN 02h) |
| `entities/upiu.md` | UPIU Types |
| `entities/write-booster.md` | Write Booster |
| `concepts/background-operations.md` | Background Operations (BKOPS) |
| `concepts/exception-events.md` | Exception Events |
| `concepts/ffu.md` | FFU — Field Firmware Update |
| `concepts/pattern-apl-rebuild.md` | Pattern: APL System Rebuild Implementation Guide |
| `concepts/pattern-inhibition-time.md` | Pattern: Inhibition Time Implementation Guide |
| `concepts/pattern-psa.md` | Pattern: PSA (Pre-Soldering Authentication) Implementation Guide |
| `concepts/pattern-rpmb.md` | Pattern: RPMB Implementation Guide |
| `concepts/pattern-thermal-protection.md` | Pattern: Thermal Protection Implementation Guide |
| `concepts/pattern-wear-leveling.md` | Pattern: Wear Leveling Implementation Guide |
| `concepts/power-management.md` | Power Management |
| `concepts/psa.md` | PSA — Production State Awareness |
| `concepts/refresh.md` | Refresh Operation |
| `concepts/shipping-mode.md` | Shipping Mode |
| `concepts/write-booster.md` | WriteBooster |

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