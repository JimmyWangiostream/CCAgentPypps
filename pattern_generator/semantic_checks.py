"""Deterministic SEMANTIC checks — the layer api_grounding deliberately skips.

`api_grounding` proves a symbol/signature is REAL; it cannot judge MEANING — it
intentionally skips attribute access (`x.u0_ffu`) and value/logic checks (see its
docstring). A handful of high-value, machine-decidable DOMAIN rules live here
instead of in the advisory, BM25-selected `review_refs` prose — so they are
ENFORCED by the gate, not merely suggested to a review LLM that may ignore them.

Findings use the SAME issue-dict shape as `api_grounding.check_api_calls`
(`{alias, symbol, kind, detail, line, suggestion?}`), so `format_issues` and the
gate (validator `semantic` key, driver `_GATE_KEYS`) handle them with no new
plumbing. This is the deterministic sibling to api_grounding promised in CLAUDE.md
("two complementary deterministic layers"), extended from symbol reality to a few
semantic invariants.

Philosophy mirrors api_grounding: conservative, context-gated, intra-function
only, prefer false negatives over false positives. Each rule pairs with a
canonical-idiom FEED entry (`CANONICAL_IDIOMS` / `canonical_facts`) injected at
generation time, so PREVENT and CATCH share one source of truth.
"""
from __future__ import annotations

import ast
import re

# --------------------------------------------------------------------------- #
# Canonical correct idioms — injected at generation (PREVENT, via canonical_facts)
# and cited in findings (CATCH). One source of truth for both sides.
# Each entry: rule_id -> (trigger_tokens, imperative_fact). The fact is injected
# when EVERY trigger token appears (substring) in the unit's generation query.
# --------------------------------------------------------------------------- #
CANONICAL_IDIOMS: dict = {
    "wb_support_path": (
        ("write booster", "support"),
        "WriteBooster support MUST be read via "
        "api.get_extended_ufs_features_support().u8_write_booster — NOT u0_ffu (that is "
        "the FFU bit) and NOT a Device Descriptor buffer-type field.",
    ),
    # NOTE: a `device_init_polarity` idiom is intentionally absent — the correct
    # fDeviceInit readiness polarity is DISPUTED across the project's own artifacts
    # (TC flow says ready == 0; the IR/enrich/generated outputs/review_refs CP-5 all say
    # == 1). We do NOT inject or enforce a polarity until a domain owner confirms it.
    # See _device_init_polarity below (dormant).
}


def canonical_facts(query: str) -> list:
    """Imperative idiom facts whose every trigger token is present in `query`.

    Used by the generation FEED path (prepare._unit_api_facts) so the model copies
    the right form instead of guessing — the prevent half of these rules."""
    q = (query or "").lower()
    return [fact for _rid, (triggers, fact) in CANONICAL_IDIOMS.items()
            if all(t in q for t in triggers)]


# --------------------------------------------------------------------------- #
# IR-level protocol-path check (Lever #4) — flag a STEP whose stated protocol path
# CONTRADICTS a canonical idiom, BEFORE generation. Report-only: a step may
# legitimately exercise the other path, and deterministically rewriting a TC's
# protocol path is the kind of guess this project refuses (cf. device_init
# dormancy). One source of truth: the same idioms PREVENT (canonical_facts),
# CATCH (check_semantics), and now FLAG-UPSTREAM here. Seed rule = wb_support_path.
# Add a rule = add a matcher fn to IR_PATH_RULES + a test.
# --------------------------------------------------------------------------- #

def _step_text(step: dict) -> str:
    """Lower-cased step text for path detection (name + protocol fields + raw)."""
    return " ".join(str(step.get(k) or "")
                    for k in ("name", "ufs_query", "idn", "raw_content")).lower()


def _ir_wb_support_path(step: dict):
    """A WriteBooster *support/capability* check grounded to the Device Descriptor
    path instead of READ ATTRIBUTE dExtendedUFSFeaturesSupport. Support tokens are
    bilingual (TCs mix the English feature name with Chinese prose)."""
    text = _step_text(step)
    if "write booster" not in text:
        return None
    if not any(t in text for t in ("support", "capability", "支援", "能力")):
        return None  # a config/enable step, not a support check
    wrong = any(t in text for t in ("device descriptor", "read descriptor"))
    right = any(t in text for t in ("dextendedufsfeaturessupport", "read attribute",
                                    "extended ufs features",
                                    "get_extended_ufs_features_support"))
    if wrong and not right:
        return {
            "alias": "ir", "symbol": "wb_support_path",
            "kind": "ir_wrong_protocol_path", "step_id": step.get("step_id"),
            "detail": (f"step {step.get('step_id')} is a WriteBooster support check but "
                       "names the Device Descriptor path; WB support MUST use READ "
                       "ATTRIBUTE dExtendedUFSFeaturesSupport "
                       "(api.get_extended_ufs_features_support().u8_write_booster)"),
            "suggestion": "READ ATTRIBUTE dExtendedUFSFeaturesSupport",
        }
    return None


IR_PATH_RULES = (_ir_wb_support_path,)


def check_ir_protocol_paths(ir: dict) -> list:
    """Flag IR steps whose stated protocol path contradicts a canonical idiom
    (report-only). Issue-dict shape matches check_semantics / check_api_calls."""
    issues: list = []
    for phase in ir.get("phases", []):
        for step in phase.get("steps", []):
            for rule in IR_PATH_RULES:
                try:
                    res = rule(step)
                except Exception:
                    res = None
                if res:
                    issues.append(res)
    return issues


