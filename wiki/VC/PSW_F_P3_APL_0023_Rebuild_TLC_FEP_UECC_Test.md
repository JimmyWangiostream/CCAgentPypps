# Test Spec: UFS FEP Smart Bit Flip & Non-LWP UECC Persistence Test

## Verification Criterion (VC)
驗證韌體在異常掉電（SPOR）情境下，針對不同 LUN 類型（Normal vs Non-LWP）及特定物理頁面（FEP）的錯誤處理機制：
1. **FEP Smart Flip 機制驗證**：確認透過 Vendor Command (0x4060/0x40F6/0xD060) 直接操作 NAND 層級，在 TLC 模式的 FEP (First Error Page) 頁面注入 150 個比特翻轉（Bit Flip）後，讀回資料能正確反映該錯誤，且 ECC 資訊（透過 0x409E）能正確回報錯誤位元數。
2. **Normal LUN SPOR 恢復驗證**：在 Normal LUN 寫入資料並注入 UECC 後，執行 HW_RESET（無 SSU），確認 LWP (Last Write Page) 狀態在重啟前後保持一致（LWP_A == LWP_B），代表韌體未觸發重建或狀態跳變，且資料完整性依賴於之前的寫入記錄。
3. **Non-LWP LUN UECC 殘留驗證**：在 Non-LWP 情境下（奇數 Plane 測試），於 Page 0 注入 UECC 並執行 HW_RESET（無 SSU），確認該錯誤資料未被自動修復，且寫入記錄（Write Record）正確標記為 Erase Pattern，驗證韌體在無保護機制下對非關鍵區域錯誤的容忍或殘留行為。

## Test Case (TC) Checkpoints

1. **[FEP_Smart_BitFlip_ECC_Verification]**：
   - 動作：針對指定 Die/Plane/Block 的 TLC 模式，透過 `issue_409D` 獲取 LWP 資訊並計算 FEP 頁面索引。使用 `issue_4060` 讀取原始 Raw Data，透過 `flip_bits_one_per_byte` 函數在 `raw_data_flip` 中注入 150 個比特翻轉（total_bits=150）。接著執行 `issue_D060` 擦除該 Block，並透過 `issue_C060` 將修改後的 payload 寫入 NAND 頁面。最後再次使用 `issue_4060` 讀取該頁面，並透過 `issue_409E` 獲取 ECC 錯誤位元數。
   - 預期結果：讀回的 Raw Data 應包含注入的 150 個比特錯誤；`issue_409E` 回報的 `errorBitNumber` 欄位應顯示對應的錯誤位元數量，確認 Vendor Command 能精確控制 NAND 層級的比特狀態並被 ECC 模組正確偵測。

2. **[Normal_LUN_SPOR_NoSSU_LWP_Stability]**：
   - 動作：在 Normal LUN (LUN 0) 寫入 2 頁 TLC 資料（`write_len = tlc_ce_page * ce_num * 2`）。針對 CE0 及當前 Plane `i` 的 Page `(newdata_pages-1)` 注入 UECC 錯誤（透過 `inject_UECC`）。記錄重啟前的 LWP 狀態為 `lwpA`（透過 `collect_lwp_checks`）。執行 `StartStopUnit` 模擬 SPOR 並執行 `HW_RESET`（無 SSU，`power_condition=0x03` 後接 `0x01` 喚醒）。重啟後再次獲取 LWP 狀態為 `lwpB`。比較 `lwpA` 與 `lwpB`，並透過 `read_compare` 驗證資料一致性。
   - 預期結果：`lwpA` 與 `lwpB` 必須完全相同（`identical == True`），代表在無 SSU 保護的 HW_RESET 下，韌體未改變 LWP 指標或觸發 PTE 重建。資料比對應通過，確認 UECC 錯誤在 Normal LUN 的特定頁面被保留或未被自動修正，但系統狀態穩定。

3. **[Non_LWP_LUN_UECC_Persistence_Check]**：
   - 動作：僅在奇數 Plane (`i % 2 == 1`) 執行。在 Page 0 注入 UECC 錯誤（`uecc_pca.l12_fpage = 0`）。記錄該區域的寫入資訊為 `nonlwp_old_data_startlba`，並透過 `save_write_info` 將其標記為 `CmdParamPatternMode.PTN_ERASE`。執行 SPOR 與 HW_RESET。重啟後執行 `read_compare`。
   - 預期結果：韌體應識別該 LBA 為 Non-LWP 區域，且在無 SSU 情況下，注入的 UECC 錯誤不會被自動修復。寫入記錄中的標記應正確反映為 Erase Pattern，驗證韌體在處理非關鍵寫入頁面時的錯誤處理邏輯與狀態記錄的一致性。