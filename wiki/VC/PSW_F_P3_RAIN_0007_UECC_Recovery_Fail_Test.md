# Test Spec: UFS Firmware Refresh Mechanism & UECC Handling Verification

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇多重 UECC (Uncorrectable ECC) 錯誤時的硬體行為與韌體恢復機制：
1. **Refresh 停止機制**：確認透過 Vendor Command (C088) 停止背景 Refresh 後，針對注入 UECC 的 LWP 進行 Direct Read 時，控制器能正確回報 `ReadStatus.UECC`，證明 Refresh 機制確實被暫停且未自動修復錯誤。
2. **Host Read 錯誤傳播**：確認當 Host 發送 Read10 指令讀取包含注入 UECC 的 LBA 時，UFS 設備必須回報 `TARGET_FAILURE` 狀態碼，且 Sense Key 為 `MEDIUM_ERROR`，證明錯誤數據無法被讀出並正確傳遞給 Host。
3. **Refresh Booking Queue 狀態**：確認在 UECC 解碼失敗後，韌體內部針對該 Virtual Block (VB) 的 Refresh Booking Queue 狀態符合預期（通常為標記為需修復或已放棄），確保韌體內部狀態機的一致性。
4. **HW_RESET 後狀態重置**：確認執行 HW_RESET 後，韌體進入初始化流程，並透過 `reconfig_to_erase_all_lun` 清除所有測試數據，確保測試環境的乾淨性與可重複性。

## Test Case (TC) Checkpoints

1. [Case01_TLC_OpenVB_UECC_DirectRead_Check]：
   - 動作：針對 Normal LUN (TLC Mode) 寫入超過 3 個 Pageline 的資料以建立 Open VB，取得 Cursor 資訊。透過 `inject_2_UECC_by_open_vb_info` 在該 Open VB 的兩個連續物理頁面 (Page) 注入 UECC 錯誤（設定 `SLC_enable=False`）。接著發送 Vendor Command C088 (`StopRefreshRefreshCanStillBeEnqueue`) 停止背景 Refresh。隨後對這兩個注入 UECC 的 PCA 執行 `direct_read_raw_data_and_check_status`，預期狀態為 `ReadStatus.UECC`。
   - 預期結果：Direct Read 的返回狀態必須等於 `project_api.ReadStatus.UECC`，證明在 Refresh 停止的情況下，硬體無法修正 UECC 錯誤，且直接讀取原始資料會正確回報錯誤狀態。

2. [Case02_SLC_ClosedVB_UECC_HostRead_Check]：
   - 動作：針對 EM1 LUN (SLC Mode) 建立 Closed VB，透過 `inject_2_UECC_by_lun` 在 LBA 0 和 LBA 16KB (4 pages) 處注入 UECC 錯誤（設定 `SLC_enable=True`）。發送 Vendor Command C088 停止 Refresh。接著 Host 發送 Read10 指令讀取包含錯誤 LBA 的區塊。檢查最後一個 Read10 指令的回應 (`response.upiu.b6_response`, `b7_status`, `b32_sense_data.b2_sense_key`)。
   - 預期結果：Read10 指令必須失敗，具體表現為 `response.upiu.b6_response` 不等於 `UPIUResponse.TARGET_SUCCESS`，且 `response.upiu.b7_status` 等於 `ScsiStatus.CHECK_CONDITION`，同時 `sense_key` 等於 `SenseKey.MEDIUM_ERROR`。這驗證了當韌體無法透過 ECC 修正數據時，會向上層 Host 回報 Medium Error，阻止錯誤數據的讀取。

3. [Case03_UECC_Decode_Fail_Refresh_Queue_Check]：
   - 動作：在 Case02 的 SLC Closed VB 情境下，完成 Host Read 並確認收到 MEDIUM_ERROR 後，呼叫 `check_UECC_refresh_booking_Q`，傳入包含錯誤 PCA 的 `virtual_block_number` 列表。
   - 預期結果：韌體內部的 Refresh Booking Queue 必須正確反映該 VB 的 UECC 狀態。根據韌體邏輯，這通常意味著該 VB 被標記為需要特殊處理（例如標記為 Bad 或加入修復佇列但標記為不可修復），確保韌體不會在後續操作中嘗試對已確認無法修復的區塊進行無效的 Refresh 操作，或正確記錄錯誤以進行後續的 Wear Leveling 或 Bad Block Management。

4. [Case04_PTE_OpenVB_UECC_DirectRead_Check]：
   - 動作：針對 PTE LUN (PTE Mode) 建立 Open VB，透過 `inject_2_UECC_by_open_vb_info` 在 PTE LWP 注入 UECC 錯誤（設定 `SLC_enable=False`，因為 PTE 通常不使用 SLC 模式或根據 `testMode != TestMode.TEST_TLC` 判斷，此處 PTE 非 TLC，故 SLC_en 為 False? *註：代碼中 `SLC_en = testMode != TestMode.TEST_TLC`，PTE != TLC，故 SLC_en=True? 需依實際 API 定義，但通常 PTE 為特殊區域。根據代碼邏輯，PTE 模式下 `REH_Enable=True` 傳入 Direct Read*）。發送 Vendor Command C088 停止 Refresh。對注入點執行 Direct Read，預期狀態為 `ReadStatus.UECC`，且啟用 REH (Read Error Handling)。
   - 預期結果：Direct Read 狀態必須為 `ReadStatus.UECC`，且由於 `REH_Enable=True`，硬體應嘗試讀取備援數據或回報特定錯誤碼，但最終仍應確認 UECC 存在。這驗證了 PTE 區域在無 Refresh 保護下的錯誤檢測機制。

5. [Case05_POR_Reset_Cleanup_Check]：
   - 動作：在所有測試模式（TLC, SLC, WB, PTE）及 Open/Closed VB 組合完成上述檢查後，執行 `api.init_tester_to_unit_ready` 觸發 `HW_RESET`。隨後呼叫 `reconfig_to_erase_all_lun` 清除所有 LUN 資料。
   - 預期結果：設備必須成功完成 HW_RESET 並進入 Unit Ready 狀態。`reconfig_to_erase_all_lun` 必須成功執行，確保所有測試期間寫入的資料（包括注入 UECC 的區塊）被物理擦除，為下一次測試循環提供乾淨的初始狀態，防止殘留數據影響後續測試結果。