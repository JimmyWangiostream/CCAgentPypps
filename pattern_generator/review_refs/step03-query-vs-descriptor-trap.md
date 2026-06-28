# Step 0.3: Query READ ATTRIBUTE vs Descriptor Read Trap

Session: PF010_0310_WriteBooster_SSU_Rst code review (2026-06-25)

## The Bug

Step 0.3 in the normalized test flow specifies:
- **Query Opcode**: READ ATTRIBUTE (0x03)
- **IDN**: dExtendedUFSFeaturesSupport
- **Check**: u8_write_booster bit in extended features support

But three implementations (v2, Fixed_v1, jialin) all used:
```python
# WRONG: reads Device Descriptor, not Query Attribute
dev_desc = api.get_device_descriptor()
wb_type = dev_desc.b84_write_booster_buffer_type
if wb_type == 0:
    raise api.UFS_NON_SUPPORT
```

## Why It's Wrong

Two different UFS query mechanisms:

| Mechanism | Query Opcode | IDN / Field | Meaning |
|-----------|-------------|-------------|---------|
| QUERY READ ATTRIBUTE | 0x03 | dExtendedUFSFeaturesSupport | Checks if device supports WriteBooster feature (u8 bit) |
| QUERY READ DESCRIPTOR | 0x02 | Device Descriptor | Device descriptor with buffer type info (b84 byte) |

`b84_write_booster_buffer_type` values: 0=None, 1=Dedicated, 2=Shared
`u8_write_booster` value: 0=not supported, 1=supported

The test flow mandates the Query Attribute path — not the Descriptor path.

## Correct Implementation

```python
def step3(self) -> None:
    logger.info("CHECK WriteBooster support -- QUERY READ ATTRIBUTE (dExtendedUFSFeaturesSupport)")
    extended = api.get_extended_ufs_features_support()
    logger.info(f"dExtendedUFSFeaturesSupport.u8_write_booster = {extended.u8_write_booster}")
    if not extended.u8_write_booster:
        raise api.UFS_NON_SUPPORT
```

## Impact

This bug existed across ALL versions of the script (original, v2, jialin, Fixed_v1). It represents a **protocol coverage failure**: the test never actually exercises the Query READ ATTRIBUTE path on dExtendedUFSFeaturesSupport, which is the exact mechanism the normalized test flow requires.

## Lesson

When the test flow says "QUERY READ ATTRIBUTE", do NOT substitute with "QUERY READ DESCRIPTOR" even if both return WB-related data. The protocol path IS the verification — substituting it defeats the test's purpose.
