=== GROUNDING LOG ===
# Step: step_0_5 (READ DESCRIPTOR Configuration Descriptor full read)
# Source: Script/api/ufs_api/descriptors/device_desc/functions.py — get_config_descriptor
# Script/api/ufs_api/descriptors/device_desc/structs.py — Config descriptor struct

=== EXTRA IMPORTS ===
# (none needed)

=== METHODS ===
    def step5(self) -> None:
        """Step 0.5: Read Configuration Descriptor (full read)

        Reads the Configuration Descriptor and stores the raw data for later write.
        Produces: config_descriptor_data

        Expected: QUERY RESPONSE Success
        """
        logger.info('Step 0.5: Read full Configuration Descriptor')
        # get_config_descriptor reads via READ DESCRIPTOR (0x01)
        self.config_descriptor_data = api.get_config_descriptor()
        logger.info('Step 0.5: Configuration Descriptor read successfully')