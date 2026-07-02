# Test Spec: EM1 LUN SLC Mode UECC Injection & HW_RESET Without SSU Persistence Test

## Verification Criterion (VC)
驗證在 EM1 LUN (LUN 3) 配置為 SLC 模式並執行連續寫入後，針對特定物理頁（Page 0）的特定 CE/Plane 注入 UECC 錯誤，隨後執行無 SSU 保護的 HW_RESET。驗證韌體在無 Secure Storage Unit 介入的情況下，LWP (Logical Write Pointer) 狀態是否保持一致，且未修復的 UECC 錯誤數據（Pattern 0xFF/Erase State）是否正確殘留於對應 LBA 區域，確認韌體不會在無 SSU 重置時自動修復或清除該特定 LWP 的錯誤標記。

## Test Case (TC) Checkpoints
1. [EM1_SLC_Write_UECC_Injection_Check]：
   - 動作：
     1. 配置 LUN 0 (Normal), 1 (Boot A), 2 (Boot B), 3 (EM1) 為啟用狀態，其中 EM1 LUN 設定為 Enhanced 1 記憶體類型，邏輯區塊大小 4KB。
     2. 針對 EM1 LUN (LUN 3) 從 LBA 0 開始執行順序寫入，寫入長度為 `slc_ce_page * ce_num * 2` (即 2 個 SLC 寫入週期的容量)，chunk size 為 `slc_ce_page`，並啟用 FUA 與 HW Compare。
     3. 獲取當前 EM1 LUN 的 Open VB 資訊，提取 `open_logical_VB_number_for_EM1_L2_Host` 作為目標 VB 號碼。
     4. 建構 PCA (Physical Cell Address) 結構，設定目標為：Block = 目標 VB, CE = 0, Plane = 當前循環索引 `i`, Page = 0。
     5. 呼叫 `inject_UECC(uecc_pca)` 在該物理頁注入 UECC 錯誤。若 `ce_num > 1`，則額外對 CE=1, Plane=`i`, Page=0 注入 UECC。
     6. 記錄注入後未寫入新資料的 LBA 範圍 (`nonlwp_old_data_startlba`)，其起始 LBA 為 `4*i`，長度為 4 (對應 SLC 寫入的特定區塊)。
     7. 呼叫 `collect_lwp_checks` 獲取當前各 Plane 的 LWP 狀態，儲存為 `lwpA`。
     8. 執行 `api.init_tester_to_unit_ready` 進行 HW_RESET，設定 `resetmode` 為 `HW_RESET` 且 `powerdown` 為 False (無 SSU 電源循環)。
     9. 重置後再次獲取 EM1 LUN 的 Open VB 資訊及 LWP 狀態，儲存為 `lwpB`。
     10. 比較 `lwpA` 與 `lwpB`，並針對之前標記的 `nonlwp_old_data_startlba` 區域執行讀取比較，預期數據為 Erase Pattern (0xFF)。

   - 預期結果：
     1. `lwpA` 與 `lwpB` 必須完全相同 (`identical == True`)，代表 HW_RESET 無 SSU 時，LWP 指針狀態未發生跳變或重置。
     2. 針對 `nonlwp_old_data_startlba` (LBA 4*i) 及其後續 4 個 LBA 的讀取數據必須等於 `CmdParamPatternMode.PTN_ERASE` (即 0xFF 或 Erase State)，代表注入 UECC 的頁面數據未被韌體自動修復或覆蓋，錯誤數據殘留於 Flash 中。
     3. 若 `ce_num > 1`，CE=1 對應的 LBA 區域 (`nonlwp_old_data_startlba_2`) 同樣必須讀取到 Erase Pattern。