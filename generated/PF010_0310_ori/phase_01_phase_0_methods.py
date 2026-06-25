=== GROUNDING LOG ===
python graph_query.py TestUnitReady → api/cmd_seq/cmds.py:299 (TestUnitReady) — assign(lun: int)
python graph_query.py ReadCapacity10 → api/cmd_seq/cmds.py:184 (ReadCapacity10) — assign(lun: int)
python graph_query.py read_attribute → api/ufs_api/attr_flag_functions.py:64 (read_attribute)
python graph_query.py AttributeIDN → api/ufs_api/defines/enum_define.py:148 (AttributeIDN) — dExtendedUFSFeaturesSupport NOT in enum → [NO MATCH for this symbol]
python graph_query.py DescriptorIDN → api/ufs_api/defines/enum_define.py:121 (DescriptorIDN) — CONFIGURATION=0x01
python graph_query.py ReadDescriptor → api/cmd_seq/cmds.py:527 (ReadDescriptor) — assign(idn, index, selector)
python graph_query.py WriteDescriptor → api/cmd_seq/cmds.py:539 (WriteDescriptor) — assign(idn, index, selector, length)
python graph_query.py ConfigDescriptor → api/ufs_api/descriptors/configuration_desc/structs.py:19 (ConfigDescriptor)
python graph_query.py get_config_descriptors → api/ufs_api/descriptors/configuration_desc/functions.py:18 (get_config_descriptors)
python graph_query.py push_write_config → api/ufs_api/descriptors/configuration_desc/functions.py:52 (push_write_config)
python graph_query.py FlagIDN → api/ufs_api/defines/enum_define.py:133 (FlagIDN) — WRITEBOOSTER_EN=0x0E
python graph_query.py BaseTestUnitReady → api/ufs_api/upiu/upiu.py:317 (BaseTestUnitReady) — assign(lun: int)
python graph_query.py BaseReadDescriptor → api/ufs_api/upiu/upiu.py:564 (BaseReadDescriptor) — assign(idn, index, selector)
python graph_query.py BaseWriteDescriptor → api/ufs_api/upiu/upiu.py:574 (BaseWriteDescriptor) — assign(idn, index, selector, length) + set_desc(ConfigDescriptor)

=== EXTRA IMPORTS ===
import Script.api.shared as shared

=== METHODS ===
    def step1(self) -> None:
        """step_0_1 — TEST UNIT READY (0x00): 確認裝置就緒."""
        param = shared.param
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable:
                ExecuteCMD.TestUnitReady().assign(lun=lun).enqueue()  # src[code]: api/cmd_seq/cmds.py:299
        ExecuteCMD.send(clear_on_success=True)
        logger.info("step1: TEST UNIT READY — GOOD Status confirmed for all enabled LUNs")

    def step2(self) -> None:
        """step_0_2 — READ CAPACITY(10) (0x25): 取得 MAX_LBA."""
        param = shared.param
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable:
                ExecuteCMD.ReadCapacity10().assign(lun=lun).enqueue()  # src[code]: api/cmd_seq/cmds.py:184
        ExecuteCMD.send(clear_on_success=True)
        # gLUCapacity is populated by ExecuteCMD.send after ReadCapacity10 # src[code]: api/ufs_api/rw_functions.py:25
        self._test_lun: int = 0
        self.max_lba: int = 0
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable and param.gLUCapacity[lun] > 0:
                self._test_lun = lun
                self.max_lba = param.gLUCapacity[lun]
                break
        logger.info(f"step2: test_lun={self._test_lun}, max_lba={self.max_lba}")

    def step3(self) -> None:
        """step_0_3 — READ ATTRIBUTE dExtendedUFSFeaturesSupport: 確認 WB 支援."""
        # dExtendedUFSFeaturesSupport is NOT in AttributeIDN enum (code-grounded enum ends at 0x1B).
        # The attribute is cached in shared.param.gDevice after first_init_to_max_hs_gear.
        # TODO human-confirm: verify IDN value for dExtendedUFSFeaturesSupport in this codebase's AttributeIDN enum
        param = shared.param
        ext_features = param.gDevice.l79_extended_ufs_features_support  # TODO human-confirm: field name
        WB_SUPPORT_BIT = 0  # bit 0 = WriteBooster support per JESD220H §14.1 # src[wiki]: wiki/Spec/
        if not (ext_features & (1 << WB_SUPPORT_BIT)):
            logger.warning("step3: dExtendedUFSFeaturesSupport bit0=0 — WB not supported")
            raise api.UFS_NON_SUPPORT
        logger.info(f"step3: dExtendedUFSFeaturesSupport=0x{ext_features:08X} — WB supported")

    def step4(self) -> None:
        """step_0_4 — READ dLUNumWriteBoosterBufferAllocUnits: 取得 max alloc units.

        Per UFS SPEC JESD220H §14.3.1, dLUNumWriteBoosterBufferAllocUnits is a
        READ-ONLY field inside Configuration Descriptor, NOT a standalone Attribute.
        TC note 'IDN 0x17' likely refers to the descriptor field offset, not AttributeIDN.
        """
        # TODO human-confirm: AttributeIDN.0x17 maps to REF_CLK_GATING_WAIT_TIME in code,
        #   not dLUNumWriteBoosterBufferAllocUnits. Read via Configuration Descriptor instead.
        config_descs = api.get_config_descriptors(print=False)  # src[code]: api/ufs_api/descriptors/configuration_desc/functions.py:18
        self._config_descs = config_descs
        self.max_alloc_units: int = config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units  # TODO human-confirm: field name
        logger.info(f"step4: WB shared buffer alloc units = {self.max_alloc_units}")

    def step5(self) -> None:
        """step_0_5 — READ DESCRIPTOR Configuration Descriptor (IDN 0x01): log full config."""
        api.get_config_descriptors(print=True)  # src[code]: api/ufs_api/descriptors/configuration_desc/functions.py:18
        # src[code]: DescriptorIDN.CONFIGURATION=0x01 @ api/ufs_api/defines/enum_define.py:123
        logger.info("step5: Configuration Descriptor logged")

    def step6(self) -> None:
        """step_0_6 — WRITE DESCRIPTOR Configuration Descriptor: Shared Type + MAX alloc units."""
        config_descs = self._config_descs
        # bWriteBoosterBufferType = 0x01 (Shared buffer) per JESD220H
        # src[wiki]: wiki/Spec/ — Shared WriteBooster buffer type
        config_descs[0].header.b17_write_booster_buffer_type = 0x01  # TODO human-confirm: field name
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = self.max_alloc_units  # TODO human-confirm: field name
        for i in range(4):
            config_descs[i].header.b2_conf_desc_continue = 0 if i == 3 else 1  # TODO human-confirm: field name
            api.push_write_config(config_descs[i], index=i)  # src[code]: api/ufs_api/descriptors/configuration_desc/functions.py:52
        ExecuteCMD.send(clear_on_success=True)
        logger.info("step6: WRITE DESCRIPTOR Configuration — WB Shared Type + MAX alloc units applied")
