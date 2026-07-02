# Test Spec: UFS FTL Internal State Consistency & Hardware Mapping Verification

## Verification Criterion (VC)
驗證 UFS 韌體內部 FTL 狀態機與硬體實體配置的一致性：
1. **Index 0 (EC Table)**：確認 SRAM 中的 Erase Count (EC) 與 FlashSetting 中的 Hidden Block EC 與 MicronVU 軟體計算值完全一致，確保韌體對 NAND 壽命計數的讀取無誤。
2. **Index 3 (CIS Code)**：確認韌體代碼 (FW Code) 的物理地址 (Channel, CE, Plane, Block, Page) 與 FlashSetting 中的 CIS 區塊配置一致，且 `TempCodeValidPlaneBitmap` 與 `gaFwTmpCodeBlkPackAddr` 陣列與韌體內部變數同步，確保韌體載入與備份區塊映射正確。
3. **Index 6 (BBT Info)**：確認 Bad Block Table (BBT) 區塊的 Sub_VB_version、First_empty_page (固定為 9)、Block_count (固定為 1) 及物理位置 (CE, Plane, Block) 與透過 Direct Read 搜尋到的 BBT 標記 (0x8B) 完全吻合。
4. **Index 7 (VB Type & Mapping)**：在執行 Normal, EM1, WriteBooster 三種 LUN 的連續寫入後，確認 FTL 內部 VB 列表 (VB List) 中的 Group ID、Access Mode 與 Dirty 狀態，經轉換後的 `VB_type` 欄位數值與韌體內部 `all_vb_type` 結構體完全一致，驗證 L2P 與 VB 管理邏輯的數據完整性。
5. **Index 8 (ICS Bad Block)**：確認 ICS (Internal Control Structure) 中的 Bad Block 列表索引順序正確，且每個 VB 的 `Invalid_logical_plane` 與 ICS Table 中的對應欄位數值一致，確保壞塊標記在硬體與韌體間同步。

## Test Case (TC) Checkpoints

1. **[Index0_EC_Table_Consistency_Check]**：
   - 動作：透過 `api.get_flash_setting_buffer()` 取得 FlashSetting 緩衝區，並呼叫 `project_api.get_all_VB_erase_count()` 取得 MicronVU 計算的 VB Erase Count (`erase_cnt_of_vb`) 與 Hidden Block Erase Count。同時呼叫 `api.read_Xmemory` 從 SRAM 讀取 `VB_list_cycle_address` 的原始數據。遍歷所有 VB (0 至 `l52_total_vb_count-1`)，將 SRAM 讀取的 4-byte Little-Endian EC 值與 MicronVU 值比對；同時從 FlashSetting Buffer 偏移量 2284 開始，每 4-byte 讀取 Hidden Block EC 並與 MicronVU 的 `erase_cnt_for_hidden_physical_block` 比對。
   - 預期結果：所有 VB 的 SRAM EC 值必須等於 MicronVU 計算值；所有 Hidden Block 的 FlashSetting EC 值必須等於 MicronVU 計算值。若有任何差異，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體對 NAND 擦除計數器的硬體狀態讀取或軟體維護邏輯存在不一致。

2. **[Index3_CIS_Code_Physical_Address_Check]**：
   - 動作：呼叫 `project_api.get_FW_code_physical_address_information()` 取得韌體內部記錄的 CIS Code 1 與 2 的物理地址資訊。從 `flash_setting_buffer` 解析出 CIS_Block1 與 CIS_Block2 的 Channel, CE, Plane, Block 欄位（Block 由 buffer[30:31] 與 [33:34] 組合而成）。呼叫 `check_CIS_code` 驗證韌體內部 CISCode 物件的 Channel, CE, Plane, Block, Page 是否與從 FlashSetting 解析出的值完全匹配。接著，呼叫 `api.read_fw_value` 讀取韌體變數 `gwFwTmpCodeVbPlnBitmap` 與 `gaFwTmpCodeBlkPackAddr[0-11]`，並與 `fw_code_physical_address` 物件中的 `TempCodeValidPlaneBitmap` 與 `TempCodePhysicalAddress` 陣列進行逐項比對。
   - 預期結果：CIS_Block1 與 CIS_Block2 的所有物理地址欄位 (Channel, CE, Plane, Block, Page) 必須完全一致；`TempCodeValidPlaneBitmap` 數值必須相等；`gaFwTmpCodeBlkPackAddr` 陣列中的 12 個物理地址必須與 `TempCodePhysicalAddress` 陣列中的對應值完全相等。任何不匹配均觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體代碼映射表與硬體設定衝突。

