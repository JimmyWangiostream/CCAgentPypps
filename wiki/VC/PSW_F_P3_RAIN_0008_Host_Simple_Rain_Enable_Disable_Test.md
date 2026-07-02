# Test Spec: UFS Rain VB Parity & Recovery Logic Verification (TLC/SLC/WB)

## Verification Criterion (VC)
驗證 UFS 韌體在不同儲存模式（TLC/SLC/WB）下，Rain VB（Rainbow VB）的奇偶校驗（Parity）計算與錯誤恢復機制：
1. **Parity Consistency Check**：確認在 Host Simple Rain 功能關閉期間，即使持續寫入數據跨越同一 Rain Group 邊界，韌體內部儲存的 Parity 值（透過 VU 4055 讀取）必須保持不變，證明未觸發不必要的 Parity 更新。
2. **Parity Update Logic**：確認在 Host Simple Rain 功能重新開啟並繼續寫入數據後，Parity 值必須發生改變，證明韌體正確地將新寫入的數據納入 Parity 計算。
3. **Recovery User Parity Match**：確認當前測試模式對應的 Rain User Parity 與系統預設的 RECOVER_USER Parity 完全一致，確保恢復路徑的數據完整性。
4. **UECC Recovery via Host Simple Rain**：確認在注入 UECC 錯誤後，若 Host Simple Rain 處於 Disable 狀態，讀取會返回 UECC 狀態；若切換為 Enable 狀態，韌體應利用 SRAM 中的 Parity 資訊自動修復錯誤，使讀取比較（Read Compare）通過。

## Test Case (TC) Checkpoints

1. [Case01_TLC_SLC_WB_Parity_Stability_Check]：
   - 動作：針對當前測試模式（TLC/SLC/WB）的指定 LUN，寫入總長度為 `max_plane * 16KB * prog_unit` 的數據。獲取該 LBA 對應的 PCA 並注入 UECC 錯誤。接著，透過 VU D08B 將 Host Simple Rain 的 BIT4/5/6 設為 Disable（關閉數據恢復功能）。隨後，繼續寫入長度為 `rain_goup_cnt * max_ce * max_plane * 16KB` 的數據，確保寫入範圍超過下一個相同的 Rain Group 邊界。在此過程中，透過 VU 4055 讀取當前 Rain User 的 Parity 值（`old_get_parity`），並再次讀取 Parity 值（`new_get_parity`）。
   - 預期結果：`new_get_parity[0:8]` 必須嚴格等於 `old_get_parity[0:8]`。這證明在 Host Simple Rain 關閉期間，即使寫入數據跨越 Group 邊界，韌體也不會更新 Parity，確保 Parity 僅在功能啟用時才反映最新數據狀態。

2. [Case02_Recovery_User_Parity_Consistency_Check]：
   - 動作：在 Case 01 的 Parity 穩定狀態下，透過 VU 4055 分別讀取當前測試模式對應的 `rain_user` Parity 以及系統預設的 `RECOVER_USER` Parity。
   - 預期結果：`rain_user` 的 Parity 值必須與 `RECOVER_USER` 的 Parity 值完全相同。若不相等，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此步驟驗證韌體在當前配置下，恢復用戶的奇偶校驗數據與當前活躍用戶數據的一致性，確保備援恢復路徑的正確性。

3. [Case03_Host_Simple_Rain_Enable_Parity_Update_Check]：
   - 動作：透過 VU D08B 將 Host Simple Rain 的 BIT0/1/2 設為 Enable（開啟數據恢復功能）。隨後，再次寫入長度為 `rain_goup_cnt * max_ce * max_plane * 16KB` 的數據，同樣跨越下一個 Rain Group 邊界。寫入完成後，透過 VU 4055 讀取新的 Parity 值（`new_get_parity`），並與之前的 `old_get_parity` 進行比對。
   - 預期結果：`new_get_parity[0:8]` 必須不等於 `old_get_parity[0:8]`。這證明在 Host Simple Rain 啟用狀態下，新寫入的數據被正確地整合進 Parity 計算中，Parity 值隨數據更新而改變。

4. [Case04_UECC_Recovery_Verification]：
   - 動作：在 Case 01 中，針對寫入的最後一個頁面（LBA `last_lba`）注入 UECC 錯誤。首先，確認在 Host Simple Rain Disable 狀態下，直接讀取該頁面（透過 `direct_read_raw_data_and_check_status`）會返回 `ReadStatus.UECC`。接著，透過 VU D08B 將 Host Simple Rain Enable（BIT4/5/6 設為 Enable）。最後，使用 `read_compare_rain_result` 對該 LBA 進行讀取比較。
   - 預期結果：在 Host Simple Rain Enable 後，讀取比較必須通過（`expect_error=False`）。這證明韌體能夠利用 SRAM 中儲存的 Parity 資訊（由 `Rain_in_SRAM` 參數控制）自動修復注入的 UECC 錯誤，恢復數據完整性。