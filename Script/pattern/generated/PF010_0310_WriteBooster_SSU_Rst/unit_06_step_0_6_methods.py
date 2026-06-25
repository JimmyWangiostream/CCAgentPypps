=== GROUNDING LOG ===
# Step: step_0_6 (WRITE DESCRIPTOR Configuration Descriptor — set WB buffer)
# Source: Script/api/ufs_api/descriptors/device_desc/functions.py — get_config_descriptor, get_device_descriptor
# Script/pattern/luns_reconfiguration/PSW_F_P3_Reconfiguration_0002.py — pattern_get_configure_descriptor
# Script/pattern/config_attribute_flag/PSW_F_P3_Attributes_Flags_Descriptor_0001.py — set_config_descriptor_lock
# Wiki: write-booster — bWriteBoosterBufferType=0x01 (Shared), alloc MAX units

=== EXTRA IMPORTS ===
# (none needed)

=== METHODS ===
    def step6(self) -> None:
        """Step 0.6: Configure WriteBooster Buffer — WRITE DESCRIPTOR (Configuration)

        Sets bWriteBoosterBufferType=0x01 (Shared) and allocates MAX units.
        Produces: wb_configured

        Expected: QUERY RESPONSE Success
        """
        logger.info('Step 0.6: Configure WriteBooster buffer (Shared + MAX alloc units)')

        # Get current configuration descriptor to preserve other fields
        current_config = self.config_descriptor_data

        # Get max alloc units from device descriptor
        max_units = self.max_wb_alloc_units

        if max_units == 0:
            logger.info('Step 0.6: max_wb_alloc_units=0, skip WB config (not available)')
            self.wb_configured = False
            return

        # Prepare configuration descriptor write
        # b84_write_booster_buffer_type = 0x01 (Shared)
        # l85_num_shared_write_booster_buffer_alloc_units = MAX
        # Use raw WRITE DESCRIPTOR via ExecuteCMD
        cmd = ExecuteCMD.WriteDescriptor()
        cmd.assign(
            idn=0x01,  # Configuration Descriptor
            index=0x00,
            selector=0x00,
            data=b''
        )

        # Build config descriptor write data
        # Read current config, modify WB fields, write back
        # Configuration descriptor is 64 bytes
        config_data = bytearray(64)

        # Read current config descriptor data first
        cmd_read = ExecuteCMD.ReadDescriptor()
        cmd_read.assign(idn=0x01, index=0x00, selector=0x00)
        ExecuteCMD.enqueue(cmd_read)
        ExecuteCMD.send(clear_on_success=False)
        resp = ExecuteCMD.read_response(0)
        config_data = bytearray(resp.data) if hasattr(resp, 'data') else bytearray(64)

        # Set b84_write_booster_buffer_type = 0x01 (Shared) at offset 84
        # Set l85_num_shared_write_booster_buffer_alloc_units = MAX at offset 85
        if len(config_data) >= 84:
            config_data[84] = 0x01  # Shared type
        if len(config_data) >= 89:
            config_data[85] = max_units & 0xFF
            if max_units > 0xFF:
                config_data[86] = (max_units >> 8) & 0xFF
                config_data[87] = (max_units >> 16) & 0xFF
                config_data[88] = (max_units >> 24) & 0xFF

        # Write the modified configuration descriptor
        cmd.assign(idn=0x01, index=0x00, selector=0x00, data=bytes(config_data))
        ExecuteCMD.enqueue(cmd)
        ExecuteCMD.send(clear_on_success=True)

        self.wb_configured = True
        logger.info(f'Step 0.6: WriteBooster configured (Shared, {max_units} alloc units)')