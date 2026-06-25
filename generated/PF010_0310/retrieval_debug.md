# Retrieval Debug

_(no review flags — every unit grounded in both wiki and code)_

## unit_01_step_0_1_methods.py
**wiki refs:**
- entities/scsi-commands.md — TEST UNIT READY (00h) is a mandatory no-data SCSI command; GOOD Status means ready
- entities/lun.md — iterate enabled Normal LUs to confirm readiness
**code refs (gitnexus):**
- Script/pattern/sample_code/response_sample.py: Pattern.test_test_unit_ready (gitnexus rank1) — TestUnitReady().assign/enqueue/send idiom
- Script/api/cmd_seq/cmds.py: TestUnitReady (gitnexus rank2)
- Script/api/shared.py: param.gMaxNumberLU / gUnit[].b3_lu_enable (rank3)

## unit_02_step_0_2_methods.py
**wiki refs:**
- entities/scsi-commands.md — READ CAPACITY(10) (25h) returns Last LBA + block length
**code refs (gitnexus):**
- Script/api/cmd_seq/cmds.py: ReadCapacity10 (gitnexus rank1)
- Script/api/ufs_api/initial_device.py: gLUCapacity[index] = gUnit[index].q11_logical_block_count (rank2) — capacity cache populated at init
- Script/api/shared.py: param.gLUCapacity / gMaxNumberLU (rank3)

## unit_03_step_0_3_methods.py
**wiki refs:**
- entities/device-descriptor.md — dExtendedUFSFeaturesSupport lives in the Device Descriptor; WriteBooster support is bit[8]
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/device_desc/functions.py: get_extended_ufs_features_support (gitnexus rank1) — reads Device Descriptor, parses extended features
- Script/api/ufs_api/descriptors/device_desc/structs.py: ExtendedUFSFeaturesSupport.u8_write_booster = CHK_BIT(..., 8) (rank2) — WriteBooster support bit
- Script/pattern/sample_code/device_desc_sample.py: api.get_extended_ufs_features_support().u8_write_booster (rank3) — canonical idiom

## unit_04_step_0_4_methods.py
**wiki refs:**
- entities/configuration-descriptor.md — WriteBooster shared buffer alloc units are a Configuration Descriptor field
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/configuration_desc/functions.py: get_config_descriptors (gitnexus rank1)
- Script/pattern/sample_code/response_sample.py: printout_config_desc_header — header field l18_num_shared_write_booster_buffer_alloc_units (rank2)
- Script/api/ufs_api/defines/enum_define.py: AttributeIDN.0x17 == REF_CLK_GATING_WAIT_TIME (rank3) — confirms 0x17 is NOT alloc units

## unit_05_step_0_5_methods.py
**wiki refs:**
- entities/configuration-descriptor.md — Configuration Descriptor (IDN 01h) read via READ DESCRIPTOR
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/configuration_desc/functions.py: get_config_descriptors (gitnexus rank1) — reads all 4 config indexes
- Script/api/ufs_api/defines/enum_define.py: DescriptorIDN.CONFIGURATION=0x01 (rank2)

## unit_06_step_0_6_methods.py
**wiki refs:**
- entities/configuration-descriptor.md — Configuration Descriptor is writable (before bConfigDescrLock); set WriteBooster buffer type + alloc units here
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/configuration_desc/functions.py: push_write_config (gitnexus rank1) — WriteDescriptor(CONFIGURATION,index).set_desc(config_desc)
- Script/pattern/sample_code/response_sample.py: printout_config_desc_header — b17_write_booster_buffer_type / l18_num_shared_write_booster_buffer_alloc_units (rank2)

## unit_07_loop_4_methods.py
**wiki refs:**
- entities/flags.md — fWriteBoosterEn / flush flags accessed via SET/READ/CLEAR FLAG; volatile flags reset on power cycle
- entities/scsi-commands.md — WRITE(10)/READ(10) for the W/R compare phases; START STOP UNIT (1Bh) for SSU power transitions
**code refs (gitnexus):**
- Script/api/ufs_api/attr_flag_functions.py: set_flag / read_flag / clear_flag (gitnexus rank1) — return flag value
- Script/api/ufs_api/rw_functions.py: random_write / read_compare (rank2) — random W/R + HW compare via write_record
- Script/api/ufs_api/initial_device.py: init_tester_to_unit_ready(resetmode, powerdown) (rank3) — powerdown=True -> POR, powerdown=False -> reset/link
- Script/pattern/read_disturb/PSW_F_P3_Read_Disturb_0004_RD_Flush_Test.py: StartStopUnit().assign(lun=UFS_DEVICE, immed, power_condition, no_flush, start) (rank4) — SSU idiom
- Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN=0x0E, WRITEBOOSTER_BUFFER_FLUSH_EN=0x0F, WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE=0x10 (rank5)
