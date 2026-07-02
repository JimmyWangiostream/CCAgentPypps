=== WIKI REFS ===
entities/configuration-descriptor.md -- Configuration Descriptor IDN 0x01 structure and WB buffer fields
entities/write-booster.md -- WriteBooster buffer type and allocation units

=== CODE REFS ===
Script/api/ufs_api/descriptors/configuration_desc/functions.py:push_write_config (gitnexus rank1)
Script/pattern/PSA/PSW_F_P3_PSA_0005_PSAwritebootEM1_Test.py:Pattern.config_precondition -- idiom for setting b17_write_booster_buffer_type=1 (SHARED)
Script/pattern/rain/mutual_fun.py:config_lun -- l18_num_shared_write_booster_buffer_alloc_units from gGeometry
Script/api/ufs_api/descriptors/configuration_desc/functions.py:get_config_descriptors -- to read current config before modifying
Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_write_booster_support -- to get max alloc units from geometry

=== REVIEW FLAGS ===
(empty)

=== EXTRA IMPORTS ===
import Script.api.shared as shared

=== METHODS ===
    def step2(self) -> None:
        # sig: api.get_config_descriptors() -> list[ConfigDescriptorUnion]  via gitnexus context
        # sig: api.push_write_config(config_desc, index, selector=0)  via push_write_config context
        # sig: shared.param.gGeometry.l79_write_booster_buffer_max_n_alloc_units  via config_lun idiom
        # Set WriteBooster Buffer to SHARED type with maximum allocation units
        # src[code]: Script/api/ufs_api/descriptors/configuration_desc/functions.py:get_config_descriptors
        # src[code]: Script/pattern/rain/mutual_fun.py:config_lun (l79 field access)
        import Script.api.shared as shared

        config_descs = api.get_config_descriptors()
        wb_geometry = api.get_extended_write_booster_support()
        max_alloc_units = shared.param.gGeometry.l79_write_booster_buffer_max_n_alloc_units

        logger.info(f"[PF010_0310] Setting WB Buffer to SHARED, max_alloc_units={max_alloc_units}")

        # Set global WB buffer type to SHARED on config index 0
        config_descs[0].header.b17_write_booster_buffer_type = api.WriteBoosterBufferType.SHARED
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = max_alloc_units

        # Ensure the max-capacity LUN is enabled with its current allocation
        # Just preserve existing unit config -- only change WB buffer header fields
        # Write all 4 config descriptor pages
        for idx in range(4):
            # src[code]: Script/api/ufs_api/descriptors/configuration_desc/functions.py:push_write_config
            api.push_write_config(config_descs[idx], index=idx)
        ExecuteCMD.send()

        self.config_descriptor_data = config_descs  # consumed by step_0_2 itself (for reference)
        self.max_alloc_units = max_alloc_units       # consumed by loop_1 steps
