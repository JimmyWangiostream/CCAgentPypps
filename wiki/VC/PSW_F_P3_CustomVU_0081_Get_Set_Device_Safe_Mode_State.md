# Test Spec: UFS Vendor Command Safe Mode Transition & FW Assert Validation

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command (D089) 進入 Safe Mode 的邊界條件處理與韌體異常保護機制：
1. **非法模式拒絕**：確認當設定值為 3~255 時，裝置必須拒絕請求並返回錯誤狀態碼，且透過 40A0 查詢確認裝置未進入 Safe Mode (State=0)。
2. **正常退出與進入**：確認設定為 0 可成功退出 Safe Mode (State=0)；設定為 1 進入 Safe Mode 後，後續查詢指令 (40A0) 必須觸發韌體 Assert 並導致 Host 端超時 (G_TIMEOUT_ALL)。
3. **Assert 恢復機制**：確認在 Safe Mode (Setting=1) 觸發 Assert 後，透過 MP (Maintenance Procedure) 重啟鏈路，裝置必須自動恢復至非 Safe Mode 狀態 (State=0)，證明韌體在 Assert 後具備自我修復或重置狀態機的能力。
4. **強制進入 Safe Mode 的超時行為**：確認設定為 2 時，裝置必須進入 Safe Mode 並導致 Host 端發送指令超時 (G_TIMEOUT_ALL)，驗證不同 Safe Mode 參數下的行為一致性。

## Test Case (TC) Checkpoints
1. [Case01_Illegal_SafeMode_Rejection_Check]：
   - 動作：首先透過 Vendor Command 40A0 讀取當前 Safe Mode 狀態，預期初始值為 255 (表示未處於 Safe Mode 或初始狀態)。接著隨機生成一個介於 3 到 255 之間的整數 `setting_mode`，透過 Vendor Command D089 嘗試設定該非法 Safe Mode。預期此操作會拋出 `DLL_RESPONSE_ERROR` 異常。若未拋出異常，則測試失敗。最後再次透過 40A0 讀取狀態，預期 payload[0] 必須等於 0。
   - 預期結果：D089 設定非法值 (3-255) 時必須返回錯誤 (`DLL_RESPONSE_ERROR`)；40A0 查詢結果 payload[0] 必須為 0，代表裝置成功拒絕非法請求且狀態保持正常。

2. [Case02_Normal_Exit_SafeMode_Check]：
   - 動作：透過 Vendor Command D089 設定 `setting_mode = 0` (退出 Safe Mode)。接著透過 Vendor Command 40A0 讀取裝置 Safe Mode 狀態。
   - 預期結果：D089 設定成功；40A0 查詢結果 payload[0] 必須等於 0，代表裝置已成功退出 Safe Mode 並處於正常運作狀態。

3. [Case03_SafeMode_Entry_Assert_Timeout_Check]：
   - 動作：透過 Vendor Command D089 設定 `setting_mode = 1` (進入 Safe Mode)。隨後立即透過 Vendor Command 40A0 嘗試讀取狀態。預期此查詢指令會觸發韌體 Assert，導致 Host 端收到 `G_TIMEOUT_ALL` 異常。記錄 Assert 次數 (`api.get_fw_assert_number()`)。若未發生超時，則測試失敗。接著執行 MP (Maintenance Procedure) 並重新初始化鏈路至最高 HS Gear (`first_init_to_max_hs_gear`)。最後再次透過 40A0 讀取狀態。
   - 預期結果：D089 設定後，隨後的 40A0 查詢必須觸發 `G_TIMEOUT_ALL` (代表 FW Assert)；鏈路重啟後，40A0 查詢結果 payload[0] 必須等於 0，代表韌體在 Assert 恢復後，Safe Mode 狀態已重置為正常 (0)。

4. [Case04_SafeMode_Entry2_Timeout_Check]：
   - 動作：透過 Vendor Command D089 設定 `setting_mode = 2` (另一種 Safe Mode 參數)。預期此操作會導致後續通訊異常。記錄 Assert 次數。若未發生超時，則測試失敗。接著執行 MP 並重新初始化鏈路。
   - 預期結果：D089 設定 `setting_mode = 2` 後，裝置必須進入 Safe Mode 並導致 Host 端超時 (`G_TIMEOUT_ALL`)，驗證參數 2 同樣能觸發 Safe Mode 行為。