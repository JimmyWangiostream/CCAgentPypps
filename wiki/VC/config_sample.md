# Test Spec: UFS 4.1 Configuration Descriptor Write & Read-Back Verification

## Verification Criterion (VC)
驗證 UFS 裝置在接收 `WRITE DESCRIPTOR` 命令後，內部 Configuration Descriptor 的硬體狀態與韌體配置是否正確寫入，並透過 `READ DESCRIPTOR` 確認資料的一致性與完整性：
1. **Header 層級驗證**：確認 `CONFIGURATION` 描述符（Index 3, Last Descriptor）的 Header 欄位（如 Boot Enable, RPMB Region Enable, Write Booster Type 等）是否被正確鎖存。
2. **LUN 配置驗證**：確認四個 LUN (0-3) 的 Unit Descriptor 配置是否正確生效，特別是 LUN 0 (Normal/Thin Provisioning), LUN 1 (Boot A/Enhanced), LUN 2 (Boot B/Enhanced), LUN 3 (Normal) 的 `Memory Type`, `Alloc Units`, `Boot LUN ID` 及 `Write Protect` 狀態。
3. **Disable LUN 驗證**：確認 LUN 4-7 被正確設定為 `DISABLE` 且 `Alloc Units` 歸零。
4. **資料一致性驗證**：透過讀回描述符，比對 Header 與 Unit 欄位的數值是否與寫入時完全一致，確保控制器內部暫存器與非揮發性配置儲存區（若適用）的同步正確性。

## Test Case (TC) Checkpoints
1. [Config_Write_Step1]：
   - 動作：透過 `ExecuteCMD.WriteDescriptor()` 發送 `WRITE DESCRIPTOR` 命令，目標為 `DescriptorIDN.CONFIGURATION`，Index 設為 3 (最後一個描述符)，Selector 為 0x00，Length 為 0xE6。
   - 預期結果：命令執行成功，控制器接受配置請求，內部 Configuration Descriptor 暫存器開始更新。

2. [Config_Data_Payload_Verification]：
   - 動作：在 `step1` 中構建 `api.ConfigDescriptor410` 物件並透過 `cmd.set_desc(desc)` 設定 payload，隨後執行 `ExecuteCMD.send()`。具體寫入內容如下：
     - **Header**: `b2_conf_desc_continue` = DISABLE, `b3_boot_enable` = BOOT_ENABLE, `b4_descr_access_en` = DISABLE, `b5_init_power_mode` = ACTIVE, `b6_high_priority_lun` = ALL_LUN_SAME_PRIORITY, `b7_secure_removal_type` = BY_PHYSICAL_ERASE, `b8_init_active_icc_level` = LVL_00, `b11_hpb_control` = 0, `b12_rpmb_region_enable` = REGION_0-3_ENABLE, `b13-b15_rpmb_region_size` = 8, `b16_write_booster_preserve` = DISABLE, `b17_write_booster_type` = DEDICATED, `l18_shared_buffer_alloc` = 0。
     - **LUN 0 (Index 0)**: `b0_lu_enable` = ENABLE, `b1_boot_lun_id` = NOT_BOOTABLE, `b2_lu_write_protect` = NOT_WRITE_PROTECTED, `b3_memory_type` = NORMAL, `l4_num_alloc_units` = 60016, `b8_data_reliability` = LUN_NOT_PROTECTED, `b9_logical_block_size` = SIZE_4KB, `b10_provisioning_type` = THIN_PROVISIONING_ERASE。
     - **LUN 1 (Index 1)**: `b0_lu_enable` = ENABLE, `b1_boot_lun_id` = BOOT_LUN_A, `b2_lu_write_protect` = NOT_WRITE_PROTECTED, `b3_memory_type` = ENHANCED_1, `l4_num_alloc_units` = 100, `b8_data_reliability` = LUN_NOT_PROTECTED, `b9_logical_block_size` = SIZE_4KB, `b10_provisioning_type` = THIN_PROVISIONING_ERASE。
     - **LUN 2 (Index 2)**: `b0_lu_enable` = ENABLE, `b1_boot_lun_id` = BOOT_LUN_B, `b2_lu_write_protect` = NOT_WRITE_PROTECTED, `b3_memory_type` = ENHANCED_1, `l4_num_alloc_units` = 100, `b8_data_reliability` = LUN_NOT_PROTECTED, `b9_logical_block_size` = SIZE_4KB, `b10_provisioning_type` = THIN_PROVISIONING_ERASE。
     - **LUN 3 (Index 3)**: `b0_lu_enable` = ENABLE, `b1_boot_lun_id` = NOT_BOOTABLE, `b2_lu_write_protect` = NOT_WRITE_PROTECTED, `b3_memory_type` = NORMAL, `l4_num_alloc_units` = 200, `b8_data_reliability` = LUN_NOT_PROTECTED, `b9_logical_block_size` = SIZE_4KB, `b10_provisioning_type` = THIN_PROVISIONING_ERASE。
     - **LUN 4-7 (Index 4-7)**: `b0_lu_enable` = DISABLE, `l4_num_alloc_units` = 0, `b9_logical_block_size` = 0。
   - 預期結果：UFS 裝置必須正確解析並鎖存上述所有欄位值。特別是 `b12_rpmb_region_enable` 必須同時啟用 Region 0-3，且 `b17_write_booster_type` 必須設定為 DEDICATED。

3. [Config_Readback_Step2]：
   - 動作：執行 `api.get_config_descriptors()` 觸發 `READ DESCRIPTOR` 命令，讀取當前 Configuration Descriptor，並透過 `printout_config_desc_header` 與 `printout_config_desc_unit` 記錄所有欄位值。
   - 預期結果：讀回的 `cfg_desc_list` 必須包含一個有效的 `ConfigDescriptor410` 物件。

4. [Readback_Data_Integrity_Check]：
   - 動作：比對讀回的 Header 與 Unit 欄位數值與 Step 2 中寫入的預期值。
   - 預期結果：
     - **Header**: `b2_conf_desc_continue` 必須為 DISABLE (因為是 Index 3)；`b3_boot_enable` 必須為 BOOT_ENABLE；`b12_rpmb_region_enable` 必須為 `REGION_0_ENABLE | REGION_1_ENABLE | REGION_2_ENABLE | REGION_3_ENABLE`；`b17_write_booster_type` 必須為 DEDICATED。
     - **LUN 0**: `b3_memory_type` 必須為 NORMAL；`l4_num_alloc_units` 必須等於 60016；`b1_boot_lun_id` 必須為 NOT_BOOTABLE。
     - **LUN 1**: `b3_memory_type` 必須為 ENHANCED_1；`l4_num_alloc_units` 必須等於 100；`b1_boot_lun_id` 必須為 BOOT_LUN_A。
     - **LUN 2**: `b3_memory_type` 必須為 ENHANCED_1；`l4_num_alloc_units` 必須等於 100；`b1_boot_lun_id` 必須為 BOOT_LUN_B。
     - **LUN 3**: `b3_memory_type` 必須為 NORMAL；`l4_num_alloc_units` 必須等於 200；`b1_boot_lun_id` 必須為 NOT_BOOTABLE。
     - **LUN 4-7**: `b0_lu_enable` 必須為 DISABLE；`l4_num_alloc_units` 必須為 0。
     - 任何欄位數值與上述預期不符，皆視為測試失敗，代表韌體配置寫入或讀取機制存在 Bug。