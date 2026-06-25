=== GROUNDING LOG ===
# Step: step_0_4 (READ CONFIG DESCRIPTOR — Max WB Alloc Units)
# Source: Script/api/ufs_api/descriptors/device_desc/functions.py — get_config_descriptor
# Script/api/ufs_api/descriptors/device_desc/structs.py — DeviceDescriptor310/400/410.l85_num_shared_write_booster_buffer_alloc_units
# Wiki: write-booster — dLUNumWriteBoosterBufferAllocUnits is from Configuration Descriptor

=== EXTRA IMPORTS ===
# (none needed)

=== METHODS ===
    def step4(self) -> None:
        """Step 0.4: Read max WB alloc units — READ DESCRIPTOR (Configuration Descriptor)

        Reads Configuration Descriptor to get l85_num_shared_write_booster_buffer_alloc_units.
        Produces: max_wb_alloc_units

        Expected: QUERY RESPONSE Success, returns max alloc units
        """
        logger.info('Step 0.4: Read Configuration Descriptor for max WB alloc units')
        config_data = api.get_config_descriptor()

        # Max alloc units from device descriptor field (WB max capability)
        # Device descriptor has l85_num_shared_write_booster_buffer_alloc_units
        dev_desc = api.get_device_descriptor()
        self.max_wb_alloc_units = int(dev_desc.l85_num_shared_write_booster_buffer_alloc_units)

        logger.info(f'Step 0.4: max_wb_alloc_units = {self.max_wb_alloc_units}')