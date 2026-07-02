# Test Spec: UFS Unit Descriptor Retrieval & Field Validation (0001)

## Verification Criterion (VC)
驗證 UFS 主機控制器或韌體介面能否正確透過 `Get Unit Descriptor` 命令讀取 LUN 0 至 LUN 31 的硬體配置描述符，並確認關鍵硬體參數（如 LUN 使能狀態、Boot LUN ID、寫入保護、記憶體類型、HPB 區域配置及 Write Booster 緩衝區分配）的數據完整性與邏輯一致性。此測試旨在確保韌體層對 UFS 設備物理層資源映射的正確性，特別是針對 HPB (Host Performance Booster) 和 Write Booster 等進階功能的硬體狀態註冊。

## Test Case (TC) Checkpoints
1. [LUN_Descriptor_Range_Read_Check]：
   - 動作：透過 `api.get_unit_descriptor(unit_idx)` API 迴圈讀取 LUN Index 從 0 到 31 的 Unit Descriptor 數據，並針對每個讀回的 `unit_desc` 物件，記錄其結構體中的具體欄位數值。
   - 預期結果：所有 32 個 LUN 的 Descriptor 讀取必須成功，無通訊錯誤或逾時，且返回的數據結構完整。

2. [LUN_Enable_Boot_LUN_ID_Check]：
   - 動作：檢查每個 LUN Descriptor 中的 `b3_lu_enable` 欄位，並對應 `api.LUNEnable` 枚舉值確認 LUN 是否處於 Active 狀態；同時檢查 `b4_boot_lun_id` 欄位，對應 `api.BootLUNID` 枚舉值確認 Boot LUN 的硬體設定。
   - 預期結果：`b3_lu_enable` 必須正確反映該 LUN 在硬體層是否被啟用（例如 Normal LUN 應為 Enable，Reserved LUN 可能為 Disable）；`b4_boot_lun_id` 必須與設備實際配置的 Boot LUN 硬體設定一致，確保韌體能正確識別啟動路徑。

3. [Write_Protect_Memory_Type_Check]：
   - 動作：讀取 `b5_lu_write_protect` 欄位並對應 `api.LUNWriteProtect` 枚舉值，確認 LUN 的寫入保護狀態；讀取 `b8_memory_type` 欄位並對應 `api.MemoryType` 枚舉值，確認該 LUN 使用的快閃記憶體類型（如 SLC/MLC/TLC/QLC 或特定 Vendor 定義類型）。
   - 預期結果：`b5_lu_write_protect` 必須與設備當前設定的寫保護狀態相符（例如 Firmware LUN 通常為 Protected）；`b8_memory_type` 必須反映該 LUN 對應的物理快閃晶片類型，確保韌體能根據記憶體特性調整 ECC 強度或壽命管理策略。

4. [HPB_WriteBooster_Configuration_Check]：
   - 動作：讀取 HPB 相關硬體參數：`w35_lu_max_active_hpb_regions`（最大活躍 HPB 區域數）、`w37_hpb_pinned_region_start_idx`（固定區域起始索引）、`w39_num_hpb_pinned_regions`（固定區域數量）；同時讀取 `l41_lu_num_write_booster_buffer_alloc_units`（Write Booster 緩衝區分配單位數）。
   - 預期結果：HPB 參數必須符合設備硬體支援的規格上限，且 `w37` 與 `w39` 的組合必須邏輯自洽（例如起始索引 + 數量 <= 總區域數）；`l41` 數值必須大於 0 或為 0（若未啟用 Write Booster），且該數值必須與設備實際分配的 Write Booster SRAM/DRAM 緩衝區大小成正比，確保韌體能正確計算寫入放大率與緩衝區管理閾值。

5. [Capacity_Erase_Block_Check]：
   - 動作：讀取 `q11_logical_block_count`（邏輯區塊總數）與 `l19_erase_block_size`（擦除區塊大小，單位為邏輯區塊）。
   - 預期結果：`q11` 必須等於設備標稱容量除以邏輯區塊大小（通常 512B 或 4KB）；`l19` 必須為 2 的冪次方，且 `q11 * l19` 必須小於或等於物理快閃總容量，確保韌體計算 LBA 到 PBA 映射時的地址空間不會溢出。