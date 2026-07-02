"""Procedure idioms — intents that are a MULTI-STEP PROCEDURE, not a single API call.

The name-similarity trap has a second face: when the correct implementation is a procedure
(enumerate → read → pick) and NO single accessor implements it, the model reaches for the
closest-named single API and fakes the rest. The real bug: intent "MaxCapacity Enabled LUN"
→ the model wrote `lun_count = api.get_max_number_of_lun(); test_lun = lun_count - 1` — but
`get_max_number_of_lun()` returns the LUN *count*, not a capacity, and `-1` is a fabrication.
`api_grounding` can't catch it (the symbol is real, the signature fits, no bad field).

This registry names such procedures and injects an AUTHORITATIVE guard: do NOT substitute a
name-similar single call; ground each real step; and if you can't ground the field, emit a
fail-loud `TODO human-confirm` instead of fabricating. It anchors only VERIFIED symbols
(e.g. `api.get_unit_descriptor(unit_index)`, the `b3_lu_enable` field) and defers the exact
capacity field to the struct-field FEED rather than hard-coding a possibly-wrong name.

Same shape as semantic_checks.CANONICAL_IDIOMS: {id: (trigger_tokens, guidance)}. A guard
fires when ALL its trigger tokens appear in the (data-flow-enriched) unit query.
"""
from __future__ import annotations

PROCEDURE_IDIOMS: dict = {
    "max_capacity_lun": (
        ("lun", "capacity"),
        "Selecting the MaxCapacity Enabled LUN is a PROCEDURE, not a single API. Do NOT "
        "substitute a name-similar single call — e.g. `api.get_max_number_of_lun()` returns "
        "the LUN COUNT, not a capacity, and `count - 1` is a fabrication. Instead: enumerate "
        "the enabled Normal LUNs (Unit Descriptor `b3_lu_enable`), read each via "
        "`api.get_unit_descriptor(unit_index)`, and pick the LUN whose allocated-size field "
        "(see the injected Unit Descriptor fields) is largest. If you cannot ground the exact "
        "field, emit `logger.warning(\"TODO human-confirm: max-capacity LUN field\")` — never "
        "fabricate a value.",
    ),
}


def match_procedures(query: str) -> list:
    """Guidance strings whose every trigger token appears in `query` (possibly empty)."""
    q = (query or "").lower()
    return [guidance for _pid, (triggers, guidance) in PROCEDURE_IDIOMS.items()
            if all(t in q for t in triggers)]
