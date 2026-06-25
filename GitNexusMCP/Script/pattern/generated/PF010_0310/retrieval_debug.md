# Retrieval Debug

> ⚠️ review flags raised:
>  - `TODO-REVIEW-NO-WIKI`: 18

## unit_01_step_0_1_methods.py
**wiki refs:**
- entities/scsi-commands.md — TEST UNIT READY is a UCS SCSI command (CONTROL byte 00h); GOOD status means ready
- entities/lun.md — target the UFS device well-known LUN for the readiness probe
**code refs (gitnexus):**
- Script/api/cmd_seq/cmds.py: CmdSeqTestUnitReady (gitnexus context)
- Script/api/cmd_seq/protocols.py: IsEntry.enqueue (gitnexus context)
- Script/api/util/write_record/functions.py: get_empty_write_record (gitnexus query rank)
- Script/api/ufs_api/defines/enum_define.py: WellKnownLUN.UFS_DEVICE (gitnexus grep-confirmed)

## unit_02_step_0_2_methods.py
**wiki refs:**
- entities/scsi-commands.md — READ CAPACITY(10) (25h) is a UCS SCSI command returning the LU last-LBA/block-size
- entities/lun.md — capacity is a per-LUN property; max LBA derives from the LU capacity
**code refs (gitnexus):**
- Script/api/cmd_seq/cmds.py: ReadCapacity10 (gitnexus context — set_option(wait_queue_empty,timeout,delay_time))
- Script/api/cmd_seq/protocols.py: IsEntry.enqueue (gitnexus context)
- Script/api/__init__.py: shared (gitnexus grep — api.shared.param.gLUCapacity capacity cache)

## unit_03_step_0_3_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/device_desc/functions.py: get_extended_ufs_features_support (gitnexus grep + read — reads dExtendedUFSFeaturesSupport from Device Descriptor)
- Script/api/ufs_api/descriptors/device_desc/structs.py: ExtendedUFSFeaturesSupport*.u8_write_booster (grep-confirmed bit accessor)
- Script/api/exception.py: UFS_NON_SUPPORT (grep-confirmed ApiErrorBase subclass)
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_04_step_0_4_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/geometry_desc/functions.py: get_geometry_descriptor (gitnexus grep + read)
- Script/api/ufs_api/descriptors/geometry_desc/structs.py: GeometryDescriptor*.l79_write_booster_buffer_max_n_alloc_units (grep-confirmed — dWriteBoosterBufferMaxNAllocUnits, the MAX allocatable WB units)
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_05_step_0_5_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/configuration_desc/functions.py: get_config_descriptors (gitnexus grep + read — issues READ DESCRIPTOR (Configuration) and returns the parsed list)
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_06_step_0_6_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/configuration_desc/functions.py: push_write_config (gitnexus read — enqueues WRITE DESCRIPTOR (Configuration); caller must ExecuteCMD.send())
- Script/api/ufs_api/descriptors/configuration_desc/structs.py: header.b17_write_booster_buffer_type / l18_num_shared_write_booster_buffer_alloc_units (grep-confirmed)
- Script/api/ufs_api/defines/enum_define.py: WriteBoosterBufferType.SHARED (grep-confirmed = 0x01)
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_07_step_1_1_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/attr_flag_functions.py: set_flag (gitnexus context — set_flag(idn,index=0,selector=0))
- Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_08_step_1_2_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/attr_flag_functions.py: read_flag (gitnexus context — read_flag(idn,index=0,selector=0)->int)
- Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_09_step_1_3_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/rw_functions.py: sequential_write (lun,start_lba,total_size,chunk_size,fua,need_compare,compare_method,write_record)
- Script/api/ufs_api/rw_functions.py: get_empty_write_record
- Script/api/ufs_api/defines/enum_define.py: CompareMethod.HW_COMPARE
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_10_step_1_4_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/rw_functions.py: read_compare (write_record, compare_method)
- Script/api/ufs_api/defines/enum_define.py: CompareMethod.HW_COMPARE
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_11_step_1_5_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/cmd_seq/cmds.py: StartStopUnit (SSU) / CmdSeqPowerCycle (POR / LINKSTARTUP)
- Script/api/ufs_api/attr_flag_functions.py: read_flag (fDeviceInit)
- Script/api/ufs_api/defines/enum_define.py: PowerCycleMode.ALL_POWER_DOWN / LINK_START_UP, FlagIDN.DEVICE_INIT, WellKnownLUN.UFS_DEVICE
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_12_step_1_6_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/attr_flag_functions.py: read_flag
- Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_13_step_2_1_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/rw_functions.py: sequential_write / get_empty_write_record
- Script/api/ufs_api/defines/enum_define.py: CompareMethod.HW_COMPARE
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_14_step_2_2_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/attr_flag_functions.py: clear_flag
- Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_15_step_2_3_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/rw_functions.py: read_compare (write_record, compare_method)
- Script/api/ufs_api/defines/enum_define.py: CompareMethod.HW_COMPARE
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_16_step_2_4_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- (reuses _loop4_step_1_5 — Script/api/cmd_seq/cmds.py: StartStopUnit / CmdSeqPowerCycle)
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_17_step_2_5_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/attr_flag_functions.py: read_flag
- Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_18_step_3_3_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/attr_flag_functions.py: set_flag
- Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN / WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_19_step_3_4_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/cmd_seq/cmds.py: StartStopUnit (SSU) / CmdSeqPowerCycle (POR)
- Script/api/ufs_api/attr_flag_functions.py: read_flag (fDeviceInit)
- Script/api/ufs_api/defines/enum_define.py: PowerCycleMode.ALL_POWER_DOWN, FlagIDN.DEVICE_INIT, WellKnownLUN.UFS_DEVICE
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_20_step_3_5_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- Script/api/ufs_api/attr_flag_functions.py: read_flag
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_21_loop_4_wrapper_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- _NO MATCH_
