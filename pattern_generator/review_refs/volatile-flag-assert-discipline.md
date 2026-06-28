# WriteBooster Volatile Flag Assert Discipline

Session reference: PF010_0310_WriteBooster_SSU_Rst code review (2026-06-24)

## Core Rule

**UFS Spec 6.3.4 mandates that all WriteBooster flags are VOLATILE.** After ANY reset (SSU, POR, Link Startup), `fWriteBoosterEn` MUST equal 0. Test code MUST `raise api.PATTERN_ASSERT_*` when verifying this — logging or no-op = **silent false positive**.

## Pattern: Post-Reset Flag Verification

### WRONG (produces false positives)
```python
# Only logs the value — firmware bug goes undetected
val = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
logger.info(f"fWriteBoosterEn after reset = {val}")
```

### CORRECT (asserts the expectation)
```python
val = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
if val != 0:
    raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
        f"fWriteBoosterEn must be 0 after reset, got {val}"
    )
```

### WRONG (same issue with clear_flag)
```python
# Only warns — test silently passes on buggy firmware
api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
logger.warning(f"WB flag not cleared: {api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)}")
```

### CORRECT
```python
api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
val = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
if val != 0:
    raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
        f"fWriteBoosterEn must be 0 after clear, got {val}"
    )
```

## Volatile Flags List

| Flag | IDN | Reset Behavior | Exception to Raise |
|------|-----|----------------|-------------------|
| fWriteBoosterEn | 0x0E | MUST be 0 after any reset | PATTERN_ASSERT_UNEXPECTED_CONDITION |
| fDeviceInit | — | MUST be 1 after any reset | PATTERN_ASSERT_UNEXPECTED_CONDITION |
| fWriteBoosterBufferFlushEn | 0x0B | Volatile — check per spec | PATTERN_ASSERT_UNEXPECTED_CONDITION |
| fWriteBoosterBufferFlushDuringHibernate | 0x0C | Volatile — check per spec | PATTERN_ASSERT_UNEXPECTED_CONDITION |

## False Positive Risk

| Scenario | What happens | Impact |
|----------|-------------|--------|
| Flag read after reset without assert | Buggy firmware keeps flag=1, test passes | **False Positive** — firmware bug undetected |
| Flag clear without re-read+assert | Clear fails silently, test proceeds with WB enabled | **False Positive** — test conditions wrong |
| Wrong reset type used (SSU vs HW_RESET) | Different firmware recovery paths | **Unreliable** — test may pass on one path, fail on another |

## Common Bug Pattern

From PF010_0310 review: the comment "Shared buffer preserves state" (implying fWriteBoosterEn might stay 1 after reset on shared buffers) is **incorrect per UFS Spec 6.3.4**. All WB flags are volatile regardless of buffer type. Never assume any WB flag persists across resets.

## New Patterns (PF010_0310 session, 2026-06-24)

### Bug Pattern: Phase 2 WB disable re-check before write
Before burning in with WB disabled, re-read the flag first, then clear if needed, then re-verify clear succeeded. Do NOT assume the flag is already 0 just because the previous iteration ended with a reset. Code pattern at `_loop4_step_2_1`:
```python
wb_en = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
if wb_en != 0:
    api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
    wb_en_after = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
    if wb_en_after != 0:
        raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(...)
```
This "read → conditional-clear → re-read" pattern is the correct way to ensure WB is off before proceeding to WB-disabled write phase.

### Bug Pattern: write/read length mismatch in burn-in W/R pairs
When burn-in does `random_write(..., need_compare=False)` then `random_read(..., need_compare=True)`, if each call generates an INDEPENDENT `random.randint(1, 256)` for `length`, the read length may differ from the write length → `need_compare=True` verifies wrong data range → silent false pass or false fail.
- FIX: store write length (e.g., `self._last_write_length`) during write, reuse it during read.

### Bug Pattern: write/read length mismatch in burn-in W/R pairs
When burn-in does `random_write` then `random_read` for data integrity check, each call generates an INDEPENDENT `random.randint(1, 256)` for `length`. The read length may differ from the write length → `need_compare=True` verifies wrong data range → silent false pass or false fail.
- FIX: Store the write length (e.g., `self._last_write_length`) during write, reuse it during read.

### Bug Pattern: flush status single-shot check (2026-06-25)
Setting `fWriteBoosterBufferFlushEn` triggers device-side NVM flush. The `WRITEBOOSTER_BUFFER_FLUSH_STATUS` attribute reads 0=Idle, 1=InProgress, 2=Complete. A single `sleep(0.1) + read` may hit InProgress(1) and false fail.
- FIX: Implement `_wait_for_flush_complete(timeout_ms=5000)` with 10ms poll loop. Return immediately on status==2, raise on timeout.
- Also see `references/flush-polling-pattern.md`.

### Bug Pattern: exception type mismatch for flag value checks (2026-06-25)
Using `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LUN_CHECK_ERROR` or `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LBA_SIZE_CHECK_ERROR` for flag value verification (e.g., fWriteBoosterEn, flush status) produces wrong failure classification. These exceptions are for LUN/LBA parameter checks only.
- FIX: Always use `PATTERN_ASSERT_UNEXPECTED_CONDITION` for flag value assertions and attribute value checks. Use `PATTERN_ASSERT_RESPONSE_MISMATCH` for data comparison failures. Use `UFS_NON_SUPPORT` for early feature-not-supported exits.
- Also see `references/exception-naming-convention.md`.

### Bug Pattern: missing post-reset flag verification for flush flags (2026-06-25)
Phase 3 does SET → wait → CLEAR → RESET → END but never verifies that `fWriteBoosterBufferFlushEn` and `fWriteBoosterBufferFlushDuringHibernate` are 0 after reset. UFS spec says flush flags are volatile.
- FIX: Add `_loop4_step_3_5` after each Phase 3 reset. Read both flush flags and raise `PATTERN_ASSERT_UNEXPECTED_CONDITION` if either != 0.
