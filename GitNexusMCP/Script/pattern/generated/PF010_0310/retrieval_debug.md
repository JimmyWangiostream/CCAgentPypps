# Retrieval Debug

> ⚠️ review flags raised:
>  - `TODO-REVIEW-NO-WIKI`: 3

## unit_01_step_0_1_methods.py
**wiki refs:**
- entities/write-booster.md -- Canonical idiom confirms WriteBooster support via get_extended_ufs_features_support().u8_write_booster
- entities/device-descriptor.md -- Device Descriptor structure reference
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_ufs_features_support (gitnexus rank1)
- Script/pattern/rain/mutual_fun.py:config_lun -- idioms for reading gMaxNumberLU, gUnit[lun].b3_lu_enable, gUnit[lun].l4_num_alloc_units
- Script/api/ufs_api/descriptors/device_desc/functions.py:get_device_descriptor (caller of get_extended_ufs_features_support)
- Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_write_booster_support (rank2)

## unit_02_step_0_2_methods.py
**wiki refs:**
- entities/configuration-descriptor.md -- Configuration Descriptor IDN 0x01 structure and WB buffer fields
- entities/write-booster.md -- WriteBooster buffer type and allocation units
**code refs (gitnexus):**
- Script/api/ufs_api/descriptors/configuration_desc/functions.py:push_write_config (gitnexus rank1)
- Script/pattern/PSA/PSW_F_P3_PSA_0005_PSAwritebootEM1_Test.py:Pattern.config_precondition -- idiom for setting b17_write_booster_buffer_type=1 (SHARED)
- Script/pattern/rain/mutual_fun.py:config_lun -- l18_num_shared_write_booster_buffer_alloc_units from gGeometry
- Script/api/ufs_api/descriptors/configuration_desc/functions.py:get_config_descriptors -- to read current config before modifying
- Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_write_booster_support -- to get max alloc units from geometry

## unit_03_step_1_1_methods.py
**wiki refs:**
- entities/flags.md -- SET FLAG (0x02) opcode and flag IDN structure
- entities/write-booster.md -- WriteBooster fWriteBoosterEn flag meaning
**code refs (gitnexus):**
- Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1 -- confirmed ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()

## unit_04_step_1_2_methods.py
**wiki refs:**
- entities/scsi-commands.md -- WRITE(10) opcode 0x2A
- entities/write-booster.md -- WriteBooster behavior with random writes
**code refs (gitnexus):**
- Script/api/ufs_api/rw_functions.py:random_write (gitnexus confirmed signature)
- Script/pattern/sample_code/normal_rw_sample.py:Pattern.step1 -- confirmed api.random_write() idiom with write_record
- Script/api/util/write_record/functions.py:get_empty_write_record -- write_record source

## unit_05_step_1_3_methods.py
**wiki refs:**
- entities/scsi-commands.md -- READ(10) opcode 0x28
- entities/lun.md -- LUN semantics
**code refs (gitnexus):**
- Script/api/ufs_api/rw_functions.py:random_read -- confirmed signature via gitnexus context

## unit_06_step_1_4_methods.py
**wiki refs:**
- entities/power-modes.md -- POR behavior and power mode transitions
- concepts/power-management.md -- Reset types and timing
**code refs (gitnexus):**
- Script/pattern/Inhibition_time/PSW_F_P3_InhibitionTime_0001_Disable_Enable_Test.py:Pattern.power_cycle -- confirmed POR idiom
- Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready -- confirmed signature
- Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode -- confirmed no-arg vendor mode
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_07_step_2_1_methods.py
**wiki refs:**
- entities/flags.md -- CLEAR FLAG (0x05) opcode and flag IDN structure
- entities/write-booster.md -- WriteBooster flag semantics
**code refs (gitnexus):**
- Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1 -- confirmed ExecuteCMD.ClearFlag() idiom

## unit_08_step_2_2_methods.py
**wiki refs:**
- entities/scsi-commands.md -- WRITE(10) opcode 0x2A
- entities/write-booster.md -- WriteBooster behavior (WB disabled path)
**code refs (gitnexus):**
- Script/api/ufs_api/rw_functions.py:random_write -- confirmed signature
- Script/pattern/sample_code/normal_rw_sample.py:Pattern.step1 -- confirmed api.random_write() idiom

