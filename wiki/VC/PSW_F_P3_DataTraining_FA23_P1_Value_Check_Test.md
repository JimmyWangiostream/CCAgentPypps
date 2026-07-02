# Test Spec: UFS NAND Temperature-Dependent Data Training VREF Verification

## Verification Criterion (VC)
驗證 UFS 控制器在 NAND Flash 溫度變化時，韌體（FW）能否正確根據硬體設定的 `LT_CE0_TX_VREF`、`CT_CE0_TX_VREF` 及 `HT_CE0_TX_VREF` 動態調整內部數據訓練（Data Training）的參考電壓值。測試邏輯涵蓋三個階段：1) 基準狀態確認，確保初始 HW Setting 與 FW 讀取的溫度特徵值一致；2) 異常溫度假設驗證，透過 Vendor Command `D08A` 強制設定虛構的低溫（-11°C）與高溫（100°C），並修改 HW Setting 中的 VREF 值，確認 FW 透過 Vendor Command `4022` 回報的 Data Training 特徵值（Feature 0x23, Byte 8）是否嚴格對應於設定後的 VREF 值（公式為 `VREF << 1`）；3) 環境恢復驗證，確認將 HW Setting 與溫度恢復至初始狀態後，FW 回報的特徵值亦同步恢復至基準值，證明溫度與 VREF 的映射關係具有可逆性與穩定性。

## Test Case (TC) Checkpoints
1. [Baseline_HW_FW_Consistency_Check]：
   - 動作：透過 `api.HwSetting` 從裝置讀取初始的 `LT_CE0_TX_VREF` (lt_ce0)、`CT_CE0_TX_VREF` (ct_ce0) 與 `HT_CE0_TX_VREF` (ht_ce0)。接著呼叫 `project_api.issue_4022_to_get_NAND_feature(0, 0x23)` 取得 NAND Feature 的 Payload，並提取索引為 8 的 Byte 值 (nand_feature_tmp)。
   - 預期結果：`nand_feature_tmp` 必須嚴格等於 `(ct_ce0 << 1)`。此步驟驗證在常溫基準下，FW 內部記錄的 Data Training 溫度特徵值與硬體設定的中心溫度 VREF 保持正確的位移對應關係，排除初始配置錯誤。

2. [Low_Temp_VREF_Mapping_Check]：
   - 動作：計算預期低溫 VREF 值 `expected_lt_ce0 = lt_ce0 + 1`。透過 `hw_setting.set_local_val` 將 `LT_CE0_TX_VREF` 設定為 `expected_lt_ce0`，並執行 `hw_setting.set_to_device` 寫入硬體。接著呼叫 `self.set_temp(-11)` 發送 Vendor Command `D08A` 設定虛構的低溫環境（Payload 為 signed 16-bit -11）。最後再次呼叫 `issue_4022_to_get_NAND_feature(0, 0x23)` 取得新的 Payload Byte 8 值。
   - 預期結果：取得的 Payload Byte 8 值必須嚴格等於 `(expected_lt_ce0 << 1)`。此結果證明當硬體 VREF 設定改變且溫度條件觸發時，FW 能正確反映低溫區間的 Data Training 參數變化。

3. [High_Temp_VREF_Mapping_Check]：
   - 動作：計算預期高溫 VREF 值 `expected_ht_ce0 = ht_ce0 + 3`。透過 `hw_setting.set_local_val` 將 `HT_CE0_TX_VREF` 設定為 `expected_ht_ce0`，並執行 `hw_setting.set_to_device`。接著呼叫 `self.set_temp(100)` 發送 Vendor Command `D08A` 設定虛構的高溫環境（Payload 為 signed 16-bit 100）。最後再次呼叫 `issue_4022_to_get_NAND_feature(0, 0x23)` 取得新的 Payload Byte 8 值。
   - 預期結果：取得的 Payload Byte 8 值必須嚴格等於 `(expected_ht_ce0 << 1)`。此結果證明 FW 能正確處理高溫區間的 VREF 映射，確保在高溫條件下 Data Training 參數隨硬體設定同步調整。

4. [Recovery_State_Verification_Check]：
   - 動作：將 `LT_CE0_TX_VREF`、`CT_CE0_TX_VREF` 與 `HT_CE0_TX_VREF` 分別恢復為初始讀取的 `lt_ce0`、`ct_ce0` 與 `ht_ce0`，並執行 `hw_setting.set_to_device`。接著呼叫 `self.recover_temp()` 發送 Vendor Command `D08A` 並設定 `bEnableSetVuTemp.value = 0` 以清除溫度設定。最後呼叫 `issue_4022_to_get_NAND_feature(0, 0x23)` 取得最終的 Payload Byte 8 值。
   - 預期結果：取得的 Payload Byte 8 值必須嚴格等於 `(ct_ce0 << 1)`（即初始基準值）。此結果驗證系統在恢復硬體設定與溫度狀態後，FW 的 Data Training 特徵值能完全回退至初始狀態，無殘留狀態或記憶體泄漏，確保測試環境的乾淨性。