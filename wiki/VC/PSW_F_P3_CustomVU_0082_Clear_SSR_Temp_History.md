# Test Spec: UFS Enhanced Health Report Temperature Profile Reset Verification

## Verification Criterion (VC)
驗證 UFS 裝置在執行 `D011` (Clear SSR Temp History) 指令後，其內部暫存溫度歷史記錄是否被正確清除；並確認在執行 `HW_RESET` 硬體重啟後，韌體是否會自動重新初始化或載入新的溫度剖面數據，導致 `40FE` (Enhanced Health Report) 中的溫度剖面欄位從「非零（歷史數據）」轉變為「全零（初始/重置狀態）」，以此驗證 SSR (Self-Reporting) 溫度歷史清除機制與韌體狀態機在掉電重啟後的行為一致性。

## Test Case (TC) Checkpoints
1. [Case01_Clear_SSR_History_Check]：
   - 動作：透過 `issue_40FE_to_read_enhanced_health_report` 讀取初始健康報告，接著呼叫 `issue_D011_clear_ssr_temp_history` 發送 Vendor Command D011 以清除 SSR 溫度歷史記錄，隨後再次讀取 `40FE` 健康報告。
   - 預期結果：讀回的健康報告中，以下六個溫度剖面欄位的數值必須全部等於 `0`：
     - `temperature_profile_t_37`
     - `temperature_profile_37_t_25`
     - `temperature_profile_25_t_0`
     - `temperature_profile_0_t_95`
     - `temperature_profile_95_t_115`
     - `temperature_profile_t_115`
     若任一欄位不為 0，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表 D011 指令未能成功清除暫存器內的溫度歷史標記。

2. [Case02_PowerCycle_ZeroState_Check]：
   - 動作：在確認 D011 清除成功後，執行 `init_tester_to_unit_ready(Dcmd5ResetType.HW_RESET)` 進行硬體重啟（Power Cycle）。重啟完成後，再次透過 `issue_40FE_to_read_enhanced_health_report` 讀取健康報告，並檢查上述六個溫度剖面欄位。
   - 預期結果：讀回的健康報告中，上述六個溫度剖面欄位的數值必須全部等於 `0`（即 `all_zero_temperature` 為 True）。若任一欄位不為 0，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此步驟驗證在硬體重啟後，韌體並未殘留舊的溫度歷史數據，或系統處於預期的初始零值狀態，確保溫度監控模組在冷啟動時的行為符合規範。