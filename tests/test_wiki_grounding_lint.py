"""Tests for the grounding-consistency lint (wiki_retrieval.grounding_lint).

Core checks are unit-testable without a Script root: they take the api_grounding-derived
data (field_bits / all_fields / index) directly. The headline case reproduces the real bug —
device-descriptor.md said WriteBooster = bit[0], but the struct puts it at bit[8]."""
from types import SimpleNamespace

from wiki_retrieval.grounding_lint import (
    build_field_bits, check_bit_positions, check_struct_field_tokens, check_namespace_apis,
)


# A minimal fake api_grounding index: ExtendedUFSFeaturesSupport bit layout (real values).
_FAKE_INDEX = {
    "_structs": {
        "ExtendedUFSFeaturesSupport310": {
            "u0_ffu", "u1_psa", "u3_refresh_op", "u8_write_booster", "u9_performance_throttling",
        },
        "DeviceDescriptor310": {"b6_number_lu", "l79_extended_ufs_features_support"},
    },
    "_all_struct_fields": frozenset({
        "u0_ffu", "u1_psa", "u3_refresh_op", "u8_write_booster", "u9_performance_throttling",
        "b6_number_lu", "l79_extended_ufs_features_support",
    }),
    "api": SimpleNamespace(symbols={"get_device_descriptor"}, all_names={"get_device_descriptor"}),
}


def _kinds(issues):
    return {i["kind"] for i in issues}


def test_build_field_bits_maps_feature_to_bit():
    fb = build_field_bits(_FAKE_INDEX)
    assert fb["writebooster"] == {8}
    assert fb["ffu"] == {0}


def test_bit_mismatch_flags_the_real_bug():
    """The device-descriptor.md defect: 'bit[0]=WriteBooster' — real bit is 8."""
    fb = build_field_bits(_FAKE_INDEX)
    issues = check_bit_positions("| dExtendedUFSFeaturesSupport | bit[0]=WriteBooster |", fb)
    assert _kinds(issues) == {"wiki_bit_mismatch"}
    assert "bit 8" in issues[0]["detail"] and "not 0" in issues[0]["detail"]


def test_bit_mismatch_prose_form():
    fb = build_field_bits(_FAKE_INDEX)
    issues = check_bit_positions("- **bit[0]**: WriteBooster supported", fb)
    assert _kinds(issues) == {"wiki_bit_mismatch"}


def test_correct_bit_is_clean():
    fb = build_field_bits(_FAKE_INDEX)
    assert check_bit_positions("bit[8]=WriteBooster supported", fb) == []


def test_generic_short_feature_not_flagged():
    """FFU (len 3) is below the min feature-key length -> never flagged (FP guard)."""
    fb = build_field_bits(_FAKE_INDEX)
    assert check_bit_positions("bit[2]=FFU ext", fb) == []


def test_unknown_struct_field_flagged():
    issues = check_struct_field_tokens("read l85_num_shared_write_booster_buffer_alloc_units",
                                       _FAKE_INDEX["_all_struct_fields"])
    assert _kinds(issues) == {"wiki_unknown_struct_field"}


def test_real_struct_field_is_clean():
    assert check_struct_field_tokens("bit u8_write_booster is set",
                                     _FAKE_INDEX["_all_struct_fields"]) == []


def test_unknown_api_flagged():
    issues = check_namespace_apis("call api.get_write_booster_magic() here", _FAKE_INDEX)
    assert _kinds(issues) == {"wiki_unknown_api"}


def test_real_api_is_clean():
    assert check_namespace_apis("call api.get_device_descriptor() here", _FAKE_INDEX) == []


def test_spec_name_not_treated_as_struct_field():
    """`dExtendedUFSFeaturesSupport` (camelCase spec name) must not match the field-token regex."""
    assert check_struct_field_tokens("the dExtendedUFSFeaturesSupport field",
                                     _FAKE_INDEX["_all_struct_fields"]) == []
