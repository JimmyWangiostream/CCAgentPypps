# Test Spec: Thermal Protection (D0F1/D0F3) Hot-Only Mode Assert & Recovery Test

## Verification Criterion (VC)
驗證 UFS 裝置在啟用 Hard Thermal Protection (TP_HARD_HOT_ONLY) 且設定極端低溫保護閾值（TD_TOOLOW_AREA_ENTER = 100°C，對應 UFS 內部溫度 180°C）的情境下，當寫入操作觸發熱保護機制時，韌體應進入 Assert 狀態並停止回應（Stuck）。測試需確認：1. 正常寫入與讀取比對成功；2. 觸發保護閾值後的寫入請求會導致 Host 端 TIMEOUT；3. 透過 DME Get 讀取的韌體 Assert Code 必須非 0x0（代表記錄了具體錯誤碼）；4. 執行 HW_RESET 後，未寫入的 LBA 區域資料應保持為預期的 CRC 空值狀態，證明寫入操作被正確中止且未造成資料損壞。

## Test Case (TC) Checkpoints
1. [Case01_Normal_Write_Read_Check]:
   - 動作：
     1. 執行 FormatUnit 於 UFS_DEVICE LUN。
     2. 讀取熱保護閾值（issue_40FA_read_thermal_stuck_threshold）。
     3. 發送 Vendor Command D0F3 將熱保護模式切換為 TP_HARD_HOT_COLD，隨後發送 D0FC 設定 Shipping Mode (Device_state=1, only_in_ram=True)，再發送 D0F3 切換為 TP_HARD_HOT_ONLY 模式。
     4. 發送 Vendor Command D0F1 寫入熱保護閾值：設定 `low_thermal_protection_threshold` 為 180 (對應 UFS 溫度 100°C)，`high_thermal_protection_threshold` 為讀取到的高閾值。
     5. 對 `TestNormalLun` (LUN 0) 的 `TestLBA` (LBA 0) 寫入 4KB 資料。
     6. 記錄寫入資訊並執行 Read Compare (HW_COMPARE) 驗證資料完整性。
   - 預期結果：寫入成功，讀取比對結果為 Pass，確認熱保護閾值設定生效且正常寫入功能無誤。

2. [Case02_Thermal_Assert_Stuck_Check]:
   - 動作：
     1. 發送 Vendor Command D0F1 修改閾值：設定 `low_thermal_protection_threshold` 為讀取到的低閾值，`high_thermal_protection_threshold` 為 80 (對應 UFS 溫度 0°C)。此設定意在模擬極端低溫條件觸發保護。
     2. 嘗試對下一個 LBA (`TestLBA + 4KB`) 寫入 4KB 資料。
     3. 監控寫入命令回應，預期發生 TIMEOUT_EXCEPTIONS。
     4. 清除命令佇列後，透過 `api.get_fw_assert_number()` 讀取韌體 Assert Code。
   - 預期結果：
     - 寫入命令必須觸發 TIMEOUT，證明韌體因熱保護機制進入 Stuck 狀態。
     - 讀取的 Assert Code 必須不等於 0x0。若為 0x0 則視為 Fail，代表韌體未正確記錄 Assert 事件或機制失效。

3. [Case03_Recovery_Data_Integrity_Check]:
   - 動作：
     1. 執行 HW_RESET (透過 `api.init_tester_to_unit_ready` with `powerdown=False`) 恢復裝置。
     2. 對之前嘗試寫入但超時的 LBA (`TestLBA + 4KB`) 執行 Read10 命令，並設定 `sw_cmp` 為 `ExpectedCRC` (0x0)。
   - 預期結果：讀取成功，且資料內容必須與預期的 CRC 0x0 相符。這證明在熱保護觸發導致韌體 Assert 期間，該 LBA 的寫入操作被完全中止，未留下任何部分寫入的髒資料，確保資料一致性。