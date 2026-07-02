# Test Spec: Thermal Protection VU (D08A/D088) Temperature Delta & ATS Timer Verification

## Verification Criterion (VC)
驗證 UFS 韌體在透過 Vendor Command (VU) D08A 模擬 NAND 與 UC 溫度變化時，內部溫度計算邏輯（Delta_T）的正確性，以及自動休眠計時器（ATS Timer）在啟用 Auto-Standby 後的遞增行為：
1. **Delta_T 邏輯驗證**：確認韌體內部變數 `gUfsApiStruct.ftl->temp.delta_asic_nand` 嚴格等於 `ts_asic` 減去 `avg_ts_nand`，驗證溫度差值計算無誤。
2. **ATS Timer 遞增驗證**：確認在啟用 Auto-Standby (VU D088 Enable) 後，透過 Smart Info 讀取的 ATS Timer 計數器會隨時間穩定增加，排除計數器倒數或重置的異常行為。
3. **狀態一致性驗證**：確認在溫度設定變更後，讀回的 `t_nand` 與 `t_asic` 及 `delta_asic_nand` 三者之間滿足數學恆等式 `t_nand = t_asic - delta_asic_nand`，確保溫度狀態機數據同步。

## Test Case (TC) Checkpoints
1. [Case01_Delta_T_Calculation_Check]：
   - 動作：
     1. 發送 VU D088 將 Auto-Standby 設為 Disable (0)。
     2. 發送 VU D08A 設定 UC 溫度為 50°C (`uc=50`)，NAND 溫度為 30°C (`nand=30`)。
     3. 等待 10 秒讓韌體變數更新。
     4. 透過 `read_fw_value` 讀取韌體內部結構體 `gUfsApiStruct.ftl->temp` 下的三個欄位：`ts_asic` (t_asic), `avg_ts_nand` (t_nand), 以及 `delta_asic_nand`。
     5. 計算預期差值 `expected_delta = t_asic - t_nand`，並與讀取的 `delta_asic_nand` 進行比對。
   - 預期結果：`delta_asic_nand` 必須精確等於 `t_asic - t_nand`。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體內部溫度差值計算邏輯錯誤。

2. [Case02_ATS_Timer_Increment_Check]：
   - 動作：
     1. 發送 VU D088 將 Auto-Standby 設為 Enable (1)。
     2. 發送 VU D08A 設定 UC 溫度為 40°C (`uc=40`)，NAND 溫度為 30°C (`nand=30`)。
     3. 呼叫 `get_ast_times()` 讀取 Smart Info payload 中偏移量 0x4a8 處的 8-byte 資料，轉換為整數得到 `backup_ats_times`。
     4. 等待 10 秒。
     5. 再次呼叫 `get_ast_times()` 讀取 Smart Info payload 中偏移量 0x4a8 處的 8-byte 資料，轉換為整數得到 `get_ats_times`。
     6. 比對 `get_ats_times` 與 `backup_ats_times`。
   - 預期結果：`get_ats_times` 必須大於或等於 `backup_ats_times`。若 `get_ats_times < backup_ats_times`，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表 ATS Timer 在 Auto-Standby 啟用期間未正確遞增或發生異常重置。

3. [Case03_Temperature_State_Sync_Check]：
   - 動作：
     1. 在 Case02 的溫度設定 (UC=40, NAND=30) 持續生效下。
     2. 再次透過 `read_fw_value` 讀取韌體內部變數 `ts_asic`, `avg_ts_nand`, `delta_asic_nand`。
     3. 驗證數學關係：計算 `calculated_t_nand = t_asic - delta_asic_nand`，並與讀取的 `t_nand` (`avg_ts_nand`) 進行比對。
   - 預期結果：`t_nand` 必須精確等於 `t_asic - delta_asic_nand`。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體內部溫度狀態變數之間存在數據不一致或同步延遲問題。