## unit_09_step_2_3_methods.py
**wiki refs:**
- entities/scsi-commands.md -- READ(10) opcode 0x28
- entities/lun.md -- LUN semantics
**code refs (gitnexus):**
- Script/api/ufs_api/rw_functions.py:random_read -- confirmed signature via gitnexus context

## unit_10_step_2_4_methods.py
**wiki refs:**
- entities/power-modes.md -- POR behavior and power mode transitions
**code refs (gitnexus):**
- Script/pattern/Inhibition_time/PSW_F_P3_InhibitionTime_0001_Disable_Enable_Test.py:Pattern.power_cycle -- confirmed POR idiom (same as Unit 6)
- Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready -- confirmed signature

## unit_11_step_3_1_methods.py
**wiki refs:**
- entities/flags.md -- SET FLAG (0x02) opcode and flag IDN structure
- entities/write-booster.md -- WriteBooster flush flags
**code refs (gitnexus):**
- Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1 -- confirmed ExecuteCMD.SetFlag() idiom (same as Unit 3)

## unit_12_step_3_2_methods.py
**wiki refs:**
- (None -- pure delay operation)
**code refs (gitnexus):**
- (None -- stdlib only)

## unit_13_step_3_3_methods.py
**wiki refs:**
- concepts/power-management.md -- POR timing and reset type guidance
- entities/power-modes.md -- power mode transitions
**code refs (gitnexus):**
- Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready -- confirmed HW_RESET signature
- Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode -- confirmed vendor mode after POR
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_14_step_3_4_methods.py
**wiki refs:**
- concepts/power-management.md -- SSU Sleep power condition field encoding
- entities/power-modes.md -- Sleep mode transitions and power conditions
**code refs (gitnexus):**
- Script/pattern/read_scan/mutual_fun.py:push_ssu -- confirmed StartStopUnit(CDB) idiom with lun=WellKnownLUN.UFS_DEVICE, power_condition=0x02(Sleep), assign/set_option/enqueue pattern

## unit_15_step_3_5_methods.py
**wiki refs:**
- concepts/power-management.md -- POR timing and reset type guidance
- entities/power-modes.md -- power mode transitions and reset behavior
**code refs (gitnexus):**
- Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready -- confirmed HW_RESET signature
- Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode -- confirmed vendor mode after POR
**review flags:** `TODO-REVIEW-NO-WIKI`

## unit_16_loop_1_wrapper_methods.py
**wiki refs:**
- _NO MATCH_
**code refs (gitnexus):**
- _NO MATCH_


---

## Defaults offered (deterministic — what was injected)

# Defaults offered per unit — DETERMINISTIC (what was INJECTED)

> §1-§3 overrides (UserPrompt/CustomerReq) are ALWAYS injected.
> §4 ModelDefault base is retrieved per step (top-1 topic).
> What the model actually USED = its `# src[wiki]` tags (see retrieval_debug.md).

- unit 01 (step_0_1): overrides=always; modeldefault=hardware_settings
- unit 02 (step_0_2): overrides=always; modeldefault=descriptor_operations
- unit 03 (step_1_1): overrides=always; modeldefault=descriptor_operations
- unit 04 (step_1_2): overrides=always; modeldefault=hardware_settings
- unit 05 (step_1_3): overrides=always; modeldefault=data_operations
- unit 06 (step_1_4): overrides=always; modeldefault=power_management
- unit 07 (step_2_1): overrides=always; modeldefault=hardware_settings
- unit 08 (step_2_2): overrides=always; modeldefault=hardware_settings
- unit 09 (step_2_3): overrides=always; modeldefault=data_operations
- unit 10 (step_2_4): overrides=always; modeldefault=power_management
- unit 11 (step_3_1): overrides=always; modeldefault=descriptor_operations
- unit 12 (step_3_2): overrides=always; modeldefault=NONE
- unit 13 (step_3_3): overrides=always; modeldefault=power_management
- unit 14 (step_3_4): overrides=always; modeldefault=data_operations
- unit 15 (step_3_5): overrides=always; modeldefault=power_management