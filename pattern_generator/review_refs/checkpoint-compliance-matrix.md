# LLM-Wiki Checkpoint Compliance Matrix Pattern

Session reference: PF010_0310_WriteBooster_SSU_Rst code review (2026-06-24)

## Core Concept

When the user requests UFS test script review with LLM-Wiki auto-retrieval, produce a **structured compliance matrix** mapping each wiki spec checkpoint to the corresponding code line. This makes coverage gaps immediately visible.

## Review Workflow (7-Step)

### Step 1: Identify Keywords from Target Script
Scan the script for feature keywords:
- WriteBooster → `write.boost`, `wb_`, `fwritebooster`, `writebooster_en`
- SSU/Reset → `ssu`, `reset`, `start.stop`, `power.?loop`
- Descriptor → `config_desc`, `device_desc`, `descriptor`, `lun`
- Flag → `flag`, `set_flag`, `read_flag`, `clear_flag`
- Flush → `flush`, `buffer_flush`

### Step 2: Retrieve Relevant Wiki Docs
Grep `docs/test_plans/*.md` for the same keywords. Load top 3-5 most relevant files.

### Step 3: Extract Verification Criteria (VC) and Test Case (TC) Checkpoints
From each loaded doc, extract:
- **VC sections** — behavioral guarantees (what the firmware MUST do)
- **TC Checkpoints** — enumerated numbered steps with expected results
- **Exception naming conventions** — which `api.PATTERN_ASSERT_*` for which scenario
- **Flag/parameter naming** — e.g., `fWriteBoosterEn`, `fDeviceInit`

### Step 4: Map Code Lines to Checkpoints
Build a compliance matrix:
```
| LLM-Wiki Checkpoint | Script Line(s) | Status |
|---------------------|----------------|--------|
| DevDesc b84 != 0     | unit_03.py     | ✅     |
| Config Write+Readback| unit_06.py     | ✅     |
| WB En after reset == 0| unit_12.py    | ✅     |
```

### Step 5: Check for Missing Asserts
Every TC checkpoint with "expected result = X must equal Y" requires `raise api.PATTERN_ASSERT_*`:
- Value mismatch → `api.PATTERN_ASSERT_UNEXPECTED_CONDITION`
- Response code wrong → `api.PATTERN_ASSERT_RESPONSE_MISMATCH`
- Feature not supported → `api.UFS_NON_SUPPORT`
- **Warning-only on expected-value check = FALSE POSITIVE**

### Step 6: Verify Domain-Specific Pitfalls
Cross-check against pitfalls in skill references:
- Post-reset flag asserts present? (no log-only)
- fDeviceInit == 1 after every reset path?
- SSU power_condition semantics correct?
- Config Descriptor write uses standard API?
- LBA pool avoids collision?

### Step 7: Report with Severity Prioritization
CRITICAL > HIGH > MEDIUM > LOW. CRITICAL items that block execution (e.g., stepN scope error) must be listed first.

## Example Output Format

```
# Code Review: <script_name>.py

## LLM-Wiki Related Files Retrieved
| # | File | Relevance |
|---|------|-----------|
| 1 | config_sample.md | Config Descriptor b17/l18 write+readback |
| 2 | device_desc_sample.md | DevDesc b84 WB type check |

## Checkpoint Compliance Matrix
| LLM-Wiki Checkpoint | Script Line | Compliant |
|---------------------|-------------|-----------|
| ...                 | ...         | ✅/⚠️/❌   |

## Findings by Severity
### 🔴 CRITICAL
#N. Line X-Y: <description>

### 🟠 HIGH
...

### 🟡 MEDIUM
...

### ⚪ LOW
...
```
