# Test Spec: System Block EC Register Write/Read Consistency & Recovery Test

## Verification Criterion (VC)
驗證 UFS 韌體透過 Vendor Command `0xD048` 對系統關鍵區塊（FW CIS, BBM Table, Pointer Block）的 Erase Count (EC) 暫存器進行寫入與讀取的數據一致性，以及異常值（如 `0xFFFFFFFF`）的處理邏輯：Case 01 確認隨機生成的 EC 值能正確寫入並被讀回，驗證寫入路徑與讀取路徑的數據完整性；Case 02 確認 ISP Block EC 固定為 `0xFFFFFFFF` 時，系統能正確識別並維持該特定狀態碼，不將其視為普通計數值；Case 03 為恢復機制驗證，確認測試結束後能透過備份的原始 EC 值將系統狀態還原，確保測試環境的乾淨性與可重複性。

## Test Case (TC) Checkpoints
1. [Case01_Random_EC_Write_Read_Check]：
   - 動作：在 `pre_process` 階段備份原始的 FW CIS0 EC、FW CIS1 EC、BBM Table EC 及 Pointer Block EC 值。進入 `step1` 後，透過 `random.randint(1, 255)` 分別生成隨機的 `set_FW_CIS0`、`set_FW_CIS1`、`set_BBM_Table_EC` 與 `set_Pointer_Block_EC` 值。呼叫 `project_api.issue_D048_to_set_FW_BBT_and_system_block_EC` 將這些隨機值寫入對應的系統區塊 EC 暫存器。隨後再次呼叫 `get_and_print_system_block_ec` 讀取當前 EC 值，並與寫入前的隨機值進行逐項比對。
   - 預期結果：讀回之 `FW_CIS0`、`FW_CIS1`、`BBM_Table_EC` 與 `Pointer_Block_EC` 必須分別精確等於寫入時指定的隨機值。若任何一項不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，代表 Vendor Command `0xD048` 的寫入機制或內部 EC 計數器邏輯存在數據損毀或同步錯誤。

2. [Case02_ISP_Block_EC_Fixed_Value_Check]：
   - 動作：在 `step1` 中，將 `set_ISP_Block_EC` 硬編碼設定為 `0xFFFFFFFF`，並透過 `issue_D048_to_set_FW_BBT_and_system_block_EC` 執行寫入。接著在讀取階段，確認 `get_and_print_system_block_ec` 回傳的 `ISP_Block_EC` 值。
   - 預期結果：讀回之 `ISP_Block_EC` 必須等於 `0xFFFFFFFF`。此驗證旨在確認韌體對於 ISP Block 的 EC 狀態有特殊的定義或保留值處理，且該特殊值能透過 Vendor Command 正確寫入並被讀取機制正確識別，不會被誤判為普通整數或觸發非預期的錯誤檢查。

3. [Case03_EC_Recovery_Check]：
   - 動作：在 `step1` 結束前，呼叫 `self.recover_ec_setting()`。該函數會讀取 `pre_process` 階段儲存在 `self.cis_block_bkup`、`self.bbt_bkup` 與 `self.pointer_bkup` 中的原始 EC 值，並再次呼叫 `issue_D048_to_set_FW_BBT_and_system_block_EC` 將這些原始值寫回系統。
   - 預期結果：系統區塊的 EC 值必須完全恢復至測試開始前的初始狀態。此步驟確保測試腳本不會對 Flash 控制器的系統區塊狀態造成永久性污染，保證後續測試用例（TC）能在乾淨且一致的硬體狀態下執行，避免因 EC 計數器偏移導致的 Wear Leveling 或 Bad Block Management 邏輯異常。