# Test Spec: UFS Device Geometry Descriptor & Feature Capability Verification

## Verification Criterion (VC)
驗證 UFS 裝置在初始化或查詢階段，透過 `GET GEOMETRY DESCRIPTOR` (Opcode 0x00) 指令正確回傳硬體幾何結構與功能支援狀態：
1. **幾何參數完整性**：確認韌體回傳的 `GeometryDescriptor410` 結構體中，關鍵容量與區塊大小欄位（如 `b0_length`, `q4_total_raw_device_capacity`, `l68_optimal_logical_block_size`）符合硬體規格定義，且無解析度錯誤。
2. **LUN 配置驗證**：確認 `b12_max_number_lu` 欄位數值與 `GET MAX NUMBER OF LUN` 指令回傳的實際 LUN 數量一致，驗證邏輯 LUN 到實體 LUN 的映射上限。
3. **資料排序與記憶體類型支援**：解析 `b25_data_ordering` 欄位以確認裝置是否支援 Out-of-Order Data Transfer；解析 `w30_supported_memory_types` 位元欄位，精確驗證裝置硬體是否具備 NORMAL, SYSTEM_CODE, NON_PERSISTENT, ENHANCED_1~4, 以及 RPMB 等特定記憶體區域的存取能力，並確保位元遮罩比對邏輯正確反映硬體 Capabilities。

## Test Case (TC) Checkpoints
1. [Geometry_Descriptor_Read_and_Parse]：
   - 動作：執行 `api.get_geometry_descriptor()` 指令讀取裝置回傳的幾何描述元，並將其強轉為 `api.GeometryDescriptor410` 型別。記錄並輸出結構體中所有欄位，特別關注 `b0_length` (結構體長度), `q4_total_raw_device_capacity` (總原始容量), `l13_segment_size` (區段大小), `b17_allocation_unit_size` (配置單元大小), `b18_min_addr_block_size` (最小地址區塊大小), `b19_optimal_read_block_size` (最佳讀取區塊大小), `b20_optimal_write_block_size` (最佳寫入區塊大小), 以及 `l68_optimal_logical_block_size` (最佳邏輯區塊大小)。
   - 預期結果：指令回傳狀態碼為 Success；結構體欄位數值必須為有效的非零整數（除非該功能未實作），且 `b0_length` 必須等於 `GeometryDescriptor410` 定義的預期結構體大小，確保資料結構解析無偏移。

2. [LUN_Max_Number_Verification]：
   - 動作：執行 `api.get_max_number_of_lun()` 取得當前配置的 LUN 總數，並與 `GeometryDescriptor` 中的 `b12_max_number_lu` 欄位數值進行比對。
   - 預期結果：`api.get_max_number_of_lun()` 回傳的整數值必須嚴格等於 `desc.b12_max_number_lu`，確認韌體報告的邏輯 LUN 數量與幾何描述元中宣告的最大 LUN 數量一致。

3. [Data_Ordering_Capability_Check]：
   - 動作：從 `GeometryDescriptor` 讀取 `b25_data_ordering` 欄位，並透過 `api.SupportedOutOfOrderDataTransfer(desc.b25_data_ordering)` 進行解碼與驗證。
   - 預期結果：解碼後的 `out_of_order_type` 必須為 `api.SupportedOutOfOrderDataTransfer` 列舉中的有效成員（如 `NORMAL`, `OUT_OF_ORDER` 等），且其數值與 `b25` 欄位原始位元值對應，確認裝置支援的資料排序機制符合 UFS 規範定義。

4. [Supported_Memory_Types_Bitmap_Validation]：
   - 動作：讀取 `GeometryDescriptor` 中的 `w30_supported_memory_types` 位元欄位，並針對以下特定記憶體類型執行位元遮罩 (`&`) 檢查：`NORMAL`, `SYSTEM_CODE`, `NON_PERSISTENT`, `ENHANCED_1`, `ENHANCED_2`, `ENHANCED_3`, `ENHANCED_4`, `RPMB`。記錄所有位元為 1 的記憶體類型名稱。
   - 預期結果：
     - 若 `w30 & api.SupportedMemoryType.NORMAL` 為真，則 `NORMAL` 必須出現在支援列表中。
     - 若 `w30 & api.SupportedMemoryType.RPMB` 為真，則 `RPMB` 必須出現在支援列表中。
     - 支援列表中的類型必須與 `w30` 欄位中實際設為 1 的位元位置完全吻合，無遺漏或錯誤包含，確認硬體對不同記憶體區域（如系統碼區、非揮發性區、增強區、RPMB 區）的存取權限與硬體實作狀態正確反映。