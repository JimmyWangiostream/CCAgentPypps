=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/descriptors/configuration_desc/functions.py: push_write_config (direct read read — enqueues WRITE DESCRIPTOR (Configuration); caller must ExecuteCMD.send())
Script/api/ufs_api/descriptors/configuration_desc/structs.py: header.b17_write_booster_buffer_type / l18_num_shared_write_booster_buffer_alloc_units (grep-confirmed)
Script/api/ufs_api/defines/enum_define.py: WriteBoosterBufferType.SHARED (grep-confirmed = 0x01)

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def step6(self) -> None:
        """Step 0.6 — WRITE DESCRIPTOR (Configuration): WriteBooster Shared Type + MAX units.

        Consumes: self.max_wb_alloc_units, self.config_descriptor_data.
        dLUNumWriteBoosterBufferAllocUnits is R/O, so the shared-buffer size is set via the
        Configuration Descriptor. Expected: QUERY RESPONSE Success.
        """
        # TODO-REVIEW-NO-WIKI
        logger.info('Step 0.6: configure WriteBooster buffer (Shared type + MAX alloc units)')
        max_units = self.max_wb_alloc_units
        if max_units == 0:
            logger.warning('Step 0.6: max_wb_alloc_units == 0 — WB buffer not allocatable, skipping config')
            self.wb_configured = False
            return

        # Modify the first config descriptor block (covers LUN 0-7) and write it back.
        config_desc = self.config_descriptor_data[0]
        config_desc.header.b17_write_booster_buffer_type = api.WriteBoosterBufferType.SHARED  # src[code]: enum_define.py:WriteBoosterBufferType.SHARED
        config_desc.header.l18_num_shared_write_booster_buffer_alloc_units = max_units  # src[code]: configuration_desc/structs.py:l18_num_shared_write_booster_buffer_alloc_units
        # sig: api.push_write_config(config_desc, index, selector=0) -> None via reading the source file
        api.push_write_config(config_desc, index=0)  # src[code]: Script/api/ufs_api/descriptors/configuration_desc/functions.py:push_write_config
        ExecuteCMD.send(clear_on_success=True)

        self.wb_configured = True
        logger.info(f'Step 0.6: WriteBooster configured (Shared, {max_units} alloc units)')
