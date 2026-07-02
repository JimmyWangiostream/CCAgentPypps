# Test Spec: UFS Vendor Command OTP & BBT Consistency Verification

## Verification Criterion (VC)
驗證 UFS 裝置在生產測試或維護階段，透過 Vendor Command (VC) 讀取的 OTP (One-Time Programmable) 備份區塊 (BB) 資料與 Flash 實體層直接讀取的 BBT (Bad Block Table) 資料之間的一致性：
1. **OTP 內部一致性**：驗證 OTP Page 0 (Full BB), Page 1 (Top Deck BB), Page 2 (Bottom Deck BB) 之間的邏輯對應關係。具體而言，Page 1 與 Page 2 必須完全相同（代表 Top/Bottom Deck 備份頁一致），且 Page 0 必須與 Page 1 內容完全一致（代表 Full BB 與 Deck 備份頁一致）。
2. **OTP 與實體 BBT 一致性**：驗證從 OTP 解析出的 Die 級壞塊資訊（透過 `parse_die_data` 解析 0xFFF0-0xFFF3 標記及數據）與透過 Vendor Command 0x4097 獲取物理區塊資訊後，對指定 CE/Plane 進行 Direct Read 所獲取的 BBT 狀態（透過 `format_direct_read_bbt` 解析 spare area 中 0x04 標記）必須完全吻合。此驗證確保韌體維護的邏輯備份與 Flash 介面的實體狀態無偏差。

## Test Case (TC) Checkpoints
1. [OTP_Read_and_Internal_Consistency_Check]：
   - 動作：
     1. 透過 `project_api.issue_40BC_get_OTP` 分別讀取 OTP Page Index 0, 1, 2 的資料，並儲存為 `otp[0]`, `otp[1]`, `otp[2]`。
     2. 將讀取的資料 dump 至檔案以便後續分析。
     3. 執行比較檢查：首先比對 `otp[1]` (Top Deck) 與 `otp[2]` (Bottom Deck) 是否相等；若不相等則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     4. 接著比對 `otp[0]` (Full BB) 與 `otp[1]` (Top Deck) 是否相等；若不相等則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
   - 預期結果：
     - `otp[1]` 必須等於 `otp[2]`，確認 Top Deck 與 Bottom Deck 的備份頁數據一致。
     - `otp[0]` 必須等於 `otp[1]`，確認 Full BB 頁數據與 Deck 備份頁數據一致。
     - 若上述任一比較失敗，測試應立即終止並標記為 Fail，代表 OTP 內部備份機制異常或資料損毀。

2. [BBT_Physical_Read_and_OTP_Consistency_Check]：
   - 動作：
     1. 透過 `project_api.get_BBT_physical_block_information` 獲取當前 BBT 的物理區塊資訊，提取 `Block`, `CE` (Chip Enable), `Plane` 參數，並組裝為 `PCA` (Physical Command Argument) 結構。
     2. 使用 `api.direct_read` 針對上述 PCA 指定的位置，讀取長度為 `4 * api.BLOCK4K_SIZE_4K_BYTE` 的資料，並包含 FW Spare Area (`include_FW_spare=True`)。
     3. 將 OTP Page 0 的原始二進位資料透過 `parse_die_data` 函數解析，該函數識別 0xFFF0-0xFFF3 為 Die 標記，並收集後續數據生成 `otp_dict0`。
     4. 將 Direct Read 獲取的 BBT 資料透過 `format_direct_read_bbt` 函數解析，該函數掃描 spare area 中 byte 值低 4 位元或高 4 位元為 0x04 的標記，計算對應的 VB (Virtual Block) 與 Plane，生成 `direct_read_bbt_dict`。
     5. 比對 `otp_dict0` 與 `direct_read_bbt_dict` 是否完全相等。
   - 預期結果：
     - `otp_dict0` 必須等於 `direct_read_bbt_dict`。
     - 這意味著從 OTP 解析出的 Die 級壞塊列表，與從 Flash 實體 Spare Area 直接讀取並解析出的壞塊狀態完全一致。
     - 若不相等，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體維護的 OTP 備份與 Flash 實體 BBT 狀態不同步，存在潛在的資料完整性風險。