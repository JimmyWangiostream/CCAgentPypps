# Grounding Log

## phase_01_phase_0_methods.py

- `python graph_query.py TestUnitReady → api/cmd_seq/cmds.py:299 (TestUnitReady) — assign(lun: int)`
- `python graph_query.py ReadCapacity10 → api/cmd_seq/cmds.py:184 (ReadCapacity10) — assign(lun: int)`
- `python graph_query.py read_attribute → api/ufs_api/attr_flag_functions.py:64 (read_attribute)`
- `python graph_query.py AttributeIDN → api/ufs_api/defines/enum_define.py:148 (AttributeIDN) — dExtendedUFSFeaturesSupport NOT in enum → [NO MATCH for this symbol]`
- `python graph_query.py DescriptorIDN → api/ufs_api/defines/enum_define.py:121 (DescriptorIDN) — CONFIGURATION=0x01`
- `python graph_query.py ReadDescriptor → api/cmd_seq/cmds.py:527 (ReadDescriptor) — assign(idn, index, selector)`
- `python graph_query.py WriteDescriptor → api/cmd_seq/cmds.py:539 (WriteDescriptor) — assign(idn, index, selector, length)`
- `python graph_query.py ConfigDescriptor → api/ufs_api/descriptors/configuration_desc/structs.py:19 (ConfigDescriptor)`
- `python graph_query.py get_config_descriptors → api/ufs_api/descriptors/configuration_desc/functions.py:18 (get_config_descriptors)`
- `python graph_query.py push_write_config → api/ufs_api/descriptors/configuration_desc/functions.py:52 (push_write_config)`
- `python graph_query.py FlagIDN → api/ufs_api/defines/enum_define.py:133 (FlagIDN) — WRITEBOOSTER_EN=0x0E`
- `python graph_query.py BaseTestUnitReady → api/ufs_api/upiu/upiu.py:317 (BaseTestUnitReady) — assign(lun: int)`
- `python graph_query.py BaseReadDescriptor → api/ufs_api/upiu/upiu.py:564 (BaseReadDescriptor) — assign(idn, index, selector)`
- `python graph_query.py BaseWriteDescriptor → api/ufs_api/upiu/upiu.py:574 (BaseWriteDescriptor) — assign(idn, index, selector, length) + set_desc(ConfigDescriptor)`

## phase_02_loop_4_methods.py

- `python graph_query.py FlagIDN → api/ufs_api/defines/enum_define.py:133 (FlagIDN) — WRITEBOOSTER_EN=0x0E, WRITEBOOSTER_BUFFER_FLUSH_EN=0x0F, WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE=0x10, DEVICE_INIT=0x01`
- `python graph_query.py set_flag → api/ufs_api/attr_flag_functions.py:115 (set_flag)`
- `python graph_query.py clear_flag → api/ufs_api/attr_flag_functions.py:133 (clear_flag)`
- `python graph_query.py read_flag → api/ufs_api/attr_flag_functions.py:97 (read_flag)`
- `python graph_query.py Write10 → api/cmd_seq/cmds.py:359 (Write10) — assign(lun, lba, length, fua)`
- `python graph_query.py Read10 → api/cmd_seq/cmds.py:122 (Read10) — assign(lun, lba, length, fua=0), set_hw_cmp(mark_tag, pattern_mode)`
- `python graph_query.py BaseWrite10 → api/ufs_api/upiu/upiu.py:403 (BaseWrite10) — assign(lun, lba, length, fua: int)`
- `python graph_query.py BaseRead10 → api/ufs_api/upiu/upiu.py:128 (BaseRead10) — assign(lun, lba, length, fua=0)`
- `python graph_query.py StartStopUnit → api/cmd_seq/cmds.py:266 (StartStopUnit) — assign(lun, immed, power_condition, no_flush, start)`
- `python graph_query.py BaseStartStopUnit → api/ufs_api/upiu/upiu.py:266 (BaseStartStopUnit) — assign(lun, immed, power_condition, no_flush, start)`
- `python graph_query.py init_tester_to_unit_ready → api/ufs_api/initial_device.py:69 (init_tester_to_unit_ready)`
- `python graph_query.py Dcmd5ResetType → api/ufs_api/debug_cmd/dcmd_enum.py:51 (Dcmd5ResetType) — HW_RESET=0, ENDPOINT_RESET=2`
- `python graph_query.py CmdParamPatternMode → api/ufs_api/defines/enum_define.py:490 (CmdParamPatternMode) — HW_FIX=2`
