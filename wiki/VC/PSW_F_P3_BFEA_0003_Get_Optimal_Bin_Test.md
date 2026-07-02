# Test Spec: UFS XTEMP Thermal Management & BFEA Scan Optimization Verification

## Verification Criterion (VC)
驗證 UFS 韌體在極端溫度條件下的 XTEMP 熱管理機制與 BFEA (Block Failure Early Assessment) 掃描優化邏輯：
1. **XTEMP 熱保護觸發驗證**：確認當 NAND 溫度超過 `XTEMP_REFRESH_T2` 閾值時，透過 Vendor Command 注入特定 EC (Error Correction) 參數並執行 HW_RESET，韌體應正確啟動 XTEMP 演算法以保護資料完整性；反之，當溫度低於 `XTEMP_REFRESH_T2 - 1` 時，應能正常寫入資料而不觸發異常保護機制。
2. **BFEA 掃描閾值與 Bin 選擇驗證**：
   - Case 5：當寫入容量小於 `PB_SCAN_ENABLE_PAGE_GAP + PB_SCAN_PAGE - 1` 時，BFEA 掃描結果應返回 Bin 1（代表未達最佳化掃描條件或僅進行基礎掃描）。
   - Case 7：當寫入容量達到或超過 `PB_SCAN_ENABLE_PAGE_GAP + PB_SCAN_PAGE`（並經過 Super Block 對齊）時，BFEA 掃描結果應返回 Bin 0（代表觸發完整掃描並找到最佳 Bin）。
   - Case 6：無寫入操作下，BFEA 應返回 Bin 1。
3. **BFEA 最佳 Bin 一致性驗證**：透過 Vendor Command `0x40B1` 獲取的最佳 Bin 編號，必須與透過 `0x4067` 單次讀取所有 16 個 Bin 的錯誤位元數後，計算出的最小錯誤位元數對應之 Bin 索引完全一致，且 `0x40B1` 返回的最佳錯誤位元數不得為 `0xFFFFFFFF`（代表無效數據）。

## Test Case (TC) Checkpoints

1. [Case05_BFEA_Bin1_Below_Threshold_Check]：
   - 動作：隨機啟用一個 Normal LUN (`random_en_lun`)，執行 Unmap 與 Purge 清除資料，禁用 ATS。計算寫入大小 `Write_Size = (PB_SCAN_ENABLE_PAGE_GAP + PB_SCAN_PAGE - 1) * 4 * 6 * CE_Count`。向該 LUN 寫入此大小的資料。透過 `lba_to_pba` 取得對應的 VB 與 CE 索引。呼叫 Vendor Command `0x40B1` (Get Best Bfea Scan) 並讀取 payload 前 4 位元組（Little Endian）。
   - 預期結果：`0x40B1` 返回的 Bin 編號必須等於 **1**。這代表在寫入容量未達到觸發完整 BFEA 掃描的頁數閾值時，韌體維持保守的掃描狀態。

2. [Case07_BFEA_Bin0_Above_Threshold_Check]：
   - 動作：隨機啟用一個 Normal LUN，執行 Unmap 與 Purge，禁用 ATS。計算寫入大小 `Write_Size = (PB_SCAN_ENABLE_PAGE_GAP + PB_SCAN_PAGE) * 4 * 6 * CE_Count`，並透過 `aligned_super_one_pass` 函數進行 Super Block 對齊調整。向該 LUN 寫入對齊後的資料。取得對應 VB 與 CE 索引。呼叫 Vendor Command `0x40B1` 並讀取 payload 前 4 位元組。
   - 預期結果：`0x40B1` 返回的 Bin 編號必須等於 **0**。這代表寫入容量達到閾值並對齊後，韌體觸發了更深入的 BFEA 掃描，並識別出最佳化的 Bin 設定。

3. [Case06_BFEA_Bin1_No_Write_Check]：
   - 動作：隨機啟用一個 Normal LUN，執行 Unmap 與 Purge，禁用 ATS。**不執行任何 Write 操作**。直接呼叫 Vendor Command `0x40B1` 並讀取 payload 前 4 位元組。
   - 預期結果：`0x40B1` 返回的 Bin 編號必須等於 **1**。確認在無新資料寫入的情境下，BFEA 狀態保持初始或保守模式。

4. [Case08_Hot_Risky_XTEMP_Trigger_Check]：
   - 動作：讀取 mConfig 中的 `XTEMP_ENABLE_PEC` 與 `XTEMP_REFRESH_T2`。透過 Vendor Command `0x404A` 相關機制（代碼中 `set_ec` 與 `do_hot_risky` 邏輯）設置 EC 值為 `XTEMP_ENABLE_PEC * 100 - 1`。執行 **HW_RESET** 以啟用 XTEMP 演算法。接著透過 Vendor Command 將 NAND 溫度設定為 `XTEMP_REFRESH_T2 + 1`（超過閾值）。向 Normal LUN 寫入 1 個 TLC VB 大小的資料。最後呼叫 `0x40B1` 檢查 BFEA 結果。
   - 預期結果：`0x40B1` 返回的 Bin 編號必須等於 **0**。這驗證了在溫度超過 `XTEMP_REFRESH_T2` 的高溫風險情境下，韌體不僅處理了熱保護，且 BFEA 掃描機制仍能正常運作並返回最佳 Bin。

5. [Case09_Cold_Risky_XTEMP_Normal_Check]：
   - 動作：透過 Vendor Command 將 NAND 溫度設定為 `XTEMP_REFRESH_T2 - 1`（低於閾值）。向 Normal LUN 寫入 1 個 TLC VB 大小的資料。最後呼叫 `0x40B1` 檢查 BFEA 結果。
   - 預期結果：`0x40B1` 返回的 Bin 編號必須等於 **0**。這驗證了在溫度低於閾值的正常/低溫情境下，寫入操作不會被 XTEMP 機制阻斷，且 BFEA 掃描正常執行。

6. [Case10_BFEA_Bin_Consistency_Verification]：
   - 動作：在 Case 7 或 Case 8 的寫入情境後，獲取 `0x40B1` 返回的最佳 Bin 編號 (`best_bin`)。接著，針對相同的 VB 與 CE，依序呼叫 Vendor Command `0x4067` (Single Read With Bin Option) 16 次（Bin 0 到 Bin 15），記錄每次返回的錯誤位元數 (`bin_result`)。找出 `bin_result` 中最小值對應的 Bin 索引列表 (`mini_bin_idx_list`)。同時檢查 `0x40B1` payload 第 8-11 位元組的 `best_error_bit`。
   - 預期結果：
     1. `best_bin` 必須存在於 `mini_bin_idx_list` 中。
     2. `best_error_bit` 必須不等於 **0xFFFFFFFF**（代表讀取有效）。
     3. 這確認了 `0x40B1` 彙總掃描結果的準確性與 `0x4067` 單次掃描結果的一致性。