# PF010_0310 — Full Defect-to-Fix Mapping (Fixed v2, 2026-06-25)

Condensed knowledge bank from the two-pass review of `PSW_F_P3_PF010_0310_WriteBooster_SSU_Rst`.

## Defect Matrix (15 issues, all FIXED)

| # | Severity | Issue | Before (Wrong) | After (Fixed) |
|---|----------|-------|----------------|---------------|
| CRIT-1 | Critical | Step 0.3 Protocol Path | `api.get_device_descriptor().b84_write_booster_buffer_type` (Opcode 0x02) | `api.get_extended_ufs_features_support().u8_write_booster` (Opcode 0x03) |
| CRIT-2 | Critical | Step 3.2 Flush Polling | `sleep(0.1)` + single read | 5s timeout, 10ms poll loop, return on status==2 |
| CRIT-3 | Critical | Step 3.5 Post-Reset Verification | Missing entirely | Read both flush flags, assert == 0, raise on non-zero |
| HIGH-1 | High | Step 1.2 Exception Type | `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LUN_CHECK_ERROR` | `PATTERN_ASSERT_UNEXPECTED_CONDITION` |
| HIGH-2 | High | Step 1.3/1.4 Length Mismatch | Independent `random.randint(1,256)` | `self._last_write_length` stored in write, reused in read |
| HIGH-3 | High | Step 1.5 Reset Determinism | `random.choice(['SSU','POR','LINKSTARTUP'])` | `self._reset_types[loop_idx % N]` deterministic rotation |
| HIGH-4 | High | Step 1.5 SSU Manual Construction | `StartStopUnit()` with hardcoded params | `idv.init_tester_to_unit_ready(resetmode=HW_RESET, powerdown=True)` |
| HIGH-5 | High | Step 2.3 Length Mismatch | Same as HIGH-2 | Same fix applied to Phase 2 |
| HIGH-6 | High | Step 2.4 Reset Issues | Same as HIGH-3/4 | Same fix applied to Phase 2 |
| HIGH-7 | High | Step 3.4 TC Flow Types | Generic SSU/POR/LINKSTARTUP | `['POR_delay', 'SSU+Hibernate+POR']` per TC flow |
| HIGH-8 | High | Step 3.2 Exception Type | `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LBA_SIZE_CHECK_ERROR` | `PATTERN_ASSERT_UNEXPECTED_CONDITION` |
| M-1 | Medium | write_record Type | `self.write_record: list = []` | `api.get_empty_write_record()` framework factory |
| M-2 | Medium | Config Desc Index | `push_write_config(desc, index=0)` | `push_write_config(desc, index=self.config_desc_index)` |
| M-3 | Medium | Phase 3 Branching | Always SET WRITEBOOSTER_BUFFER_FLUSH_EN | `loop_idx % 2` alternates between both flush flags |
| M-4 | Medium | Phase 3 TC Flow Types | Same as HIGH-7 | Same as HIGH-7 |
| L-1 | Low | Length Range | `randint(1, 256)` | `randint(16, 1024)` via class attrs |
| L-2 | Low | Initial Sleep | Standalone `sleep(0.1)` before polling | Merged into unified polling loop |
| L-3 | Low | post_process Empty | `# TODO` | Reverts all WB flags to safe defaults |

## Key Patterns for Future WB+Reset Tests

1. **Protocol path matters**: Query READ ATTRIBUTE (0x03) != Query READ DESCRIPTOR (0x02). Never substitute.
2. **Flush status MUST poll**: Device NVM flush latency varies. Single-shot check = flaky test.
3. **All WB flags volatile**: fWriteBoosterEn, fWriteBoosterBufferFlushEn, fWriteBoosterBufferFlushDuringHibernate — all MUST be 0 after any reset.
4. **fDeviceInit == 1**: Required after ALL reset paths. Check in a shared `_do_reset()` helper.
5. **Framework API for reset**: `init_tester_to_unit_ready()` over manual StartStopUnit. Avoids wrong power_condition semantics.
6. **Deterministic rotation**: `reset_types[loop_idx % N]` over `random.choice()` for burn-in coverage.
7. **Write-read length linkage**: Store length during write step, reuse during read step.
8. **write_record factory**: Use `api.get_empty_write_record()`, NOT `[]`.
9. **Exception domain discipline**: Flag/attribute checks → `PATTERN_ASSERT_UNEXPECTED_CONDITION`. Never LUN/LBA exceptions.
