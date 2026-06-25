=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/descriptors/device_desc/functions.py: get_extended_ufs_features_support (direct grep + read of source — reads dExtendedUFSFeaturesSupport from Device Descriptor)
Script/api/ufs_api/descriptors/device_desc/structs.py: ExtendedUFSFeaturesSupport*.u8_write_booster (grep-confirmed bit accessor)
Script/api/exception.py: UFS_NON_SUPPORT (grep-confirmed ApiErrorBase subclass)

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def step3(self) -> None:
        """Step 0.3 — READ ATTRIBUTE dExtendedUFSFeaturesSupport. Produces: self.wb_supported.

        Expected: QUERY RESPONSE Success; WriteBooster feature bit is set.
        """
        # TODO-REVIEW-NO-WIKI
        logger.info('Step 0.3: check WriteBooster support via dExtendedUFSFeaturesSupport')
        # sig: api.get_extended_ufs_features_support() -> ExtendedUFSFeaturesSupportUnion via reading the source file
        ext_feat = api.get_extended_ufs_features_support()  # src[code]: Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_ufs_features_support
        self.wb_supported = bool(ext_feat.u8_write_booster)  # src[code]: device_desc/structs.py:ExtendedUFSFeaturesSupport*.u8_write_booster
        if not self.wb_supported:
            logger.error('Step 0.3: WriteBooster NOT supported by device')
            raise api.UFS_NON_SUPPORT('WriteBooster not supported by device')  # src[code]: Script/api/exception.py:UFS_NON_SUPPORT
        logger.info('Step 0.3: WriteBooster supported (u8_write_booster=1)')
