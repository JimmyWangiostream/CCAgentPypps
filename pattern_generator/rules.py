"""Prescriptive rule pack — the "how to write a CORRECT UFS test" knowledge.

Unlike the descriptive wiki (what FFU/PSA *are*), these are imperative do/don't
rules with the trap shown, ported from hard-won code-review findings. They are
selected per-pattern by keyword and injected into the review prompt (review.py),
and can also be injected into unit prompts. This is the knowledge whose absence
let the first-gen pipeline ship Query-vs-Descriptor, log-instead-of-assert, and
re-randomised-LBA bugs (see the plan's RC2/RC4).

Pure data + stdlib; no third-party deps.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    keywords: tuple        # lower-cased substrings matched against pattern/step text
    body: str              # imperative do/don't, WRONG/CORRECT shown
    severity: str = "high"


RULES: list[Rule] = [
    Rule(
        id="assert-discipline",
        title="Every Expected / Verification Criterion must RAISE, not log",
        keywords=("expected", "verify", "confirm", "check", "assert", "status",
                  "good status", "success", "match"),
        body=(
            "A step's `expected` / `fail_condition` MUST be enforced with "
            "`raise api.PATTERN_ASSERT_*` (or `assert`). Logging the value is a "
            "SILENT FALSE POSITIVE — buggy firmware passes.\n"
            "  WRONG:   val = api.read_flag(...); logger.info(f'val={val}')\n"
            "  CORRECT: val = api.read_flag(...)\n"
            "           if val != expected:\n"
            "               raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(f'... got {val}')"
        ),
    ),
    Rule(
        id="query-vs-descriptor",
        title="QUERY READ ATTRIBUTE is NOT the same as reading a Descriptor field",
        keywords=("read attribute", "query", "dextended", "ufsfeatures",
                  "attribute", "writebooster support", "wb support", "feature support"),
        body=(
            "When the flow says QUERY READ ATTRIBUTE (opcode 0x03) of an attribute "
            "(e.g. dExtendedUFSFeaturesSupport), use the attribute API "
            "(`api.get_extended_ufs_features_support().u8_write_booster`). Do NOT "
            "substitute a Device Descriptor field — the protocol path IS the test.\n"
            "  WRONG:   api.get_device_descriptor().b84_write_booster_buffer_type\n"
            "  CORRECT: api.get_extended_ufs_features_support().u8_write_booster"
        ),
    ),
    Rule(
        id="volatile-flag-assert",
        title="WriteBooster / volatile flags must be re-read AND asserted after reset",
        keywords=("flag", "fwritebooster", "writebooster_en", "volatile", "reset",
                  "fdeviceinit", "flush", "read flag", "clear flag", "set flag"),
        body=(
            "All WriteBooster flags are VOLATILE (UFS Spec 6.3.4): after ANY reset "
            "(SSU/POR/Link) `fWriteBoosterEn` MUST be 0; `fDeviceInit` MUST be 1. "
            "Re-read and RAISE on mismatch — never assume a flag persists, never "
            "just log. After clear_flag, re-read and assert it is 0.\n"
            "  val = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)\n"
            "  if val != 0:\n"
            "      raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(f'WB must be 0 after reset, got {val}')"
        ),
    ),
    Rule(
        id="exception-naming",
        title="Use the exception type that matches the checked value's domain",
        keywords=("raise", "pattern_assert", "exception", "assert", "error"),
        body=(
            "Flag/attribute/status value mismatch -> `PATTERN_ASSERT_UNEXPECTED_CONDITION`. "
            "Data compare mismatch -> `PATTERN_ASSERT_RESPONSE_MISMATCH`. Feature not "
            "supported -> `UFS_NON_SUPPORT`. LUN/LBA-parameter checks ONLY -> the "
            "specific `..._WRONG_PARAMETER_LUN/LBA_*`. A flag value is NEVER a LUN/LBA "
            "issue.\n"
            "  WRONG:   raise api.PATTERN_ASSERT_UFS_WRONG_PARAMETER_LBA_SIZE_CHECK_ERROR  # for a flag\n"
            "  CORRECT: raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION"
        ),
    ),
    Rule(
        id="lba-pool-dedup",
        title="Write/Read-compare pairs must reuse the SAME lba & length (no re-random)",
        keywords=("random", "lba", "write", "read", "compare", "read compare",
                  "write(10)", "read(10)", "data match", "need_compare"),
        body=(
            "If a read-compare verifies a prior write, the read MUST use the lba/"
            "length the write produced — re-deriving with a fresh random() compares "
            "the wrong range (silent false pass/fail). Record on write, read back on "
            "read (e.g. share `self.write_record` / `self.write_lba` / `self.write_len`). "
            "For random LBAs across iterations, draw from a shuffled non-repeating pool, "
            "not raw random.randint (collisions corrupt the write-record lookup)."
        ),
    ),
    Rule(
        id="reset-helper",
        title="Factor reset into one helper; use the right SSU/POR semantics",
        keywords=("reset", "ssu", "start stop unit", "por", "power", "linkstartup",
                  "link startup", "hibernate"),
        body=(
            "Do NOT copy-paste the SSU/POR/Link reset block per step — factor a single "
            "`_perform_reset(reset_type)` helper and assert `fDeviceInit == 1` after it. "
            "Prefer `api.init_tester_to_unit_ready(resetmode=..., powerdown=...)` over "
            "hand-built START STOP UNIT. SSU semantics: power_condition=0x02/start=0 = "
            "power-down (a real cycle); a bare STOP is not a power cycle."
        ),
    ),
]


def select_rules(text: str, extra_terms: tuple = ()) -> list[Rule]:
    """Rules whose keywords appear in `text` (the pattern source + IR step text).

    `extra_terms` are additional already-lowercased tokens to match (e.g. IR cmd
    names). Order follows RULES (stable, deterministic)."""
    hay = text.lower()
    extra = tuple(t.lower() for t in extra_terms)
    out: list[Rule] = []
    for r in RULES:
        if any(k in hay for k in r.keywords) or any(
                any(k in e for k in r.keywords) for e in extra):
            out.append(r)
    return out


def format_rules(rules: list[Rule]) -> str:
    """Render selected rules as a prescriptive block for prompt injection."""
    if not rules:
        return "(no domain rules matched)"
    blocks = []
    for r in rules:
        blocks.append(f"### [{r.severity.upper()}] {r.title}  (rule: {r.id})\n{r.body}")
    return "\n\n".join(blocks)