# --------------------------------------------------------------------------- #
# Shared AST helpers
# --------------------------------------------------------------------------- #

def _target_names(targets: list) -> list:
    """Simple assignment-target names (Name.id / Attribute.attr)."""
    out = []
    for t in targets:
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Attribute):
            out.append(t.attr)
    return out


def _is_one(node: ast.AST) -> bool:
    """The integer literal 1 (not the bool True, which == 1 in Python)."""
    return (isinstance(node, ast.Constant) and not isinstance(node.value, bool)
            and node.value == 1)


# --------------------------------------------------------------------------- #
# Rule: wb_support_path
# WriteBooster *support* must be read from get_extended_ufs_features_support()
# .u8_write_booster. Reading the FFU bit (u0_ffu) into a WB-support var is the trap.
# --------------------------------------------------------------------------- #
_WB_TARGET_RE = re.compile(r"wb|booster", re.IGNORECASE)
# Wrong source fields when used as a WB *support* gate. Kept to u0_ffu for the seed
# (zero false-positive risk: it is the FFU bit, never the WB-support source). The
# Device Descriptor `b84_write_booster_buffer_type` trap is documented in
# CANONICAL_IDIOMS but not auto-flagged — it is a legitimate read for configured
# buffer type, so flagging it needs tighter context than the seed warrants.
_WB_WRONG_ATTRS = {"u0_ffu"}
_CORRECT_WB = "api.get_extended_ufs_features_support().u8_write_booster"


def _wb_support_path(tree: ast.AST, py_source: str) -> list:
    issues = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = _target_names(node.targets)
        if not any(_WB_TARGET_RE.search(n) for n in names):
            continue  # not a WriteBooster-context assignment
        for sub in ast.walk(node.value):
            if isinstance(sub, ast.Attribute) and sub.attr in _WB_WRONG_ATTRS:
                issues.append({
                    "alias": "semantic", "symbol": "wb_support_path",
                    "kind": "wb_support_wrong_field",
                    "detail": (f"WriteBooster support read via '.{sub.attr}' "
                               f"(assigned to {', '.join(names)}); use {_CORRECT_WB}"),
                    "line": sub.lineno,
                    "suggestion": "u8_write_booster",
                })
                break
    return issues


# --------------------------------------------------------------------------- #
# Rule: device_init_polarity  —  DORMANT (NOT in RULES; see below)
#
# Detects `if fDeviceInit != 1: raise` (asserts "must be 1 to be ready"). Whether
# that is wrong depends on the true readiness polarity, which is currently DISPUTED:
# the TC normalized flow says ready == 0 (UFS spec: device clears fDeviceInit on init
# complete), but the IR/enrich_prompt, BOTH generated outputs (_h and _cc), and
# review_refs CP-5 all assert == 1. Until a domain owner confirms the polarity we do
# NOT wire this into RULES — a deterministic gate must never flag possibly-correct
# code. The matcher is kept ready so enabling it later is a one-line change (add it
# to RULES, set the operator), plus a CANONICAL_IDIOMS entry.
# --------------------------------------------------------------------------- #

def _is_device_init_readflag(node: ast.AST) -> bool:
    """`api.read_flag(idn=...FlagIDN.DEVICE_INIT...)` (any arg position)."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "read_flag"):
        return False
    for arg in list(node.args) + [k.value for k in node.keywords]:
        for sub in ast.walk(arg):
            if isinstance(sub, ast.Attribute) and sub.attr == "DEVICE_INIT":
                return True
    return False


def _device_init_polarity(tree: ast.AST, py_source: str) -> list:
    issues = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # vars in this function bound to a DEVICE_INIT read_flag()
        di_vars: set = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and _is_device_init_readflag(node.value):
                di_vars |= set(_target_names(node.targets))
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.NotEq)):
                continue
            operands = [test.left] + list(test.comparators)
            has_di = any((isinstance(o, ast.Name) and o.id in di_vars)
                         or _is_device_init_readflag(o) for o in operands)
            has_one = any(_is_one(o) for o in operands)
            has_raise = any(isinstance(b, ast.Raise) for b in ast.walk(node))
            if has_di and has_one and has_raise:
                issues.append({
                    "alias": "semantic", "symbol": "device_init_polarity",
                    "kind": "device_init_wrong_polarity",
                    "detail": ("fDeviceInit asserted '!= 1 -> fail' (treats 1 as ready); "
                               "device is ready when fDeviceInit == 0 (device clears it on "
                               "init complete)"),
                    "line": node.lineno,
                    "suggestion": "assert fDeviceInit == 0",
                })
    return issues


# --------------------------------------------------------------------------- #
# Registry + public entry
# --------------------------------------------------------------------------- #
# Active rules. `_device_init_polarity` is DORMANT pending polarity confirmation
# (see its banner above) — deliberately excluded.
RULES = (_wb_support_path,)


def check_semantics(py_source: str, ir: dict | None = None) -> list:
    """Run every semantic rule over a generated .py; return issue dicts (possibly []).

    Same shape as api_grounding.check_api_calls — feed to format_issues. A rule that
    raises is skipped (never blocks the gate on an internal error)."""
    try:
        tree = ast.parse(py_source)
    except SyntaxError:
        return []  # syntax is reported separately by validate()
    issues: list = []
    for rule in RULES:
        try:
            issues.extend(rule(tree, py_source))
        except Exception:
            continue
    return issues