3. **[Index6_BBT_Block_Info_Check]**：
   - 動作：呼叫 `project_api.get_BBT_physical_block_information()` 取得韌體記錄的 BBT 資訊。呼叫內部函數 `find_bbt_block`，該函數透過 Direct Read 掃描 Block 0 至 20，尋找 FW Spare 區域 (偏移量 `api.DATA_SIZE_4K_BYTE*4 + 4`) 數據為 `0x8B` 的區塊，並返回該區塊的 PCA (CE, Plane, Block)。比對韌體記錄的 `Sub_VB_version` 是否等於找到的 Block 編號；`First_empty_page` 是否等於 `9`；`BBT_block_count` 是否等於 `1`；`Block` 是否等於找到的 Block 編號；`CE` 是否等於找到的 CE；`plane` 是否等於找到的 Plane。
   - 預期結果：`Sub_VB_version` 必須等於找到的 BBT Block 編號；`First_empty_page` 必須嚴格等於 `9`；`BBT_block_count` 必須嚴格等於 `1`；`Block`, `CE`, `plane` 必須與 Direct Read 搜尋到的硬體實體位置完全一致。若 BBT Block 編號大於 20 或找不到 0x8B 標記，觸發 `SIGHTING_PBA_UNEXPECTED`；若數值不匹配，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

4. **[Index7_VB_Type_Mapping_Consistency_Check]**：
   - 動作：首先配置 LUN：LUN 0 (Normal), LUN 1 (EM1), LUN 2 (WriteBooster)。執行連續寫入：LUN 0 寫入 `tlc_vb_size * 2.5`，LUN 1 寫入 `slc_vb_size * 2.5`，LUN 2 在啟用 `WRITEBOOSTER_EN` 旗標後寫入 `slc_vb_size * 2.5`。寫入完成後，呼叫 `project_api.get_all_VB_type()` 取得韌體內部 VB 類型結構體，並呼叫 `get_VB_group` 從 API 獲取 FTL 內部 VB List 的原始數據 (Group, Access Mode, Dirty, Partition)。對於每個 VB，根據其 Group ID (如 `RAIN_SWAP_NO_OBR_BLK`, `PTE_POOL`, `CURRENT_L2_SLC` 等) 與 Access Mode，按照腳本中的硬編碼邏輯 (Hard-coded Logic) 計算預期的 `VB_type` 數值 (例如：`LIST_BLK` 對應 16, `REVOKE_BLK` 對應 20, `CURRENT_L2_SLC` 對應 14, `FREE_BLK_QUEUE_MLC` 對應 0 等)。最後呼叫 `compare_VB_type_criteria` 將計算出的預期 `VB_type` 與韌體內部 `all_vb_type` 中的實際值進行逐欄位 (Start Bit, End Bit) 比對。
   - 預期結果：對於所有 VB，經邏輯轉換後的預期 `VB_type` 欄位數值必須與韌體內部 `all_vb_type` 結構體中的實際值完全一致。這驗證了在執行不同類型 LUN 寫入後，FTL 的 VB 狀態機 (VB Group, Access Mode) 與韌體內部維護的 VB 類型表 (VB Type Table) 保持嚴格同步。任何欄位不匹配觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

5. **[Index8_ICS_Bad_Block_Sync_Check]**：
   - 動作：呼叫 `project_api.get_ics_bad_block()` 取得韌體記錄的 ICS Bad Block 列表。驗證列表中每個元素的 `VB_index` 是否按順序遞增 (0, 1, 2...)。接著呼叫 `api.get_ics_table()` 取得 ICS Table 的原始 Payload。遍歷 ICS Table，對於每個有效的 ICS Unit (當 `ICS_block_index` 不等於 `0xFFFF` 時)，提取 `ICS_block_index` 作為 VB 索引，並讀取該 VB 在 ICS Bad Block 列表中的 `invalid_VB_plane` 值，與 ICS Table 中對應的 `Invalid_logical_plane` 值進行比對。
   - 預期結果：ICS Bad Block 列表的 `VB_index` 必須嚴格按順序排列；對於每個壞塊 VB，韌體記錄的 `invalid_VB_plane` 必須與 ICS Table 中的 `Invalid_logical_plane` 數值完全相等。若索引順序錯誤或平面標記不一致，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表壞塊標記在韌體邏輯層與 ICS 硬體控制層之間不同步。