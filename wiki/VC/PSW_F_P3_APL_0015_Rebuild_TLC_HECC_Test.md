# Test Spec: UFS FTL Power Loss Recovery with Bit Flip Injection on TLC VB

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇異常掉電（HW_RESET without SSU）且 TLC 虛擬區塊（VB）內部頁面發生比特翻轉（Bit Flip）導致 HECC 錯誤時，Last Write Pointer (LWP) 的恢復行為與資料完整性：
1. **LWP 狀態檢查**：確認在注入 HECC 錯誤並執行無 SSU 的硬體重啟後，韌體未能自動修復該錯誤，導致 LWP 指標發生異常跳躍或倒退（LWP_B != LWP_A），證明韌體在無安全儲存單元保護下，無法從未修復的錯誤頁面恢復正常的寫入指針。
2. **資料一致性檢查**：確認儘管 LWP 指標異常，但透過 SW_COMPARE 驗證寫入記錄（Write Record）中的資料與原始注入前的資料完全一致，證明底層 NAND 資料本身未被損壞，問題僅在於韌體對 LWP 狀態機的管理邏輯。

## Test Case (TC) Checkpoints
1. [TLC_VB_Initialization_and_Hecc_Injection]：
   - 動作：
     1. 配置 LUN 0 (Normal), 1 (BootA), 2 (BootB), 3 (EM1)，並啟用 LUN 0 進行寫入。
     2. 針對 LUN 0 執行 `api.sequential_write`，寫入長度為 `tlc_ce_page * ce_num * 2` 的資料（覆蓋前 2 個 TLC 頁面週期）。
     3. 透過 `issue_4051_to_get_physical_address` 取得 LBA `tlc_ce_page * ce_num * 1 + i*4` 對應的 Physical Address (micron_pca)，鎖定特定的 Die, Plane, Block。
     4. 呼叫 `flipbit_on_TLC_smart` 函數：
        - 使用 `issue_409D_to_do_power_loss_analysing` 獲取該 Block 的 LWP 資訊。
        - 使用 `issue_4060_to_read_raw_data` 讀取該 Block 的原始頁面資料。
        - 在記憶體中對特定頁面（Page = lwp）的資料進行比特翻轉，具體為 `flip_bits_one_per_byte`，總共翻轉 150 個比特（`flipbit = 150`）。
        - 使用 `issue_D060_to_erase_specific_block` 擦除該物理 Block。
        - 使用 `issue_C060_to_write_raw_data` 將包含比特翻轉的資料寫回該物理 Block 的對應頁面。
        - 寫入後再次讀取並透過 `issue_409E_to_get_error_bit_numbers` 確認 ECC 錯誤位數，確保 HECC 錯誤已成功注入並被硬體偵測到。
   - 預期結果：
     - 物理 Block 內的特定頁面資料已被修改，且該頁面包含 150 個比特錯誤。
     - `issue_409E` 回傳的 `errorBitNumber` 應大於 0，證明硬體 ECC 模組已偵測到錯誤。
     - 韌體尚未執行重啟，LWP 仍指向寫入完成後的正常位置。

2. [LWP_A_Capture_and_HW_Reset_No_SSU]：
   - 動作：
     1. 在重啟前，呼叫 `collect_lwp_checks` 獲取當前的 LWP 狀態，儲存為 `lwpA`。
     2. 呼叫 `api.init_tester_to_unit_ready`，設定 `resetmode` 為 `HW_RESET` 且 `powerdown = False`（模擬異常掉電後上電，無 Secure Storage Unit 保護流程）。
     3. 韌體重新初始化後，再次呼叫 `collect_lwp_checks` 獲取新的 LWP 狀態，儲存為 `lwpB`。
   - 預期結果：
     - 系統成功從 HW_RESET 恢復並進入 Unit Ready 狀態。
     - 由於注入的 HECC 錯誤未被修復（無 SSU 觸發重建），韌體的 LWP 狀態機可能因讀取錯誤頁面而異常。
     - `lwpA` 與 `lwpB` 的比較結果 `identical` 應為 `False`，且 `diff_report` 顯示 LWP 指標發生變化（通常為 LWP 倒退或指向錯誤的頁面，因為韌體在恢復時嘗試驗證最後寫入的頁面，發現 HECC 錯誤且無法修正，導致寫入指針回滾或標記為錯誤狀態）。

3. [LWP_Difference_Verification_and_Data_Integrity_Check]：
   - 動作：
     1. 執行 `compare_lwp_checks(lwpA, lwpB)` 並檢查 `identical` 變數。
     2. 若 `identical == True`，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。
     3. 執行 `read_compare(self.write_record, CompareMethod.SW_COMPARE)`，將記憶體中記錄的寫入資料與實際讀取的 NAND 資料進行軟體層級比對。
   - 預期結果：
     - **LWP 檢查**：`identical` 必須為 `False`。這驗證了「無 SSU 保護下，HECC 錯誤會導致 LWP 狀態異常」這一硬體/韌體行為。
     - **資料完整性檢查**：`read_compare` 必須通過。這驗證了儘管 LWP 指標異常，但底層 NAND 中儲存的資料（包含注入的 150 個比特錯誤）與測試腳本預期寫入的資料完全一致，證明錯誤是可控注入的，且資料本身未被進一步損壞。