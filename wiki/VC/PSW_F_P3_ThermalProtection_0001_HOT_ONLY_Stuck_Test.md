# Test Spec: Thermal Protection VU D0F1 Stuck Area Entry & FW Assert Recovery Test

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command (VU) 0xD0F1 修改熱保護閾值後，硬體溫度模擬與韌體狀態機的反饋機制：Case 01 確認在正常溫度閾值下，4KB 寫入與讀取比較（HW_COMPARE）成功，證明基礎 I/O 功能正常；Case 02 確認當透過 VU 0xD0F1 將 `TD_SUPER_HIGH_AREA_ENTER` 設定為 0°C（對應 UFS 內部溫度 80°C）且 `TD_TOOLOW_AREA_ENTER` 設定為 100°C（對應 UFS 內部溫度 180°C）後，觸發寫入操作時，韌體應進入 Thermal Stuck 保護狀態並掛起（Stuck），導致寫入命令超時（TIMEOUT）；隨後驗證韌體是否正確記錄 Assert Code（非 0x0），並透過 HW_RESET 或 RESET_N 硬體重啟後，確認未寫入區域的資料保持未定義狀態（CRC 匹配預期空值），證明保護機制生效且重啟後狀態恢復正常。

## Test Case (TC) Checkpoints
1. [Case01_Baseline_IO_Verification]：
   - 動作：執行 FormatUnit 初始化 UFS_DEVICE LUN。讀取熱保護閾值暫存器。設定 `low_thermal_protection_threshold` 為 180（UFS 溫度 180°C，即實際 100°C）及 `high_thermal_protection_threshold` 為高閾值。透過 VU 0xD0F1 寫入此閾值。針對 LUN 0 的 LBA 0 寫入 4KB 資料（Write10, FUA=1）。保存寫入記錄並執行 Read10 進行 HW_COMPARE 驗證。
   - 預期結果：寫入與讀取比較成功，無超時或錯誤。證明在當前設定的高溫閾值下（100°C 實際溫度），熱保護機制未觸發，I/O 路徑正常運作。

2. [Case02_ThermalStuck_Trigger_Check]：
   - 動作：透過 VU 0xD0F1 修改熱保護閾值：將 `low_thermal_protection_threshold` 設為低閾值（對應實際低溫），並將 `high_thermal_protection_threshold` 設為 80（UFS 內部溫度 80°C，即實際 0°C）。針對 LUN 0 的下一個 LBA（LBA 0 + 4KB）發送 4KB 寫入命令（Write10, FUA=1）。監控命令回應，預期發生超時（TIMEOUT_EXCEPTIONS）。
   - 預期結果：寫入命令必須觸發超時異常。這代表韌體檢測到模擬溫度超過 `TD_SUPER_HIGH_AREA_ENTER` 閾值，觸發 Thermal Stuck 保護，阻止了資料寫入並掛起命令處理。

3. [Case03_FW_Assert_Code_Validation]：
   - 動作：在寫入超時後，立即透過 DME Get 命令讀取韌體 Assert Code (`api.get_fw_assert_number()`)。
   - 預期結果：讀回的 Assert Code 必須不等於 0x0。若為 0x0，則測試失敗（SIGHTING_FAIL_DATA_COMPARE_FAIL）。此步驟驗證韌體在觸發熱保護掛起時，正確記錄了特定的 Assert 事件代碼，而非無反應或錯誤代碼。

4. [Case04_Recovery_With_HW_RESET]：
   - 動作：執行 HW_RESET（`api.init_tester_to_unit_ready` with `powerdown=False`）。重啟後，針對之前嘗試寫入但超時的 LBA（LBA 0 + 4KB）發送 Read10 命令，並設定預期 CRC 為 0 (`ExpectedCRC = 0`)。
   - 預期結果：讀取命令成功完成。由於之前的寫入因熱保護而掛起/失敗，該 LBA 區域應保留舊資料或為未初始化狀態，其 CRC 值應與預期值 0 匹配。這證明 HW_RESET 成功恢復了裝置狀態，且熱保護機制未導致資料損壞或永久掛起。

5. [Case05_Recovery_With_RESET_N]：
   - 動作：重複 Case02 的閾值設定與寫入超時觸發。隨後執行 RESET_N 硬體重啟（`manual_rst_n()`）。重啟後，針對同一個 LBA 發送 Read10 命令，並設定預期 CRC 為 0。
   - 預期結果：讀取命令成功完成，且 CRC 匹配預期值 0。這證明 RESET_N 信號也能有效清除熱保護掛起狀態，恢復裝置至 Unit Ready 狀態，且資料完整性未受影響。