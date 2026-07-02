# Test Spec: UFS Temperature Monitoring & Health Report Consistency Verification

## Verification Criterion (VC)
驗證 UFS 裝置在正常環境溫度（20°C 至 75°C）下的溫度感測機制與韌體健康報告的一致性：
1. **Feature Support Check**：確認裝置是否支援 `TOO_HIGH_TEMPERATURE` 與 `TOO_LOW_TEMPERATURE` 事件控制功能。
2. **Multi-Source Temperature Acquisition**：透過 Vendor Command (VU) 0x40FD 讀取 uC 溫度、透過 Vendor Command (VU) 0x40FE 讀取 Enhanced Health Report 中的 `current_uc_temperature`，以及在支援情況下透過 Read Attribute (IDN 0x18) 讀取 `bDeviceCaseRoughTemperature`。
3. **Data Parsing & Validation**：
   - 驗證 VU 0x40FD 返回的原始數據經符號位元與比例因子（0.25）轉換後的溫度值必須落在 20°C 至 75°C 之間。
   - 驗證所有來源（VU 0x40FD, VU 0x40FE, Attribute 0x18）的溫度讀數之間的最大差異不得超過 4°C。
   - 驗證 Attribute 0x18 的原始值需減去 80 後才為實際溫度。

## Test Case (TC) Checkpoints
1. [Case01_Feature_Support_Initialization]：
   - 動作：呼叫 `api.get_ufs_features_support()` 獲取裝置功能支援狀態，檢查 `u4_too_high_temp` 與 `u5_too_low_temp` 位元。若任一為真，計算 `evnet_control` 值（bit[3] 為 HIGH_TEMP_EN, bit[4] 為 LOW_TEMP_EN），並透過 `api.write_attribute` 寫入 `EXC_EVENT_CONTROL` 暫存器以啟用溫度事件監控；若不支援則跳過寫入。隨後執行 3 分鐘 Idle 以穩定裝置狀態。
   - 預期結果：若裝置支援溫度事件，`EXC_EVENT_CONTROL` 暫存器應被正確設定以啟用相關中斷/事件；裝置進入穩定狀態。

2. [Case02_Multi_Source_Temperature_Readout]：
   - 動作：
     1. 透過 `project_api.push_40FD_get_uC_temp` 發送 Vendor Command 0x40FD 以獲取 uC 溫度。
     2. 若 `evnet_control != 0x0`，透過 `push_read_attr` 發送 Read Attribute 指令，IDN 設為 `DEVICE_CASE_ROUGH_TEMPERATURE` (0x18)。
     3. 透過 `project_api.push_40FE_to_read_enhanced_health_report` 發送 Vendor Command 0x40FE 以獲取增強健康報告。
     4. 執行 `ExecuteCMD.send(clear_on_success=False)` 發送所有指令。
     5. 依序讀取回應：
        - 解析 VU 0x40FD 回應：從 `data[4]` 提取符號位元 (bit[2]) 與值位元 (bit[0:1])，結合 `data[3]`，根據符號位元決定正負號，並乘以 0.25 轉換為攝氏度。
        - 若支援，解析 Attribute 回應：提取 `attr_temp` 並減去 80 得到實際溫度。
        - 解析 VU 0x40FE 回應：透過 `ReadEnhanceHealthReport` 結構體提取 `current_uc_temperature` 值。
   - 預期結果：成功獲取三個溫度來源的原始數據，且解析過程無異常；VU 0x40FD 的解析邏輯正確處理了負溫度（若存在）與小數點轉換。

3. [Case03_Temperature_Range_And_Consistency_Check]：
   - 動作：
     1. 檢查 VU 0x40FD 解析後的 `VU_temp` 是否嚴格介於 20°C 與 75°C 之間。
     2. 若支援 Attribute 讀取，收集 `VU_temp`、Health Report 溫度、Attribute 溫度至列表 `temp_list`；否則僅收集前兩者。
     3. 計算 `temp_list` 中最大值與最小值的絕對差值 (`temp_diff`)。
     4. 若 `temp_diff > 4`，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。
   - 預期結果：
     - `VU_temp` 必須在 [20, 75] 範圍內，代表裝置處於正常操作環境溫度。
     - 所有溫度來源之間的偏差必須 ≤ 4°C，代表 uC 內部感測器、健康報告記錄值與外部 Case 溫度感測器之間的一致性良好，無硬體故障或校準錯誤。