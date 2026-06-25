=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/descriptors/geometry_desc/functions.py: get_geometry_descriptor (direct grep + read of source)
Script/api/ufs_api/descriptors/geometry_desc/structs.py: GeometryDescriptor*.l79_write_booster_buffer_max_n_alloc_units (grep-confirmed — dWriteBoosterBufferMaxNAllocUnits, the MAX allocatable WB units)

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def step4(self) -> None:
        """Step 0.4 — read the maximum WriteBooster buffer alloc units. Produces: self.max_wb_alloc_units.

        The TC reads dLUNumWriteBoosterBufferAllocUnits (per-LU, R/O). The MAX value the
        host may allocate is the Geometry Descriptor field dWriteBoosterBufferMaxNAllocUnits,
        which is what Step 0.6 needs to program a MAX-sized shared buffer.
        Expected: QUERY RESPONSE Success; max alloc units returned.
        """
        # TODO-REVIEW-NO-WIKI
        logger.info('Step 0.4: read max WriteBooster buffer alloc units (Geometry Descriptor)')
        # sig: api.get_geometry_descriptor() -> GeometryDescriptorUnion via reading the source file
        geo_desc = api.get_geometry_descriptor()  # src[code]: Script/api/ufs_api/descriptors/geometry_desc/functions.py:get_geometry_descriptor
        self.max_wb_alloc_units = int(geo_desc.l79_write_booster_buffer_max_n_alloc_units)  # src[code]: geometry_desc/structs.py:l79_write_booster_buffer_max_n_alloc_units
        logger.info(f'Step 0.4: max_wb_alloc_units = {self.max_wb_alloc_units}')
