"""Tests for the deterministic semantic layer (pattern_generator.semantic_checks).

Each rule must FLAG the real bug snippet and stay CLEAN on the correct form and on
legitimate look-alikes — the deterministic gate must never flag correct code."""
from pattern_generator.semantic_checks import (
    check_semantics, canonical_facts, RULES, _device_init_polarity,
    check_ir_protocol_paths,
)


def _kinds(src):
    return {i["kind"] for i in check_semantics(src)}


# --------------------------------------------------------------------------- #
# wb_support_path
# --------------------------------------------------------------------------- #

# The actual Hermes bug: FFU bit read into a WriteBooster-support var.
HERMES_WB_BUG = '''
class P:
    def step1(self):
        ufs_feat = api.get_ufs_features_support()
        wb_supported = bool(ufs_feat.u0_ffu)
        return wb_supported
'''

# The correct form (from the working pipeline output).
CORRECT_WB = '''
class P:
    def step3(self):
        ext = api.get_extended_ufs_features_support()
        self.wb_supported = bool(ext.u8_write_booster)
'''

# A legitimate FFU support check — must NOT be flagged (target isn't WB).
LEGIT_FFU = '''
class P:
    def step1(self):
        feat = api.get_ufs_features_support()
        ffu_supported = bool(feat.u0_ffu)
        return ffu_supported
'''


def test_wb_support_flags_ffu_bit_misuse():
    kinds = _kinds(HERMES_WB_BUG)
    assert "wb_support_wrong_field" in kinds


def test_wb_support_clean_on_correct_form():
    assert check_semantics(CORRECT_WB) == []


def test_wb_support_no_false_positive_on_legit_ffu():
    # FFU read into an FFU var is correct usage, not a WriteBooster trap.
    assert check_semantics(LEGIT_FFU) == []


def test_wb_finding_cites_correct_idiom():
    issues = check_semantics(HERMES_WB_BUG)
    assert any("get_extended_ufs_features_support" in i["detail"] for i in issues)
    assert all("line" in i and "detail" in i for i in issues)  # format_issues shape


# --------------------------------------------------------------------------- #
# canonical_facts (FEED / prevent)
# --------------------------------------------------------------------------- #

def test_canonical_facts_triggers_on_wb_support_query():
    facts = canonical_facts("step check write booster support capability")
    assert any("u8_write_booster" in f for f in facts)


def test_canonical_facts_empty_on_unrelated_query():
    assert canonical_facts("random write read compare lba") == []


# --------------------------------------------------------------------------- #
# check_ir_protocol_paths (Lever #4 — IR-level flag, report-only)
# --------------------------------------------------------------------------- #

def _ir(*steps):
    return {"phases": [{"phase_id": "p", "steps": list(steps)}]}


def test_ir_does_not_flag_wb_support_via_read_descriptor():
    # The real PF010_0310 step_0_1 shape: WB support check via READ DESCRIPTOR of the
    # Device Descriptor. This is the CORRECT path (get_extended_ufs_features_support reads
    # descriptor field l79), so it must NOT be flagged — the retired _ir_wb_support_path
    # rule was false-premised.
    ir = _ir({"step_id": "step_0_1", "name": "檢查 Write Booster 支援能力",
              "ufs_query": "READ DESCRIPTOR (0x07)", "idn": "0x00 (Device Descriptor)"})
    assert check_ir_protocol_paths(ir) == []


def test_ir_clean_on_wb_config_step_not_support_check():
    # A WB Buffer config step (no support/capability token) must NOT be flagged
    # even though it reads the Configuration/Device descriptor.
    ir = _ir({"step_id": "s", "name": "設定 Write Booster Buffer 為 Shared 類型",
              "ufs_query": "WRITE DESCRIPTOR (0x08)", "idn": "0x01 (Configuration Descriptor)"})
    assert check_ir_protocol_paths(ir) == []


def test_ir_clean_on_unrelated_step():
    ir = _ir({"step_id": "s", "name": "隨機寫入", "scsi_cmd": "WRITE(10)", "idn": None})
    assert check_ir_protocol_paths(ir) == []


# --------------------------------------------------------------------------- #
# device_init_polarity is DORMANT (disputed polarity) — must not be enforced
# --------------------------------------------------------------------------- #

DEVICE_INIT_NE_1 = '''
class P:
    def _chk(self):
        val = api.read_flag(idn=api.FlagIDN.DEVICE_INIT)
        if val != 1:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION("not ready")
'''


def test_device_init_rule_is_dormant():
    # The matcher exists but is deliberately NOT wired into RULES until the
    # readiness polarity is confirmed by a domain owner.
    assert _device_init_polarity not in RULES
    # So a `!= 1` device-init assertion is NOT flagged by the active gate.
    assert "device_init_wrong_polarity" not in _kinds(DEVICE_INIT_NE_1)


def test_wb_en_compare_to_1_not_flagged():
    # A read of WRITEBOOSTER_EN compared to 1 must never be confused with device-init.
    src = '''
class P:
    def step(self):
        wb_en = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
        if wb_en != 1:
            raise api.SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH
'''
    assert check_semantics(src) == []
