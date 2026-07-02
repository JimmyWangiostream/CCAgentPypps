# Test Spec: UFS SGS (Sudden Good Scan) Mechanism Validation & Event Log Control

## Verification Criterion (VC)
驗證 UFS 韌體中 SGS (Sudden Good Scan) 機制在不同 LUN 配置 (TLC/WB/SLC) 下的觸發邏輯、標記狀態機轉換、以及 Event Log 的禁用/重啟行為：
1. **SGS 參數一致性**：確認 Vendor Command 4056/4071 讀取的 SGS 閾值 (RC_TH) 與視窗 (Window) 經過 CE (Chip Enable) 與時間單位轉換後，與內部參數完全一致。
2. **SGM (Sudden Good Management) 失效處理**：驗證在強制注入 SGS 失敗情境下，根據 `enable_retirement` 參數，Bad Block 是否正確進入 BBT (Bad Block Table) 或保留在 Free Block 狀態。
3. **SGS 標記與清除邏輯**：驗證在 TLC/WB/SLC 模式下，當 Read Count (RC) 未達閾值時 VB 不被標記；當 RC 達到閾值並執行 Erase 觸發 SGM 後，Flagged VB Count 歸零且 Event Count 正確遞增；驗證 SLC 模式下 Erase 前後 Flagged VB Count 的差值與 Event Count 增量的一致性。
4. **Event Log 禁用機制**：驗證 Vendor Command D0F8 禁用特定 Event Log (0x6008, 0x6009, 0x0026) 後，觸發 SGS 事件時不會寫入新 Log；驗證 H8 (Hibernate) 進入/退出後，禁用狀態保持；驗證 HW_RESET 或 UNIPRO_RESET 後，禁用狀態解除，且新觸發的 SGS 事件能正確寫入並通過 Event Log 內容比對。

## Test Case (TC) Checkpoints

1. **[SGS_Param_Conversion_Check]**：
   - 動作：透過 Vendor Command 4056 讀取 mConfig 資料，提取 `SGS_TOUCHUP_ERASE_SWITCH`, `SGSSCAN_RC_TH`, `SGSSCAN_RC_0~3`, `SGSSCAN_W_0~4` 等欄位數值。接著透過 Vendor Command 4071 獲取系統當前 SGS 掃描參數 (`sgs_read_count_threshold`, `sgs_read_count_threshold_list`, `sgs_scan_window_list`)。將 mConfig 讀取的 RC 值乘以 `1,000,000,000 * CE`，將 Window 值乘以 `1,000,000 * CE` 進行單位與硬體縮放轉換，並與 4071 返回的數值進行逐項比對。同時確認初始狀態下 `sgs_scan_event_cnt_TLC` 與 `sgs_scan_event_cnt_SLC` 均為 0。
   - 預期結果：轉換後的 mConfig 數值必須與 4071 返回的系統參數數值完全相等；初始 Event Count 必須為 0，確認 SGS 參數初始化與單位轉換邏輯正確。

2. **[SGM_Fail_Retirement_Check]**：
   - 動作：選擇 `FREE_BLK_QUEUE_MLC` 中的 Free Block，透過 Vendor Command D017 強制注入 SGS 失敗錯誤。接著發送 Vendor Command 404B 觸發 SGM 擦除，分別測試 `enable_retirement=0` 與 `enable_retirement=1`，以及 `error_inject_enable=0` (無錯誤) 的情境。檢查 404B 返回結果碼，並使用 `check_vb_in_BBT` 驗證該 VB 是否被標記為 Bad Block。
   - 預期結果：
     - 當 `error_inject_enable=1` 且 `enable_retirement=0` 時：404B 返回 0，且該 VB **不**在 BBT 中 (保留為 Free Block)。
     - 當 `error_inject_enable=1` 且 `enable_retirement=1` 時：404B 返回 0，且該 VB **在** BBT 中 (被 Retirement)。
     - 當 `error_inject_enable=0` 時：404B 返回 1，且該 VB **不**在 BBT 中。

