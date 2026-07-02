# Test Spec: UFS VU Temperature Control & Health Report Verification

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command (VU) 0xD08A 設定虛擬溫度後，韌體內部溫度感測器、健康報告 (Health Report) 中的即時溫度、極值記錄 (Highest/Lowest) 以及溫度分佈統計 (Temperature Profile) 與溫度差統計 (Temperature Delta) 的正確性與一致性：
1. **即時溫度映射驗證**：確認 VU 設定的 NAND Die 溫度與 Controller (uC) 溫度能正確反映在 VU 0x4021 (NAND Temp) 與 0x40FD (uC Temp) 讀取值中，且健康報告中的 `current_nand_temp` 與 `current_uc_temperature` 與設定值完全一致。
2. **極值記錄驗證**：確認在設定高溫 (85°C) 與低溫 (-25°C) 後，健康報告中的 `highest_temp` 與 `power_on_highest_temp` 正確記錄高溫極值，`lowest_temp` 與 `power_on_lowest_temp` 正確記錄低溫極值；且執行 HW_RESET (POR) 後，`highest/lowest` 保持測試期間的極值，而 `power_on_highest/lowest` 重置為環境預設範圍 (10-60°C)。
3. **溫度差統計驗證**：確認透過 VU 逐步改變溫度（間隔 2-19°C）時，健康報告中的 `temperature_delta` 計數器能精確累加至對應的溫度差區間（<1, 1-5, 5-10, 10-15, >15°C），且其他區間計數不變。
4. **溫度分佈驗證**：確認透過 VU 設定特定臨界溫度點（如 -37, -25, 0, 95, 115°C 等），健康報告中的 `temperature_profile` 計數器能精確累加至對應的溫度分佈區間，且其他區間計數不變。

## Test Case (TC) Checkpoints

1. [Initial_State_Verification]：
   - 動作：在 Pattern 開始時，透過 VU 0x40FE 讀取 Enhanced Health Report，檢查 `highest_temp`, `lowest_temp`, `power_on_highest_temp`, `power_on_lowest_temp` 四個欄位。
   - 預期結果：這四個欄位的數值必須介於 10 到 60 之間（代表環境預設值），若有任何一個欄位超出此範圍則判定為失敗，確保測試前無殘留的極值數據干擾。

2. [High_Temp_Setting_Verification]：
   - 動作：透過 VU 0xD08A 設定 NAND Die 溫度為 20°C，Controller (uC) 溫度為 85°C（`Use_Delayed_fake_tmeperatures=0`）。等待 2 秒後，分別執行 VU 0x4021 讀取各 Die 溫度、VU 0x40FD 讀取 Controller 溫度、VU 0x40FE 讀取 Health Report。
   - 預期結果：
     - VU 0x4021 讀回的各 Die 溫度值必須等於 `20 + 37 = 57`（程式碼中 `temp_gap=37` 為校正值）。
     - VU 0x40FD 讀回的 Controller 溫度必須等於 85。
     - Health Report 中的 `current_nand_temp_die_X` 必須等於 20。
     - Health Report 中的 `current_uc_temperature` 必須等於 85。
     - Health Report 中的 `highest_temp` 與 `power_on_highest_temp` 必須等於 85。

3. [Low_Temp_Setting_Verification]：
   - 動作：透過 VU 0xD08A 設定 NAND Die 溫度維持 20°C，Controller (uC) 溫度為 -25°C（`Use_Delayed_fake_tmeperatures=0`）。等待 2 秒後，分別執行 VU 0x4021、0x40FD、0x40FE。
   - 預期結果：
     - VU 0x4021 讀回的各 Die 溫度值必須等於 57。
     - VU 0x40FD 讀回的 Controller 溫度必須等於 -25。
     - Health Report 中的 `current_nand_temp_die_X` 必須等於 20。
     - Health Report 中的 `current_uc_temperature` 必須等於 -25。
     - Health Report 中的 `lowest_temp` 與 `power_on_lowest_temp` 必須等於 -25。

4. [Power_On_Reset_Persistence_Check]：
   - 動作：執行 HW_RESET (POR)，等待系統重啟後，透過 VU 0x40FE 讀取 Enhanced Health Report。
   - 預期結果：
     - `highest_temp` 必須保持為 85（測試期間的最高溫）。
     - `lowest_temp` 必須保持為 -25（測試期間的最低溫）。
     - `power_on_highest_temp` 必須重置為 10-60 之間的環境預設值（小於 85）。
     - `power_on_lowest_temp` 必須重置為 10-60 之間的環境預設值（大於 -25）。
     - 此步驟驗證極值記錄在掉電重啟後是否正確保留歷史極值，而電源週期極值是否正確重置。

5. [Temperature_Delta_Statistical_Verification]：
   - 動作：初始化基準 Health Report。進入迴圈，設定溫度間隔 `test_temp_gap` 從 2 遞增至 19。每次設定新溫度後，等待 2 秒並讀取 Health Report。計算當前報告與基準報告的 `temperature_delta` 各欄位差值。
   - 預期結果：
     - 根據 `test_temp_gap` 的大小，對應的 `temperature_delta` 區間計數器差值必須大於 0（例如 gap=3 對應 1-5 區間，gap=12 對應 10-15 區間）。
     - 所有非對應區間的 `temperature_delta` 計數器差值必須為 0。
     - 若對應區間未增加或非對應區間發生變化，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

6. [Temperature_Profile_Statistical_Verification]：
   - 動作：初始化基準 Health Report。針對特定溫度列表 `[-37, -36, -26, -25, -24, -1, 0, 1, 94, 95, 96, 114, 115, 116]` 進行設定。每次設定後等待 2 秒並讀取 Health Report。
   - 預期結果：
     - 根據設定的 `test_temp` 值，對應的 `temperature_profile` 區間計數器（如 `temperature_profile_t_37`, `temperature_profile_37_t_25` 等）差值必須大於 0。
     - 所有非對應區間的 `temperature_profile` 計數器差值必須為 0。
     - 此驗證確保韌體能正確將即時溫度映射到預定義的溫度分佈桶 (Buckets) 中。