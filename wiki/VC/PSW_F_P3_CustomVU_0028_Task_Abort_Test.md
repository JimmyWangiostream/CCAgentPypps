# Test Spec: UFS Task Management Abort Counter Verification via Vendor Command 40F0

## Verification Criterion (VC)
驗證 UFS 韌體在啟用 Assert 機制後，針對不同 Task Management Function (TMF: ABORT_TASK, ABORT_TASK_SET, CLEAR_TASK_SET, LU_RESET) 與多種 SCSI Command (Write, Read, Verify, Other) 組合下的 Abort 行為一致性。核心驗證點包含：
1. **Assert 觸發機制**：確認透過 Vendor Command D0B0 啟用 Assert 後，發送特定 TM 序列能正確觸發韌體 Assert (預期 Assert Number 為 0xF400)，並透過 HW_RESET 後的健康報告 (Enhanced Health Report 40FE) 確認 Panic 計數增加且 Assert 標記正確。
2. **Abort 計數器精確性**：在禁用 Assert 後，透過 Vendor Command 40F0 讀取韌體內部的 Abort Hit Information。驗證發送隨機 SCSI 命令並夾雜 TM 命令後，40F0 回報的 `num_of_write_cmd_been_abort`、`num_of read_cmd_been_abort`、`num_of_other_cmd_been_abort` 以及 `total_number_of_abort_cmd` 的增量，必須與腳本實際統計到的被 Abort 命令數量完全一致。
3. **狀態一致性與邊界檢查**：確認 40F0 中的驗證欄位 (`verify_abort_*_wait`) 均為 0，且硬體佇列狀態 (`num_of_cmd_still_in_HW_queue`) 與各階段 Abort 計數器 (`abort_*_during_*_stage`) 在測試前後呈現非遞減趨勢（即計數器只增不減，或至少不減少），確保無計數器重置或丟失錯誤。

## Test Case (TC) Checkpoints

1. **[Assert_Trigger_and_Panic_Verification]**：
   - 動作：
     1. 配置 32 個 LUN (混合 Normal/Enhanced 記憶體類型)。
     2. 執行 RPMB Region 0 的 Key Programming (若尚未程式化)。
     3. 針對四種 TMF (`ABORT_TASK`, `ABORT_TASK_SET`, `CLEAR_TASK_SET`, `LU_RESET`) 分別執行以下循環：
        - 發送 Vendor Command **D0B0** 設定 `enable=1` (啟用 Assert 測試模式)。
        - 呼叫 `random_scsi` 生成包含隨機 SCSI 命令與目標 TMF 的命令佇列 (Queue)。
        - 發送命令佇列，預期觸發韌體 Assert。
        - 呼叫 `api.get_fw_assert_number()` 讀取 Assert 編號。
        - 嘗試執行 `UNIPRO_RESET` 或 `ENDPOINT_RESET`，預期失敗 (Fail)。
        - 執行 `HW_RESET` (Power Cycle) 恢復系統。
        - 發送 Vendor Command **40FE** 讀取 Enhanced Health Report。
        - 再次呼叫 `api.get_fw_assert_number()` 讀取 Assert 編號。
   - 預期結果：
     - `api.get_fw_assert_number()` 在 Assert 觸發後必須等於 **0xF400**。
     - Enhanced Health Report 中 `latest_assert_or_panic_triggered.value` 必須等於 **0xF400**，且 `total_panic_count.value` 必須大於 0。
     - HW_RESET 後清除 Assert 狀態，`api.get_fw_fw_assert_number()` 必須等於 **0x0**。

2. **[Abort_Counter_Increment_Check_Write_Read_Verify]**：
   - 動作：
     1. 發送 Vendor Command **D0B0** 設定 `enable=0` (禁用 Assert)。
     2. 發送 Vendor Command **40F0** 讀取初始 Abort 計數器狀態，儲存為 `data_40F0_backup`。
     3. 針對四種 TMF 與四種 Case (`ONLY_WRITE`, `ONLY_READ`, `ONLY_VERIFY`, `ONLY_OTHER`, `RANDOM`) 的組合執行：
        - 呼叫 `random_scsi` 生成命令佇列，並記錄被 TM 標記為 Abort 的命令索引對 `(target_index, tm_index)`。
        - 若 TMF 為 `LU_RESET`，額外 enqueue 一個 `TestUnitReady` 並設定 `wait_queue_empty=True`。
        - 發送命令佇列。
        - 遍歷 `abort_list`，對每個被 Abort 的目標命令，檢查其 CDB 類型：
          - 若為 `WRITE_6/10/16`，計數 `abort_w_cnt`。
          - 若為 `READ_6/10/16`，計數 `abort_r_cnt`。
          - 若為 `VERIFY_10` 或其他，計數 `abort_other_cnt` (其中 Verify 單獨計數 `verify_cnt`)。
        - 發送 Vendor Command **40F0** 讀取當前 Abort 計數器狀態，儲存為 `data_40F0`。
        - 計算增量：`diff = data_40F0.field.value - data_40F0_backup.field.value`。
        - 驗證以下增量是否等於對應的計數器：
          - `diff(num_of_write_cmd_been_abort) == abort_w_cnt`
          - `diff(num_of_read_cmd_been_abort) == abort_r_cnt`
          - `diff(num_of_other_cmd_been_abort) == abort_other_cnt`
          - `diff(total_number_of_abort_cmd) == total_abort_cnt`
          - `diff(verify_abort_cmd_wait) == verify_cnt`
   - 預期結果：
     - 所有上述增量比對必須完全相等，誤差為 0。這證明韌體內部追蹤的 Abort 事件與 Host 端觀察到的行為完全同步。

3. **[40F0_Validation_Fields_and_Hardware_Queue_Integrity]**：
   - 動作：
     - 在每次 40F0 讀取後，檢查以下特定欄位的數值：
       - `verify_abort_rw_done_wait`
       - `verify_abort_flush_done_wait`
       - `verify_abort_data_check_done_wait`
       - `verify_abort_repsonse_down_wait`
       - `l24_rev`
       - `l36_rev`
     - 檢查硬體佇列與階段性 Abort 計數器的非遞減性：
       - `num_of_cmd_still_in_HW_queue` (當前) >= `num_of_cmd_still_in_HW_queue` (Backup)
       - `abort_read_during_cmd_analysis_stage` (當前) >= (Backup)
       - `abort_read_during_dtm_read_queue_status_report_stage` (當前) >= (Backup)
       - `abort_write_during_cmd_analysis_stage` (當前) >= (Backup)
       - `abort_write_during_dtm_write_queue_status_report_stage` (當前) >= (Backup)
       - `abort_write_after_dataout_fill_write_cache` (當前) >= (Backup)
       - `abort_cmd_but_it_may_send_response_at_last` (當前) >= (Backup)
   - 預期結果：
     - 所有 `verify_abort_*_wait` 與 `l24_rev`、`l36_rev` 欄位的數值必須嚴格等於 **0**。這表示韌體在處理 Abort 時沒有進入未定義的等待狀態或發生版本衝突。
     - 所有硬體佇列與階段性 Abort 計數器必須呈現**非遞減**趨勢。若發現任何計數器減少，代表韌體內部狀態機在 Reset 或錯誤處理後錯誤地重置了統計資訊，測試應報錯。