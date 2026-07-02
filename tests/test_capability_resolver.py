"""Tests for the deterministic capability resolver (pattern_generator.capability_resolver)."""
import pytest

from pattern_generator.api_grounding import SigSpec, Namespace, build_script_index
from pattern_generator.capability_resolver import (
    canonical_symbols, symbol_version_ok, version_gate, _struct_family_versions,
    check_version_availability,
)
from pattern_generator.config import PGConfig

# Fake index: the three real WriteBooster-adjacent accessors + their return-struct versions.
_FAKE = {
    "api": Namespace(symbols={
        "get_device_descriptor": SigSpec(kind="func", returns="DeviceDescriptorUnion"),
        "get_extended_ufs_features_support": SigSpec(
            kind="func", returns="ExtendedUFSFeaturesSupportUnion"),
        "get_extended_write_booster_support": SigSpec(
            kind="func", returns="ExtendedWriteBoosterSupportUnion"),
    }, all_names=set()),
    "_structs": {
        "DeviceDescriptor310": set(), "DeviceDescriptor400": set(), "DeviceDescriptor410": set(),
        "ExtendedUFSFeaturesSupport310": {"u8_write_booster"},
        "ExtendedUFSFeaturesSupport400": {"u8_write_booster"},
        "ExtendedUFSFeaturesSupport410": {"u8_write_booster"},
        "ExtendedWriteBoosterSupport410": {"u0_write_booster_buffer_resize"},
    },
}

_WB_IDIOM = ("WriteBooster support MUST be read via "
             "api.get_extended_ufs_features_support().u8_write_booster — NOT u0_ffu.")


def test_canonical_symbols_parses_idiom():
    assert canonical_symbols([_WB_IDIOM]) == ["get_extended_ufs_features_support"]


def test_struct_family_versions():
    assert _struct_family_versions(_FAKE, "ExtendedUFSFeaturesSupportUnion") == {"310", "400", "410"}
    assert _struct_family_versions(_FAKE, "ExtendedWriteBoosterSupportUnion") == {"410"}


def test_wb_sibling_unavailable_on_31():
    # get_extended_write_booster_support returns a 4.1-only struct -> not OK on 3.1
    assert symbol_version_ok(_FAKE, "get_extended_write_booster_support", "3.1") is False
    # the correct support accessor exists on all versions -> OK on 3.1
    assert symbol_version_ok(_FAKE, "get_extended_ufs_features_support", "3.1") is True


def test_both_available_on_41():
    assert symbol_version_ok(_FAKE, "get_extended_write_booster_support", "4.1") is True
    assert symbol_version_ok(_FAKE, "get_extended_ufs_features_support", "4.1") is True


def test_no_version_no_gating():
    assert symbol_version_ok(_FAKE, "get_extended_write_booster_support", None) is True


def test_version_gate_drops_the_wrong_sibling_on_31():
    names = ["get_extended_write_booster_support", "get_extended_ufs_features_support",
             "get_device_descriptor"]
    kept, dropped = version_gate(_FAKE, names, "3.1")
    assert dropped == ["get_extended_write_booster_support"]
    assert "get_extended_ufs_features_support" in kept and "get_device_descriptor" in kept


_USES_WB_SIBLING = ("class P:\n    def step1(self):\n"
                    "        x = api.get_extended_write_booster_support()\n")


def test_version_catch_flags_used_wrong_sibling_on_31():
    issues = check_version_availability(_USES_WB_SIBLING, _FAKE, "3.1")
    assert [i["kind"] for i in issues] == ["version_unavailable"]
    assert issues[0]["symbol"] == "get_extended_write_booster_support"


def test_version_catch_clean_on_41():
    assert check_version_availability(_USES_WB_SIBLING, _FAKE, "4.1") == []


def test_version_catch_no_version_no_flag():
    assert check_version_availability(_USES_WB_SIBLING, _FAKE, None) == []


# --- integration against the REAL Script index (the definitive proof) --------------------
_SCRIPT = PGConfig().script_root
_HAS_SCRIPT = (_SCRIPT / "api" / "__init__.py").is_file()


@pytest.mark.skipif(not _HAS_SCRIPT, reason="GitNexusMCP/Script not present")
def test_real_index_gates_wb_sibling_on_31():
    index = build_script_index(_SCRIPT)
    assert index is not None
    # The real Hermes trap: on a 3.1 target the w77/4.1-only accessor must be gated out,
    # while the version-agnostic support accessor survives.
    assert symbol_version_ok(index, "get_extended_write_booster_support", "3.1") is False
    assert symbol_version_ok(index, "get_extended_ufs_features_support", "3.1") is True
    assert symbol_version_ok(index, "get_extended_write_booster_support", "4.1") is True
