# Test Spec: UFS FTL Wear Leveling & Global EC Threshold Configuration Test

## Verification Criterion (VC)
驗證 UFS 韌體在動態配置 LUN 類型（Normal/EM1/WB）並執行寫入後，FTL 層級 Wear Leveling (WL) 資訊的正確性與一致性：
1. **基礎 WL 狀態驗證**：確認在寫入 TLC (LUN0), SLC/EM1 (LUN1), 及 Write Booster (LUN2) 資料後，透過 Vendor Command `0x4098` 讀取的 WL 資訊中，VB List Num 與 Open VB Type 符合預設分組邏輯，且 SWLEnable 為 1。
2. **VB 級別 EC/Version 注入與回讀驗證**：透過 Vendor Command `0x408A` 獲取 FW 配置後，利用 `set_ftl_version` 與 `set_all_VB_erase_count` 在 RAM 中強制設定特定 VB 的 Erase Count (EC) 與 Version 值（隨機 0-300 範圍），並驗證 `0x4098` 回傳的 `EC_data_of_VBs` 與 `VER_data_of_VBs` 是否精確反映注入值，且 Open Type 在 EC 與 Version 結構中保持一致。
3. **Global Version 邊界與重置驗證**：驗證當設定 `slc_partition_current_vb_version` 與 `mlc_partition_current_vb_version` 為 `boundaryVersion + 1` 後，再次讀取 `0x4098` 時，`globalVersion_of_static_pool` 與 `globalVersion_of_dynamic_pool` 是否被韌體自動重置為 0，確認 Global Version 的環繞或重置機制。
4. **Global EC Threshold 設定驗證**：透過 Vendor Command `0xC072` 設定靜態 WL 的 Global EC 閾值（包含 Static/Dynamic/ICS Pool 的 Global EC 及 TH1/TH2 閾值），並驗證 `0x4098` 回傳的全域計數器與閾值是否與注入值完全一致。
5. **Enhanced Health Report 一致性驗證**：確認 `0x40FE` 讀取的 Enhanced Health Report 中，各 Partition (Table/EM1/TLC) 的 Exhausted Life、Min/Max/Avg Block Erase Count 與 `0x4098` 讀取的 WL 資訊及 VB 級別 EC 統計結果完全吻合，並驗證 Hidden Pool、FW Blocks、BBT、Pointer 區塊的最大 EC 值記錄正確。

## Test Case (TC) Checkpoints

1. [LUN_Config_WL_Baseline_Check]：
   - 動作：配置 LUN 0 為 Normal (TLC), LUN 1 為 Enhanced 1 (SLC), LUN 2 為 Write Booster (SLC)。分別對 LUN 0 寫入 `tlc_vb_size * 1.5` 大小資料，對 LUN 1 寫入 `slc_vb_size * 1.5` 大小資料，並啟用 Write Booster 後對 LUN 2 寫入相同大小資料。執行 `0x4098` 獲取 WL 資訊 (`wear_leveling_A`)，並解析 `EC_data_of_VBs` 中的 `VBListNum` 與 `OpenVBType`。
   - 預期結果：`wear_leveling_A` 的 `data_size` 為 `12KB - 4`，`size_in_byte_of_following_data` 為 304，`SWLEnable` 為 1，`Version_delta_Threshold` 為 500。每個 VB 的 `VBListNum` 必須匹配其 Group Type 的預設 VBList 映射，且 `OpenVBType` 必須匹配預設 Open Type 映射，否則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [VB_EC_Version_RAM_Injection_Check]：
   - 動作：透過 `0x408A` 獲取 FW 配置以確定 Static/Dynamic/Table Pool 的起始 VB。在 RAM 中為所有 VB 設定 EC 為 `0xFFFFFFFF`，但對 Table Pool 起始 VB 隨機設定 EC (0-300)，對 Static Pool 起始 VB 隨機設定 Version (0-300)。同時設定 Hidden VB 的 EC。執行 `set_ftl_version` 設定 Partition 級別 Version，並執行 `set_all_VB_erase_count` 將上述 EC 寫入 RAM。再次執行 `0x4098` 獲取 WL 資訊 (`wear_leveling_B`)。
   - 預期結果：對於已設定非 `0xFFFFFFFF` EC 的 VB，`wear_leveling_B.EC_data_of_VBs[vb].EC.value` 必須等於注入的隨機 EC 值。對於已設定非 `0xFFFFFFFF` Version 的 VB，`wear_leveling_B.VER_data_of_VBs[vb].version.value` 必須等於注入的隨機 Version 值。且對於每個 VB，其 `EC_data_of_VBs.OpenVBType` 必須等於 `VER_data_of_VBs.open_type`。若 `OpenVBType` 不等於 `OTHER`，則該 Type 對應的 `version_of_open_VBs` 列表中的值必須等於該 Type 下任意一個 VB 的 Version 值。

