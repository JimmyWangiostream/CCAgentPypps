# Test Spec: RPMB Region 0 Key Clearing & Data Integrity Verification

## Verification Criterion (VC)
驗證 UFS 裝置中 RPMB (Replay Protected Memory Block) Region 0 的密鑰清除機制與數據寫入/讀取的一致性：確認在執行 `vuc_clear_rpmb_key` 後，若嘗試讀取計數器會觸發 `SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常並自動執行 `rpmb_key_programming` 重新初始化；若密鑰未被正確清除（即仍舊存在），則應拋出 `SPEC_ASSERT_RPMB_KEY_NOT_CLEARED` 異常。在密鑰成功清除並重新編程後，驗證對 Block 0 寫入 4 字節數據後，讀回數據必須與寫入數據完全一致，確保 RPMB 區塊在密鑰重置後的數據完整性與訪問控制邏輯正確。

## Test Case (TC) Checkpoints
1. [RPMB_Key_Clear_and_Reprogram_Check]:
   - 動作：針對 `api.RPMBRegion.REGION_0` 執行兩次循環（模擬不同狀態或重複驗證）。首先呼叫 `api.vuc_clear_rpmb_key` 清除 Region 0 的 RPMB 密鑰。接著建立 `api.RPMB` 實例並嘗試呼叫 `rpmb.rpmb_read_counter()`。
     - 情境 A（密鑰已清除）：若觸發 `api.SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常，記錄日誌 "RPMB key is cleared"，並立即呼叫 `rpmb.rpmb_key_programming()` 重新編程密鑰。
     - 情境 B（密鑰未清除）：若未觸發異常（即 `else` 分支），記錄錯誤 "RPMB key is not cleared" 並拋出 `api.SPEC_ASSERT_RPMB_KEY_NOT_CLEARED` 異常終止測試。
   - 預期結果：在情境 A 中，系統必須成功捕捉密鑰缺失異常並完成密鑰重新編程流程，使 RPMB 進入可寫入狀態；在情境 B 中，測試必須失敗並報告密鑰清除失敗，確保測試環境處於預期的「密鑰已清除」初始狀態。

2. [RPMB_Data_Write_Read_Integrity_Check]:
   - 動作：在密鑰成功編程後（接續步驟 1 的 `else` 或異常處理後），呼叫 `rpmb.rpmb_write_data(0, 4)` 向 RPMB Block 0 寫入 4 字節的測試數據。隨後立即呼叫 `rpmb.rpmb_read_data(0, 4)` 從同一 Block 0 讀取 4 字節數據。
   - 預期結果：讀取回來的 4 字節數據必須與寫入的數據完全相等。這驗證了 RPMB 區塊在密鑰重置並重新編程後，其內部閃存單元能夠正確儲存數據，且讀寫通道無損壞，符合 RPMB 的安全數據存儲規範。