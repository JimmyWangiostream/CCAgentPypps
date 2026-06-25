=== WIKI REFS ===
entities/configuration-descriptor.md — Configuration Descriptor (IDN 01h) read via READ DESCRIPTOR

=== CODE REFS ===
Script/api/ufs_api/descriptors/configuration_desc/functions.py: get_config_descriptors (gitnexus rank1) — reads all 4 config indexes
Script/api/ufs_api/defines/enum_define.py: DescriptorIDN.CONFIGURATION=0x01 (rank2)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step5(self) -> None:
        """step_0_5 — READ DESCRIPTOR Configuration Descriptor (IDN 0x01): read and log full config."""
        # produces: config_descriptor_data
        # src[code]: configuration_desc/functions.py:get_config_descriptors ; DescriptorIDN.CONFIGURATION=0x01
        self.config_descriptor_data = api.get_config_descriptors(print=True)
        logger.info("step5: Configuration Descriptor read and logged")