3. [Global_Version_Reset_Check]：
   - 動作：從 `wear_leveling_B` 讀取 `boundaryVersion_of_static_pool` 與 `boundaryVersion_of_dynamic_pool`，將 `slc_partition_current_vb_version` 與 `mlc_partition_current_vb_version` 設定為 `boundaryVersion + 1`。執行 `set_ftl_version` 更新版本。再次執行 `0x4098` 獲取 WL 資訊 (`wear_leveling_C`)。
   - 預期結果：`wear_leveling_C.globalVersion_of_static_pool` 必須等於 0，且 `wear_leveling_C.globalVersion_of_dynamic_pool` 必須等於 0。這驗證了當 Partition 級別 Version 超過 Boundary Version 時，Global Version 會被韌體重置為 0。

4. [Global_EC_Threshold_Setting_Check]：
   - 動作：從 `wear_leveling_C` 讀取所有 Global EC 計數器與 EC Gap Delta Threshold (TH1/TH2) 的當前值，並分別加 1 作為新的目標值。透過 Vendor Command `0xC072` 將這些值設定為靜態 Wear Leveling 的全域閾值。再次執行 `0x4098` 獲取 WL 資訊 (`wear_leveling_D`)。
   - 預期結果：`wear_leveling_D` 中的以下欄位必須精確等於注入的 `Current_Value + 1`：
     - `Global_Erase_Counter_of_static_pool`
     - `Global_Erase_Counter_of_dynamic_pool`
     - `Global_Erase_Counter_of_ICS_pool`
     - `Global_Erase_Counter_of_static_pool_for_open_block`
     - `Global_Erase_Counter_of_dynamic_pool_for_open_block`
     - `EC_gap_delta_Threshold_TH1_of_static_pool`
     - `EC_gap_delta_Threshold_TH1_of_dynamic_pool`
     - `EC_gap_delta_Threshold_TH1_of_ICS_pool`
     - `EC_gap_delta_Threshold_TH2_of_static_pool`
     - `EC_gap_delta_Threshold_TH2_of_dynamic_pool`
     - `EC_gap_delta_Threshold_TH2_of_ICS_pool`

5. [Health_Report_WL_Consistency_Check]：
   - 動作：執行 `0x40FE` 讀取 Enhanced Health Report (`health_report_after`)。遍歷所有 VB，根據其 Partition (0:Table, 1:EM1, 2:TLC) 計算該 Partition 內所有 VB 的 Max EC, Min EC, Avg EC 及 Exhausted Life (Table/EM1 分母 3000, TLC 分母 100000)。同時讀取 Hidden Pool, FW Blocks (CIS0/CIS1), BBT, Pointer 的最大 EC 值。
   - 預期結果：
     - **Partition 0 (Table)**: `health_report_after` 的 `exhausted_life_for_slc_table_only` 等於計算值；`min/max/average_block_erase_count_for_slc_table` 等於 Min/Max/Avg EC；`max_erase_counter_0_for_ICS_pool` 等於 Max EC。
     - **Partition 1 (EM1)**: `health_report_after` 的 `exhausted_life_for_em1` 等於計算值；`min/max/average_block_erase_count_for_em1` 等於 Min/Max/Avg EC；`max_erase_counter_0_for_Static_pool` 等於 Max EC。
     - **Partition 2 (TLC)**: `health_report_after` 的 `exhausted_life_for_tlc` 等於計算值；`min/max/average_block_erase_count_for_tlc` 等於 Min/Max/Avg EC；`max_erase_counter_0_for_Dynamic_pool` 等於 Max EC。
     - **特殊區塊**: `ec_hidden_pool` 等於所有 Hidden Physical Block EC 總和；`fw_blocks_max_ec` 等於 CIS0/CIS1 中較大的 EC 值；`bbt_blocks_max_ec` 等於 BBT 區塊最大 EC；`pointer_blocks_max_ec` 等於 Pointer 區塊最大 EC。