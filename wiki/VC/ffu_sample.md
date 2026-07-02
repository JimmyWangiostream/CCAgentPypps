# Test Spec: UFS FW/HW SVN Backward Update & Recovery Test

## Verification Criterion (VC)
驗證 UFS 裝置在啟用 `FFU_SAMVE_SVN_BACKWARD_EN` 硬體設定後，韌體（FW）與硬體微碼（HW）的 SVN（Security Version Number）向下更新（Backward Update）機制及其恢復行為：
1. **FW SVN 向下更新**：確認從 Current SVN 刷入 Old SVN 後，裝置能成功完成微碼更新並重置；隨後從 Old SVN 刷回 Current SVN，確認 SVN 值正確恢復且狀態正常。
2. **HW SVN 向下更新**：確認從 Current SVN 刷入 Old SVN 後，裝置能成功完成微碼更新並重置；隨後從 Old SVN 刷回 Current SVN，確認 SVN 值正確恢復且狀態正常。
3. **核心驗證點**：每次 `send_ffu_write_buffer` 後執行 `HW_RESET`，必須讀取 `DEVICE_FFU_STATUS` 為 `SUCCESSFUL_MICROCODE_UPDATE`，且透過 `get_flash_setting` 讀取的 `FW_SVN` 必須與預期版本一致，證明韌體版本控制邏輯在向下更新情境下未被鎖定或報錯。

## Test Case (TC) Checkpoints

1. [FW_SVN_Backward_Then_Forward_Check]：
   - 動作：
     1. 讀取初始 `FW_SVN` 並記錄為 `origianl svn`。
     2. 透過 `api.search_ffu_bin` 取得 `FW_BIN` 的 `CURRENT_SVN_BIN` (orign) 與 `OLD_SVN_BIN` (test)。
     3. 設定硬體特徵 `FFU_FEATURE` 為 `FFU_SAMVE_SVN_BACKWARD_EN`，允許向下更新。
     4. 呼叫 `api.send_ffu_write_buffer` 將 `OLD_SVN_BIN` 寫入裝置，隨後呼叫 `api.init_tester_to_unit_ready` 執行 `HW_RESET`。
     5. 讀取 `DEVICE_FFU_STATUS`，若不等於 `SUCCESSFUL_MICROCODE_UPDATE` 則拋出異常。
     6. 讀取更新後的 `FW_SVN` 並記錄。
     7. 再次設定 `FFU_SAMVE_SVN_BACKWARD_EN`。
     8. 呼叫 `api.send_ffu_write_buffer` 將 `CURRENT_SVN_BIN` (orign) 寫入裝置，隨後呼叫 `api.init_tester_to_unit_ready` 執行 `HW_RESET`。
     9. 讀取 `DEVICE_FFU_STATUS`，若不等於 `SUCCESSFUL_MICROCODE_UPDATE` 則拋出異常。
     10. 讀取最終 `FW_SVN` 並記錄為 `after ffu old -> original, svn`。
   - 預期結果：
     - 第一次 HW_RESET 後，`DEVICE_FFU_STATUS` 必須為 `SUCCESSFUL_MICROCODE_UPDATE`，且讀取的 `FW_SVN` 必須等於 `OLD_SVN_BIN` 對應的版本號。
     - 第二次 HW_RESET 後，`DEVICE_FFU_STATUS` 必須為 `SUCCESSFUL_MICROCODE_UPDATE`，且讀取的 `FW_SVN` 必須恢復為 `CURRENT_SVN_BIN` 對應的版本號（即初始版本）。
     - 這證明在啟用向下更新功能後，韌體 SVN 可以從高版本降至低版本，再升回高版本，且韌體狀態機在每次重置後均能正確識別當前載入的微碼版本。

2. [HW_SVN_Backward_Then_Forward_Check]：
   - 動作：
     1. 讀取當前 `FW_SVN` 並記錄。
     2. 透過 `api.search_ffu_bin` 取得 `FW_HW_BIN` 的 `CURRENT_SVN_BIN` (orign) 與 `OLD_SVN_BIN` (test)。
     3. 設定硬體特徵 `FFU_FEATURE` 為 `FFU_SAMVE_SVN_BACKWARD_EN`。
     4. 呼叫 `api.send_ffu_write_buffer` 將 `FW_HW_BIN` 的 `OLD_SVN_BIN` 寫入裝置，隨後呼叫 `api.init_tester_to_unit_ready` 執行 `HW_RESET`。
     5. 讀取 `DEVICE_FFU_STATUS`，若不等於 `SUCCESSFUL_MICROCODE_UPDATE` 則拋出異常。
     6. 讀取更新後的 `FW_SVN` 並記錄。
     7. 再次設定 `FFU_SAMVE_SVN_BACKWARD_EN`。
     8. 呼叫 `api.send_ffu_write_buffer` 將 `FW_HW_BIN` 的 `CURRENT_SVN_BIN` (orign) 寫入裝置，隨後呼叫 `api.init_tester_to_unit_ready` 執行 `HW_RESET`。
     9. 讀取 `DEVICE_FFU_STATUS`，若不等於 `SUCCESSFUL_MICROCODE_UPDATE` 則拋出異常。
     10. 讀取最終 `FW_SVN` 並記錄。
   - 預期結果：
     - 第一次 HW_RESET 後，`DEVICE_FFU_STATUS` 必須為 `SUCCESSFUL_MICROCODE_UPDATE`，且讀取的 `FW_SVN` 必須等於 `OLD_SVN_BIN` 對應的版本號。
     - 第二次 HW_RESET 後，`DEVICE_FFU_STATUS` 必須為 `SUCCESSFUL_MICROCODE_UPDATE`，且讀取的 `FW_SVN` 必須恢復為 `CURRENT_SVN_BIN` 對應的版本號。
     - 這證明硬體微碼（HW Microcode）的 SVN 向下更新機制運作正常，且在恢復至原始版本後，裝置能正確識別並載入正確的硬體微碼版本，無版本衝突或鎖定錯誤。