# Exception Naming Convention for UFS Test Patterns

Session reference: PF010_0310_WriteBooster_SSU_Rst code review (2026-06-24)

## Rule

Exception names MUST match the domain of the value being checked. Using the wrong exception type produces misleading logs, wrong Jira correlation, and confusing automated reports.

## Quick Reference Table

| Scenario | Correct Exception | Wrong Examples |
|----------|------------------|----------------|
| Flag value mismatch (fWriteBoosterEn != expected, fDeviceInit != expected) | `api.PATTERN_ASSERT_UNEXPECTED_CONDITION` | `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LUN_CHECK_ERROR` |
| Flush status not in valid range (not 0/1/2) | `api.PATTERN_ASSERT_UNEXPECTED_CONDITION` | `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LBA_SIZE_CHECK_ERROR` |
| Flush status not Complete(2) after setting flag | `api.PATTERN_ASSERT_UNEXPECTED_CONDITION` | `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LBA_SIZE_CHECK_ERROR` |
| Data comparison mismatch (read != written data) | `api.PATTERN_ASSERT_RESPONSE_MISMATCH` | `PATTERN_ASSERT_UNEXPECTED_CONDITION` |
| LUN out of range / invalid LUN parameter | `api.PATTERN_ASSERT_UFS_WRONG_PARAMETER_LUN_CHECK_ERROR` | `PATTERN_ASSERT_UNEXPECTED_CONDITION` |
| LBA size out of range / invalid LBA parameter | `api.PATTERN_ASSERT_UFS_WRONG_PARAMETER_LBA_SIZE_CHECK_ERROR` | `PATTERN_ASSERT_UNEXPECTED_CONDITION` |
| Feature not supported by device | `api.UFS_NON_SUPPORT` | any other |
| Expected response code wrong | `api.PATTERN_ASSERT_RESPONSE_MISMATCH` | `PATTERN_ASSERT_UNEXPECTED_CONDITION` |
| Device descriptor check failure | `api.PATTERN_ASSERT_UNEXPECTED_CONDITION` | (various wrong types) |
| Config Descriptor write-back mismatch | `api.PATTERN_ASSERT_UNEXPECTED_CONDITION` | `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LBA_SIZE_CHECK_ERROR` |

## Common Mistakes Found

1. **LUN check exception for flag value**: Used `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LUN_CHECK_ERROR` when verifying `fWriteBoosterEn == 1`. WRONG — this exception is for LUN parameter validation only.

2. **LBA size exception for flush status**: Used `PATTERN_ASSERT_UFS_WRONG_PARAMETER_LBA_SIZE_CHECK_ERROR` when verifying flush status is 2. WRONG — this exception is for LBA size validation only.

3. **General rule**: If the checked value is NOT a LUN index or LBA size, and it's not a response code, use `PATTERN_ASSERT_UNEXPECTED_CONDITION` as the safe default.

## Verification

When reviewing any test script:
1. Find every `raise api.PATTERN_ASSERT_*`
2. Ask: "What is being checked?"
3. If it's a flag value, attribute value, or status code → must be `UNEXPECTED_CONDITION` or `RESPONSE_MISMATCH`
4. If it's specifically a LUN or LBA parameter → the specific parameter exception is OK
5. Flag mismatches are NEVER LUN or LBA issues
