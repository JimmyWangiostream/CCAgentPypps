=== WIKI REFS ===
entities/configuration-descriptor.md — Configuration Descriptor is writable (before bConfigDescrLock); set WriteBooster buffer type + alloc units here

=== CODE REFS ===
Script/api/ufs_api/descriptors/configuration_desc/functions.py: push_write_config (gitnexus rank1) — WriteDescriptor(CONFIGURATION,index).set_desc(config_desc)
Script/pattern/sample_code/response_sample.py: printout_config_desc_header — b17_write_booster_buffer_type / l18_num_shared_write_booster_buffer_alloc_units (rank2)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step6(self) -> None:
        """step_0_6 — WRITE DESCRIPTOR Configuration Descriptor: Shared WB type + MAX alloc units.

        consumes: config_descriptor_data (step5), max_alloc_units (step4).
        """
        config_descs = self.config_descriptor_data
        # bWriteBoosterBufferType = 0x01 (Shared) ; apply MAX shared alloc units from step4
        # src[wiki]: wiki/entities/configuration-descriptor.md
        config_descs[0].header.b17_write_booster_buffer_type = 0x01  # src[code]: ConfigDescriptorHeader.b17_write_booster_buffer_type
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = self.max_alloc_units
        for index in range(4):
            api.push_write_config(config_descs[index], index=index)  # src[code]: configuration_desc/functions.py:push_write_config
        ExecuteCMD.send(clear_on_success=True)
        # NOTE: WRITE DESCRIPTOR on Configuration Descriptor requires bConfigDescrLock=0 and
        # typically a device reset to take effect.
        # TODO human-confirm: whether a reset is required here before the burn-in loop
        logger.info("step6: WRITE DESCRIPTOR Configuration — Shared WB type + MAX alloc units applied")
