# WriteBooster + SSU Reset Review — Extracted Checkpoints

Session reference: PF010_0310_WriteBooster_SSU_Rst.py review (2026-06-24)

## Source Files Analyzed
- `device_desc_sample.md` — Device Descriptor & UFS Features Support enumeration
- `config_sample.md` — Configuration Descriptor Write & Read-Back Verification
- `program_fail_api.md` — LUN Configuration & EM1 Allocation Verification
- `pattern_template.md` — Test Framework Init & Execution Logic
- `response_sample.md` — Protocol Command Sequence & Data Integrity
- `PSW_F_P3_CustomVU_0018_Unlock_LU_Attribute_Configuration_Test.md` — Config Descriptor Lock Mechanism

## Core Checkpoints for WriteBooster + SSU/Reset Tests

### CP-1: WriteBooster Support Detection
- Verify `api.get_ufs_features_support().u8_write_booster == 1`
- Also check `api.get_extended_write_booster_support()` for u0/u1/u2 bits
- Raise `api.UFS_NON_SUPPORT` if WB not supported
- Field mapping: DevDesc `b84_write_booster_buffer_type` + `l85_num_shared_write_booster_buffer_alloc_units`

### CP-2: Config Descriptor WB Configuration
- `b17_write_booster_buffer_type = 0x01` (Shared) at header offset 84
- `l18_num_shared_write_booster_buffer_alloc_units` at per-unit offset 72 (NOT global offset 85)
- Use `api.ConfigDescriptor410` + `cmd.set_desc()`, NOT manual bytearray
- Read-verify after write: `ReadDescriptor` → compare header & unit fields

### CP-3: fWriteBoosterEn is VOLATILE
- Per UFS Spec 6.3.4, MUST be 0 after ANY reset (SSU/POR/Link Startup)
- Code MUST assert `wb_flag == 0` post-reset; logging-only = FALSE POSITIVE
- This is the #1 trap: reading without asserting silently passes buggy firmware

### CP-4: fWriteBoosterEn Clear Verification
- After `api.clear_flag(WRITEBOOSTER_EN)`, MUST assert == 0
- Warning-only = FALSE POSITIVE (identical trap to CP-3)
- Exception: `api.PATTERN_ASSERT_UNEXPECTED_CONDITION`

### CP-5: fDeviceInit Verification After Every Reset
- MUST be == 1 after ALL reset types (SSU, POR, Link Startup)
- Consistent severity across all reset paths — no warning-vs-assert inconsistency
- Use `api.read_flag(idn=api.FlagIDN.DEVICE_INIT)`

### CP-6: Reset API Standardization
- PREFERRED: `api.init_tester_to_unit_ready(resetmode='HW_RESET', powerdown=True/False)`
- NOT manual `StartStopUnit` cmd construction (risk: wrong power_condition semantics)
- SSU: powerdown=True = full power cycle; powerdown=False = no power cycle
- POR via Dcmd5: `api.Dcmd5Reset(0x02)` (0x01 = RESET_N link startup)

### CP-7: Data Integrity Post-Write
- Prefer `api.read_compare()` with `api.CompareMethod.HW_COMPARE`
- Manual `write_records` lookup by (lun, lba) has race condition on duplicate LBA
- If using manual read-back: `stored_data` must match `read_data` via assert, not log

### CP-8: Initialization Safety
- `self.write_records` MUST be initialized in `pre_process()` before use
- All class attributes used across steps must have defaults in `pre_process()`
- No implicit None → value usage without type guard

### CP-9: Burn-in Parameterization
- Iteration counts should be class attributes, not hardcoded inside loop methods
- LBA selection should avoid reuse across iterations (pool or increment strategy)

### CP-10: Flush Flag Behavior
- `fWriteBoosterBufferFlushEn` and `fWriteBoosterBufferFlushDuringHibernate` are volatile (UFS Spec 6.3.4)
- 50/50 deterministic branching (loop_idx % 2) between the two per iteration
- BOTH flags MUST be asserted == 0 after ANY reset (SSU/POR/Link/Hibernate). Non-zero = `PATTERN_ASSERT_UNEXPECTED_CONDITION`.
- TC flow Step 3.4 may define additional reset types (e.g., `POR_delay`, `SSU+Hibernate+POR`); implement all variants.
- See `references/writebooster-ssu-review-2026-06-25.md` for full defect-to-fix mapping from PF010_0310 Fixed v2 pass.