3. **[TLC_WB_SGS_Flagging_Logic_Check]**：
   - 動作：配置 LUN 為 TLC 或 WB 模式。手動調整 SGS 動態讀取計數器 (`sgs_scan_dynamic_read_count`) 至 `next_trigger_rc - 1`。寫入 1 個 VB 資料，讀取 1 Byte 觸發讀取計數增加。檢查 Vendor Command 4071 返回的 `sgs_scan_flagged_physical_vb_cnt` 與 `sgs_scan_flagged_physical_vbNumb[vb_number]`。
   - 預期結果：由於讀取計數未達閾值 (`current_read_count < next_gen_threshold_cnt`)，`sgs_scan_flagged_physical_vb_cnt` 必須為 0，且該 VB 的 Flag 狀態必須為 0。

4. **[TLC_WB_SGS_Flagging_Threshold_Check]**：
   - 動作：手動調整 SGS 動態讀取計數器至 `next_trigger_rc` (達到閾值)。寫入 1 個 VB 資料，讀取 1 Byte。檢查 Vendor Command 4071 返回的 `sgs_scan_flagged_physical_vb_cnt` 與 `sgs_scan_flagged_physical_vbNumb[vb_number]`。
   - 預期結果：由於讀取計數已達閾值，`sgs_scan_flagged_physical_vb_cnt` 必須為 1，且該特定 VB 的 `sgs_scan_flagged_physical_vbNumb` 欄位必須為 1。

5. **[TLC_WB_SGS_Erase_Clear_Check]**：
   - 動作：在 VB 被標記 (Flagged) 後，執行 Unmap 與 Purge 操作觸發 Erase，進而觸發 SGM 流程。檢查 Vendor Command 4071 返回的 `sgs_scan_event_cnt_TLC[rc_level+1]` 與 `sgs_scan_flagged_physical_vb_cnt`。
   - 預期結果：`sgs_scan_event_cnt_TLC[rc_level+1]` 必須比上一次記錄值增加 1；`sgs_scan_flagged_physical_vb_cnt` 必須歸零為 0，且該 VB 的 Flag 狀態歸零，確認 SGM 觸發後標記已清除。

6. **[SLC_SGS_Event_Cnt_Delta_Check]**：
   - 動作：配置 LUN 為 SLC 模式。在 VB 被標記後，執行 Unmap 與 Purge 觸發 Erase。記錄 Erase 前的 `sgs_scan_flagged_physical_vb_cnt` (記為 `before`) 與 Erase 後的 `sgs_scan_flagged_physical_vb_cnt` (記為 `after`)，以及 `sgs_scan_event_cnt_SLC[rc_level+1]` 的增量。
   - 預期結果：`sgs_scan_event_cnt_SLC[rc_level+1]` 的增量 (`event_cnt - last_event_cnt`) 必須嚴格等於 `sgs_scan_flagged_physical_vb_cnt` 的減少量 (`before - after`)，確認 SLC 模式下 Event Count 與 Flagged VB 數量變化的嚴格對應關係。

7. **[Event_Log_Disable_Persistence_Check]**：
   - 動作：發送 Vendor Command D0F8 禁用 Event Log ID 0x6008 (及可選 0x0026)。觸發 SGS 事件 (Touchup + Scan + Retirement)。檢查 Event Log 中這些 ID 的條目數量是否與禁用前相同。接著執行 H8 (Hibernate) 進入與退出循環。再次觸發 SGS 事件，檢查 Event Log 條目數量是否仍保持不變。
   - 預期結果：禁用 D0F8 後及 H8 循環後，觸發 SGS 事件時，被禁用的 Event Log ID (0x6008 等) 的條目數量必須與禁用前完全一致 (無新增)，確認禁用狀態在低功耗狀態下保持有效。

8. **[Event_Log_Reset_Reenable_Check]**：
   - 動作：在禁用 Event Log 後，執行 HW_RESET 或 UNIPRO_RESET。觸發 SGS 事件。檢查 Event Log 中這些 ID 的條目數量是否比禁用前增加 1。提取最新的一筆 Log，使用對應的比對函數 (`compare_eventlog_0x6008` 等) 驗證 Log 內容中的參數 (如 Block, Die, Plane, Error Type) 是否與觸發 SGS 時的參數一致。
   - 預期結果：Reset 後禁用狀態解除，觸發 SGS 事件後，被禁用的 Event Log ID 條目數量必須增加 1；最新 Log 的內容必須與觸發時的硬體狀態參數完全匹配，確認 Reset 後 Event Log 機制恢復正常運作。