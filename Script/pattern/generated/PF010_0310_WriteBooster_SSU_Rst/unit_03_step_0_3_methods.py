=== GROUNDING LOG ===
# Step: step_0_3 (READ DEVICE DESCRIPTOR — WB Support Check)
# Source: Script/api/ufs_api/descriptors/device_desc/functions.py — get_extended_ufs_features_support
# Script/api/ufs_api/descriptors/device_desc/structs.py — ExtendedUFSFeaturesSupport.u0_write_booster_buffer_resize
# Script/api/ufs_api/defines/enum_define.py — UFSFeaturesSupport.u8_write_booster
# Wiki: write-booster — WB support via device descriptor UFSFeaturesSupport bit 8

=== EXTRA IMPORTS ===
# (none needed)

=== METHODS ===
    def step3(self) -> None:
        """Step 0.3: Check WriteBooster support — READ DEVICE DESCRIPTOR

        Reads UFSFeaturesSupport (device descriptor) and checks u8_write_booster bit.
        Produces: wb_supported

        Expected: QUERY RESPONSE Success, WB bit is set
        """
        logger.info('Step 0.3: Read device descriptor for WB support check')
        dev_desc = api.get_device_descriptor()

        # Check UFSFeaturesSupport bit 8 for WB support
        ufs_feat = api.get_ufs_features_support()
        self.wb_supported = bool(ufs_feat.u8_write_booster)

        if self.wb_supported:
            logger.info('Step 0.3: WriteBooster is supported (u8_write_booster=1)')
        else:
            logger.info('Step 0.3: WriteBooster NOT supported — raise NOT SUPPORTED')
            raise api.UFS_NON_SUPPORT('WriteBooster not supported by device')