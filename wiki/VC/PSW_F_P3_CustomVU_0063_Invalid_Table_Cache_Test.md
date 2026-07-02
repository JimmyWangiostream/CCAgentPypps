# Test Spec: UFS PTE/PMD Cache Invalid Performance Degradation Test

## Verification Criterion (VC)
驗證 UFS 韌體中 PTE (Physical Table Entry) 與 PMD (Physical Map Data) 快取機制對讀取延遲的影響：Case 01 確認在正常 PTE/PMD 快取啟用狀態下，隨機讀取 1GB 資料的平均延遲低於快取失效狀態；Case 02 透過 Vendor Command (VU D08C) 將 PTE 快取標記為無效 (rainEnable=1)，驗證此時讀取延遲顯著增加（因需即時計算 PTE）；Case 03 透過 VU D08C 將 PMD 快取標記為無效 (rainEnable=2)，驗證讀取延遲進一步增加或維持高位（因需即時讀取 PMD 映射）；Case 04 同時使 PTE 與 PMD 快取失效 (rainEnable=3)，確認此時讀取延遲達到最高基準。核心邏輯在於比對 `total_read_time_with_pte_pmd` 與後續三種失效情境下的讀取時間，確保快取機制確實降低了 I/O 處理開銷。

## Test Case (TC) Checkpoints
1. [Case01_Baseline_PTE_PMD_Cache_Enabled]：
   - 動作：關閉 ATS (Active Transfer State) 以確保時鐘穩定，設定 `POWER_SAVING_CTRL_ENABLE` 為 `0x3A`。針對 LUN 0 寫入 1GB 資料（起始 LBA 0，長度 `WRITE_10_MAX_BLOCK_LEN`，總長度 `BLOCK4K_SIZE_1G_BYTE`）。接著執行隨機讀取測試：在 LBA 0 至 `total_len//2` 範圍內，以 4KB (`BLOCK4K_SIZE_4K_BYTE`) 為單位，總讀取量 1GB。記錄此階段包含 PTE 與 PMD 快取命中時的平均讀取時間 `total_read_time_with_pte_pmd`。
   - 預期結果：讀取操作成功完成，`total_read_time_with_pte_pmd` 應為基準低延遲值，代表 PTE/PMD 快取正常運作並加速映射查詢。

2. [Case02_PTE_Cache_Invalidated_Performance_Check]：
   - 動作：發送 Vendor Command (VU D08C) 並設定參數 `rainEnable=1`，此動作強制將 PTE 快取標記為無效 (Invalid)，迫使韌體在後續讀取時必須重新計算或查詢 PTE 表。接著再次執行與 Case 01 完全相同的隨機讀取測試（LUN 0, 1GB 總量, 4KB 區塊），記錄平均讀取時間 `total_read_time_without_pte`。
   - 預期結果：`total_read_time_without_pte` 必須大於 `total_read_time_with_pte_pmd`。若 `total_read_time_without_pte < total_read_time_with_pte_pmd`，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，證明 PTE 快取失效導致映射查詢開銷增加，符合預期硬體行為。

3. [Case03_PMD_Cache_Invalidated_Performance_Check]：
   - 動作：發送 Vendor Command (VU D08C) 並設定參數 `rainEnable=2`，此動作強制將 PMD 快取標記為無效。接著執行相同的隨機讀取測試，記錄平均讀取時間 `total_read_time_without_pmd`。
   - 預期結果：記錄 `total_read_time_without_pmd`。雖然程式碼中未對 Case 03 設定嚴格的 Fail 條件（註釋掉了 raise），但邏輯上預期 `total_read_time_without_pmd` 應顯著高於 Case 01 的基準值，證明 PMD 快取失效同樣導致讀取延遲上升。

4. [Case04_Both_PTE_PMD_Cache_Invalidated_Performance_Check]：
   - 動作：發送 Vendor Command (VU D08C) 並設定參數 `rainEnable=3`，此動作同時使 PTE 與 PMD 快取失效。接著執行相同的隨機讀取測試，記錄平均讀取時間 `total_read_time_without_pte_pmd`。
   - 預期結果：`total_read_time_without_pte_pmd` 必須大於 `total_read_time_with_pte_pmd`。若 `total_read_time_without_pte_pmd < total_read_time_with_pte_pmd`，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此步驟確認在雙重快取失效的最壞情況下，讀取性能仍嚴格劣於正常快取狀態，驗證了快取機制對 I/O 效能的關鍵貢獻。

5. [Post_Test_Hardware_Restoration]：
   - 動作：測試結束後，將 `POWER_SAVING_CTRL_ENABLE` 恢復為初始值 `default_value`。
   - 預期結果：硬體設定恢復原狀，確保不影響後續測試或系統穩定性。