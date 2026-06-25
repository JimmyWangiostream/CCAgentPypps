=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/descriptors/configuration_desc/functions.py: get_config_descriptors (direct grep + read of source — issues READ DESCRIPTOR (Configuration) and returns the parsed list)

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def step5(self) -> None:
        """Step 0.5 — READ DESCRIPTOR (Configuration Descriptor). Produces: self.config_descriptor_data.

        Expected: QUERY RESPONSE Success. The parsed config descriptor list is kept so
        Step 0.6 can modify the WriteBooster fields and write it back.
        """
        # TODO-REVIEW-NO-WIKI
        logger.info('Step 0.5: READ DESCRIPTOR (Configuration Descriptor)')
        # sig: api.get_config_descriptors(print: bool=False) -> List[ConfigDescriptorUnion] via reading the source file
        self.config_descriptor_data = api.get_config_descriptors()  # src[code]: Script/api/ufs_api/descriptors/configuration_desc/functions.py:get_config_descriptors
        logger.info(f'Step 0.5: read {len(self.config_descriptor_data)} configuration descriptor block(s)')
