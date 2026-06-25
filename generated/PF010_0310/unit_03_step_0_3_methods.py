=== WIKI REFS ===
entities/device-descriptor.md — dExtendedUFSFeaturesSupport lives in the Device Descriptor; WriteBooster support is bit[8]

=== CODE REFS ===
Script/api/ufs_api/descriptors/device_desc/functions.py: get_extended_ufs_features_support (gitnexus rank1) — reads Device Descriptor, parses extended features
Script/api/ufs_api/descriptors/device_desc/structs.py: ExtendedUFSFeaturesSupport.u8_write_booster = CHK_BIT(..., 8) (rank2) — WriteBooster support bit
Script/pattern/sample_code/device_desc_sample.py: api.get_extended_ufs_features_support().u8_write_booster (rank3) — canonical idiom

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step3(self) -> None:
        """step_0_3 — confirm WriteBooster support via dExtendedUFSFeaturesSupport.

        NOTE: the TC labels this 'READ ATTRIBUTE', but dExtendedUFSFeaturesSupport is a
        Device Descriptor field (offset 4Fh–52h), not an AttributeIDN. The library helper
        reads the Device Descriptor and exposes the WriteBooster support bit (bit 8).
        """
        # produces: wb_supported
        ext = api.get_extended_ufs_features_support()  # src[code]: device_desc/functions.py:get_extended_ufs_features_support
        self.wb_supported = bool(ext.u8_write_booster)  # src[code]: ExtendedUFSFeaturesSupport.u8_write_booster (bit 8)
        if not self.wb_supported:
            logger.warning("step3: WriteBooster NOT supported (dExtendedUFSFeaturesSupport.u8_write_booster=0)")
            raise api.UFS_NON_SUPPORT
        logger.info("step3: WriteBooster supported (dExtendedUFSFeaturesSupport.u8_write_booster=1)")
