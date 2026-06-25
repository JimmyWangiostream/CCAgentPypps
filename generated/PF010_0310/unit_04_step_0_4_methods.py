=== WIKI REFS ===
entities/configuration-descriptor.md — WriteBooster shared buffer alloc units are a Configuration Descriptor field

=== CODE REFS ===
Script/api/ufs_api/descriptors/configuration_desc/functions.py: get_config_descriptors (gitnexus rank1)
Script/pattern/sample_code/response_sample.py: printout_config_desc_header — header field l18_num_shared_write_booster_buffer_alloc_units (rank2)
Script/api/ufs_api/defines/enum_define.py: AttributeIDN.0x17 == REF_CLK_GATING_WAIT_TIME (rank3) — confirms 0x17 is NOT alloc units

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step4(self) -> None:
        """step_0_4 — obtain MAX WriteBooster shared-buffer alloc units.

        NOTE: the TC labels this 'READ ATTRIBUTE IDN 0x17', but AttributeIDN 0x17 is
        REF_CLK_GATING_WAIT_TIME. dLUNumWriteBoosterBufferAllocUnits is a Configuration
        Descriptor header field — read it from the Configuration Descriptor instead.
        """
        # src[code]: configuration_desc/functions.py:get_config_descriptors
        self._config_descs = api.get_config_descriptors(print=False)
        # produces: max_alloc_units
        # src[code]: ConfigDescriptorHeader.l18_num_shared_write_booster_buffer_alloc_units
        self.max_alloc_units: int = self._config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units
        logger.info(f"step4: max WriteBooster shared-buffer alloc units = {self.max_alloc_units}")
