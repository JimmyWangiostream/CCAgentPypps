# Test Spec: UFS VB Read-Scan & APL Recovery with Multi-WL UECC Injection

## Verification Criterion (VC)
驗證 UFS 韌體在 VB (Virtual Block) 生命周期中，針對不同 WL (Write Level) 注入 UECC 錯誤後的 Read-Scan 檢測機制與 APL (Abnormal Power Loss) 恢復邏輯：
1. **階段性檢測驗證**：確認在寫入至 15 WL 後，韌體能正確識別並報告 WL0, WL1, WL3, WL9 的 UECC 錯誤（狀態碼 1），且僅掃描符合 `phy_WL % 3 == 0` 的頁面；同時確認錯誤檢測列表 (`error_detected_WLs`) 精確包含 WL0 和 WL3。
2. **SPOR 與 APL 觸發驗證**：確認在注入 WL6 UECC 並執行 SPOR (Simulated Power Off Recovery) 後，韌體能正確建立 APL 標記 (`APL_flag = 1`)，並在後續寫入觸發 VB 關閉前，持續報告 WL0, WL3, WL9 的錯誤狀態。
3. **VB 關閉與清理驗證**：確認當 VB 寫滿並關閉後，Read-Scan 狀態重置為完成 (Status 0)，且 `error_detected_WLs` 列表清空，代表錯誤標記已隨 VB 生命周期結束而被正確處理或清除。

## Test Case (TC) Checkpoints

1. [Case01_PreScan_UECC_Injection_Check]：
   - 動作：配置 LUN 0 為 Normal，LUN 1 為 EM1。寫入 15 WL 的 TLC 資料至 LUN 0。獲取當前 VB 號碼 (`self.VB`) 與 PCA 資訊。針對 WL0, WL1, WL3, WL9 對應的物理頁面注入 UECC 錯誤（透過 `inject_UECC` 修改 PCA 指向的頁面並觸發硬體錯誤注入）。
   - 預期結果：韌體內部狀態應記錄這些頁面的 UECC 錯誤，但尚未觸發 Read-Scan 報告，需等待後續寫入或狀態查詢來驗證檢測結果。

2. [Case02_Post15WL_ReadScan_Status_Check]：
   - 動作：呼叫 `project_api.check_if_current_VB_scan_in_progress_completed(VB=self.VB)` 讀取狀態暫存器。
   - 預期結果：狀態值必須等於 `1`（代表 Read-Scan 正在進行或未完成），確認韌體已偵測到先前注入的 UECC 錯誤並啟動掃描機制。

3. [Case03_PageList_Filtering_Check]：
   - 動作：呼叫 `project_api.get_Normal_VB_Scan_Pages` 獲取當前掃描頁面列表 (`PageList`)。遍歷頁面 0 到 3311，利用 `get_physical_layout` 計算每個頁面的 `phy_WL`。移除所有 `phy_WL % 3 == 0` 的頁面。檢查剩餘的 `PageList` 是否為空。
   - 預期結果：`PageList` 必須為空列表。這證明韌體的 Read-Scan 機制嚴格遵循硬體幾何限制，僅掃描特定 WL 間隔（模 3 為 0）的頁面，排除其他 WL 的干擾。

4. [Case04_ErrorDetected_WLs_Validation]：
   - 動作：呼叫 `project_api.get_gc_read_scan_released_scan_pageline()` 獲取錯誤檢測到的 WL 列表 (`old_error_detected_WLs`)。檢查列表長度及具體數值。
   - 預期結果：列表長度必須等於 `2`。列表中的第一個元素必須為 `0` (WL0)，第二個元素必須為 `3` (WL3)。這驗證了韌體在 Read-Scan 過程中精確識別並報告了 WL0 和 WL3 的錯誤，而 WL1 和 WL9 因未滿足掃描條件或處理邏輯不同而未在此階段報告。

5. [Case05_WL6_UECC_Injection_Check]：
   - 動作：獲取 LBA 對應 WL6 的 PCA，並注入 UECC 錯誤。獲取更新後的 VB 資訊。
   - 預期結果：韌體應記錄 WL6 的錯誤狀態，為後續 SPOR 情境做準備。

6. [Case06_SPOR_APL_Creation_Check]：
   - 動作：執行 `write_data_with_SPOR` 函數。該函數透過循環寫入並在中間插入 `push_spor` (模擬掉電) 來觸發 APL 建立。當 `DLL_CRC32_COMPARE_FAIL` 異常發生時，確認 APL 標記已建立。隨後寫入額外資料以確保 APL 狀態穩定。
   - 預期結果：韌體應成功建立 APL (Abnormal Power Loss) 標記，標誌著 VB 經歷了非正常電源循環。

7. [Case07_SPOR_Page_UECC_Injection_Check]：
   - 動作：計算 SPOR 發生時的頁面位置 (`self.SPOR_WL`)。透過遞迴檢查頁面邊界確定確切的 WL。在該 SPOR 頁面注入 UECC 錯誤。
   - 預期結果：韌體應記錄 SPOR 頁面的錯誤，此錯誤將與之前的錯誤共同影響後續的 VB 掃描行為。

8. [Case08_FillVB_ReadScan_Status_Check]：
   - 動作：寫入資料直至 VB 接近滿載。呼叫 `check_if_current_VB_scan_in_progress_completed` 檢查狀態。呼叫 `get_gc_read_scan_released_scan_pageline` 獲取新的錯誤 WL 列表。呼叫 `get_APL_flag_of_VB` 獲取 APL 標記。
   - 預期結果：
     1. 狀態值必須等於 `1`（掃描未完成/有錯誤）。
     2. 錯誤 WL 列表長度必須等於 `3`。
     3. 列表最後一個元素必須為 `9` (WL9)。
     4. `APL_flag` 必須等於 `1`。
     這驗證了在 APL 情境下，韌體持續追蹤並報告 WL0, WL3, WL9 的錯誤，且 APL 標記正確存在。

9. [Case09_VB_Close_Cleanup_Check]：
   - 動作：寫入剩餘資料以完全關閉 VB。呼叫 `check_if_current_VB_scan_in_progress_completed` 檢查狀態。呼叫 `get_gc_read_scan_released_scan_pageline` 獲取錯誤 WL 列表。
   - 預期結果：
     1. 狀態值必須等於 `0`（代表 VB 關閉且掃描流程結束/無待處理錯誤）。
     2. 錯誤 WL 列表長度必須等於 `0`。
     這驗證了當 VB 生命周期結束時，韌體正確清理了所有的錯誤檢測狀態，確保下一個 VB 從乾淨狀態開始。

10. [Case10_PostProcess_BB_Retirement_Check]：
    - 動作：執行 `post_process`，啟動 Refresh 並等待 Bkops 閒置。呼叫 `check_BB_retirementafter_refresh`，傳入當前 VB 列表並預期原因為 `READBACK`。
    - 預期結果：VB 應被標記為需要退休 (Retirement)，且原因必須是 `READBACK`，代表由於累積的讀取錯誤 (UECC) 導致資料完整性風險，符合 UFS 標準的壞塊管理邏輯。