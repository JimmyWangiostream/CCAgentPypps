# Test Spec: VC-30 (12.f) Program Fail Injection & Early Replacement Pool Verification

## Verification Criterion (VC)
驗證韌體在遭遇程式寫入失敗（Program Fail, PF）時的錯誤處理與區塊替換機制：
1. **錯誤注入與狀態確認**：透過 Vendor Command `0xC012` 強制在目標 LOG VB 區塊注入 Program Fail 錯誤，確認韌體能正確識別該區塊為失效狀態。
2. **動態替換邏輯驗證**：在正常寫入流量（Write10）持續進行下，當 LOG VB 發生切換（即韌體選擇了新的備用區塊作為 LOG 寫入點）時，確認此「新選取的 VB」確實來自於韌體內部的 Early Replacement Pool（早期替換池），而非隨機或舊有區塊。
3. **BBT 一致性檢查**：在 LOG VB 切換並觸發 PF 後，讀取 Bad Block Table (BBT) 狀態，確認失效區塊（原 LOG VB）已被正確標記為 Bad Block，且總 Bad Block 計數器（BB Count）嚴格增加 1，證明韌體更新了 BB Table 且未發生 Assert 或系統崩潰。

## Test Case (TC) Checkpoints
1. [Case01_Initial_State_Logging]：
   - 動作：執行 Vendor Command `0x40C1` 獲取當前 Open VB 資訊，提取 `LOG_block_VB_number_logical` 作為初始 LOG VB (`LOG_vb`)；執行 Vendor Command `0x40DC` 獲取下一個 Open VB 資訊，提取 `LOG` 欄位作為目標注入區塊 (`LOG_vb_next`)；執行 Vendor Command `0x405E` 獲取當前 Bad Block 計數 (`BB_count`) 與初始 BBT 資料。
   - 預期結果：成功獲取有效的 `LOG_vb`、`LOG_vb_next` 及初始 `BB_count`，為後續注入與比對建立基準狀態。

2. [Case02_Program_Fail_Injection]：
   - 動作：建構 `PhysicalAddressInformation` 結構體，指定 CE=0, Plane=0, Block=`LOG_vb_next`, Page=0，並透過 Vendor Command `0xC012` 呼叫 `issue_C012_to_create_program_erase_fail` 函數，設定 `fail_type=0` 在目標區塊 `LOG_vb_next` 注入 Program Fail 錯誤。記錄目標區塊資訊 (`target_data_LOG`)。
   - 預期結果：韌體成功接收並處理 `0xC012` 指令，在硬體層面模擬該區塊的寫入/擦除失敗，且系統未因注入錯誤而立即崩潰或 Assert。

3. [Case03_Write_Flow_VB_Switch_Check]：
   - 動作：進入迴圈執行隨機 Write10 操作（長度為 `WRITE_10_MAX_BLOCK_LEN`，LBA 隨機），每次寫入後透過 Vendor Command `0x40C1` 讀取當前 `LOG_block_VB_number_logical` (`LOG_vb_new`)。持續寫入直到 `LOG_vb_new` 不等於初始 `LOG_vb`，即確認 LOG VB 已發生切換。
   - 預期結果：Write10 操作正常完成，韌體在內部邏輯判斷需要更換 LOG 寫入點時，成功將 LOG VB 切換至新的 VB 號碼，證明韌體具備動態管理 LOG 區塊的能力。

4. [Case04_BBT_Update_Verification]：
   - 動作：在 LOG VB 切換後，執行 Vendor Command `0x4013` 獲取 BE (Block Error) 失敗狀態；接著再次執行 Vendor Command `0x405E` 獲取新的 Bad Block 資訊，計算新的 `BB_count_new` 與 `BB_data_new`。
   - 預期結果：
     1. `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明失效區塊已被計入 Bad Block 總數。
     2. 在 `BB_data_new` 中必須能找到包含 `target_data_LOG` (即原注入的 `LOG_vb_next` 區塊資訊) 的條目，證明該特定區塊已被正確標記為 Bad Block。
     3. 整個流程中韌體未觸發 Assert 或異常中斷，確認韌體在處理 Program Fail 並更新 BB Table 時的穩定性。