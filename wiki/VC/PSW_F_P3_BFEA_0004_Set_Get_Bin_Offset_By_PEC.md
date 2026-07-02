# Test Spec: UFS FTL Bin Offset Configuration & Persistence Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Vendor Command (D04A/404A) 對 FTL (Flash Translation Layer) 寫入平衡 (Write Booster) 及多層快閃記憶體 (SLC/MLC/TLC) 區塊分配策略 (Bin Offset) 的配置、讀取一致性與持久化機制：
1. **Case 01 (Random Config & Verify)**：透過 Vendor Command 設定隨機的 `setting_N` (0-15) 及固定的 L1-L7 閾值 (128)，並透過讀取 Command 驗證 Payload 中對應索引位的數值是否嚴格等於 128，確認寫入邏輯正確。
2. **Case 02 (EC Interval Variation)**：在固定 `setting_N=16` 下，遍歷 `setting_EC_Interval` (1-4)，驗證韌體能否接受不同的 Error Correction 間隔參數設定，並確認無異常錯誤碼返回。
3. **Persistence Check (Flow 5)**：在測試結束後，讀取初始備份的 `backup_bin_404A` 數據，重新應用相同的 Bin Offset 參數，驗證韌體狀態是否能在多次配置後保持可預測性或恢復至基準狀態，確保 Vendor Command 的參數解析邏輯無邊界錯誤。

## Test Case (TC) Checkpoints

1. [Case01_Random_N_Setting_Verification]：
   - 動作：
     1. 執行 `flow1` 初始化 LUN 配置與 RPMB 金鑰。
     2. 執行 `flow2` 備份當前 404A Vendor Command 的 Bin Offset 狀態至 `backup_bin_404A`。
     3. 在 `flow3(case_num=1)` 中，生成隨機整數 `setting_N` (範圍 0x00 至 0x0F)。
     4. 設定所有層級 (SLC_L1, MLC_L1-L3, TLC_L1-L7) 的閾值為固定值 128。
     5. 呼叫 `project_api.issue_D04A_Set_Bin_Offset` 將上述參數寫入韌體。
     6. 在 `flow4(case_num=1)` 中，呼叫 `project_api.issue_404A_Get_Bfea_Bin_Offset` 讀回當前狀態。
     7. 檢查讀回 Payload 中索引範圍 `[setting_N * 11]` 至 `[setting_N * 11 + 10]` 的 11 個 Byte 數據。
   - 預期結果：
     - Vendor Command 執行成功，無 `DLL_RESPONSE_ERROR`。
     - Payload 中索引 `i` (從 0 到 10) 的數值 `payload[setting_N * 11 + i]` 必須嚴格等於 `0x80` (十進位 128)。
     - 若任何一個 Byte 不等於 128，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，代表韌體內部 Bin Offset 表寫入錯誤或讀取映射錯誤。

2. [Case02_EC_Interval_Range_Verification]：
   - 動作：
     1. 在 `flow3(case_num=2)` 中，固定 `setting_N = 16`。
     2. 生成隨機 `setting_EC_Interval` (範圍 1 至 4)。
     3. 設定所有層級 (SLC/MLC/TLC L1-L7) 閾值為 128。
     4. 呼叫 `project_api.issue_D04A_Set_Bin_Offset` 寫入參數。
     5. 若發生 `DLL_RESPONSE_ERROR`，記錄日誌並清除 Command 隊列，視為測試通過（代表韌體正確拒絕了無效或特定情境下的參數，或測試框架預期此錯誤為正常邊界行為）。
   - 預期結果：
     - 韌體應正確處理 `setting_EC_Interval` 在 1-4 之間的變化。
     - 若未拋出異常，代表參數被成功接受並應用於 FTL 的錯誤校正間隔機制。

3. [Case03_Persistence_Backup_Restore_Check]：
   - 動作：
     1. 在 `flow5` 中，遍歷 `setting_EC_Interval` 從 1 到 4。
     2. 從 `backup_bin_404A` (由 `flow2` 備份) 中提取原始配置數據：
        - `setting_N` 為 `backup_N`。
        - 提取對應索引的 11 個 Byte 數據分別賦值給 `setting_SLC_L1` 至 `setting_TLC_L7`。
     3. 再次呼叫 `project_api.issue_D04A_Set_Bin_Offset` 將這些原始數據重新寫入韌體。
   - 預期結果：
     - 韌體應能正確解析並應用從備份中讀取的原始 Bin Offset 數據。
     - 此步驟驗證 Vendor Command 的參數序列化/反序列化邏輯在多次讀寫後保持一致性，確保韌體狀態不會因測試流程而產生不可逆的損壞或漂移。