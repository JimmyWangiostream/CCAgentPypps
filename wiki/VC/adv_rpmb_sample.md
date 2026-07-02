# Test Spec: UFS RPMB Region 0 Advanced Mode Key Programming & Data Integrity Test

## Verification Criterion (VC)
驗證 UFS 裝置在啟用 Advanced RPMB Mode 與 RPMB Purge Enable 配置下，RPMB Region 0 的密鑰管理與數據完整性機制：Case 01 確認在 RPMB Key 未燒錄狀態下，讀取 Counter 會觸發 `SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常，隨後透過 `adv_rpmb_key_programming` 成功燒錄密鑰；Case 02 確認密鑰燒錄後，針對 LBA 0 寫入 4 個 Block 的測試數據，並立即讀回，驗證 RPMB 硬體在 Advanced Mode 下能正確執行基於 HMAC-SHA256 的數據完整性檢查，確保寫入與讀取的數據一致性，且無 RPMB 錯誤狀態碼返回。

## Test Case (TC) Checkpoints
1. [Case01_Key_Programming_Check]:
   - 動作：透過 `api.push_write_config` 將 RPMB 配置寄存器 `b12_rpmb_region_enable` 設定為 `REGION_0_ENABLE | ADVANCED_RPMB_MODE | RPMB_PURGE_ENABLE`，並透過 `api.push_write_config` 寫入 UFS 裝置。接著進入循環，針對 `api.RPMBRegion.REGION_0` 執行 `api.vuc_clear_rpmb_key` 清除現有密鑰。隨後建立 `AdvRPMB` 物件並呼叫 `adv_rpmb_read_counter()`。由於密鑰已清除，預期觸發 `api.SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常。在 `except` 區塊中，記錄日誌並呼叫 `adv_rpmb_key_programming()` 執行密鑰燒錄流程。
   - 預期結果：`adv_rpmb_read_counter()` 必須拋出 `SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常，證明硬體拒絕在未授權狀態下訪問 RPMB 計數器；`adv_rpmb_key_programming()` 必須成功執行，將隨機生成的 256-bit RPMB Key 寫入裝置的非易失性儲存區，並建立對應的 HMAC 金鑰上下文，為後續數據操作做準備。

2. [Case02_Data_Integrity_Advanced_Mode_Check]:
   - 動作：在密鑰燒錄成功後（或若密鑰原本存在則跳過燒錄步驟），建立 `AdvRPMB` 物件。呼叫 `adv_rpmb_write_data(0, 4)` 向 RPMB Region 0 的 LBA 0 寫入 4 個 Block（通常為 256 或 512 位元組，取決於裝置定義）的測試數據。緊接著呼叫 `adv_rpmb_read_data(0, 4)` 從同一 LBA 讀回數據。
   - 預期結果：寫入操作必須返回成功狀態碼，且硬體內部應自動計算並儲存與該數據區塊對應的 HMAC 簽章；讀回操作必須成功返回與寫入時完全一致的數據內容，且硬體驗證機制確認 HMAC 簽章匹配，無 `RPMB_STATUS_GENERAL_FAILURE` 或 `RPMB_STATUS_AUTHENTICATION_FAILURE` 錯誤，證明 Advanced RPMB Mode 下的數據寫入與完整性驗證機制運作正常。