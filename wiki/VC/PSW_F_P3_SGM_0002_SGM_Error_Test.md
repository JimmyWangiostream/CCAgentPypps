# Test Spec: UFS SGM (Self-Governing Management) Read Count Threshold & Retention Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 SGS (Self-Governing Scan) 機制在不同 LUN 類型（TLC/WB vs SLC）下的讀取計數（Read Count, RC）閾值觸發、VB Flagging 狀態管理、Event Log 計數一致性以及最終的 Retention Bitmap 更新邏輯：
1. **TLC/WB L2 模式**：驗證當 RC 未達閾值時，`sgs_scan_flagged_physical_vb_cnt` 為 0 且特定 VB 未標記；當 RC 達閾值並觸發 SGM Fail (D017) 後，該 VB 被標記（cnt=1），且在 Erase 觸發 SGM 掃描後，標記清除（cnt=0），同時 Event Count 正確遞增。
2. **SLC L2 模式**：驗證 Erase 前後 `sgs_scan_flagged_physical_vb_cnt` 的差值必須嚴格等於 Event Count 的增量，確保 SLC 模式下標記與事件計數的原子性一致性。
3. **Retention 邏輯**：驗證在特定 D017 參數組合下，若 VB 被標記且符合 Retirement Case，則 VB 必須進入 Retirement Bitmap；若不符合條件或 RC 未達閾值，則 VB 不得進入 Retirement Bitmap。
4. **RC 閾值遞進**：驗證當 Event Count 達到 5 時，系統自動切換至下一級 RC 閾值（RC_THRESHOLD_N），並重置相關計數器以繼續監控。

## Test Case (TC) Checkpoints

1. [Case01_TLC_WB_PreThreshold_FlagCheck]：
   - 動作：針對 TLC 或 WB LUN 寫入 1 VB 資料，透過 Vendor Command 0xC071 將觸發 SGM 的剩餘讀取計數設定為 `next_trigger_rc - 1`，執行 1 Byte Read 觸發讀取計數增加，隨後透過 Vendor Command 0x4071 讀取 SGS 參數。
   - 預期結果：`data_4071.curr_read_count_TLC` 小於 `next_gen_threshold_cnt`；`data_4071.sgs_scan_flagged_physical_vb_cnt` 必須等於 0；`data_4071.sgs_scan_flagged_physical_vbNumb[vb_number]` 必須等於 0。代表在讀取計數未達閾值前，韌體不會將該 VB 標記為異常。

2. [Case02_TLC_WB_PostThreshold_FlagCheck]：
   - 動作：在 TLC/WB LUN 上，透過 Vendor Command 0xC071 將觸發 SGM 的剩餘讀取計數設定為 `next_trigger_rc`（即達閾值），執行 1 Byte Read，隨後透過 Vendor Command 0x4071 讀取 SGS 參數。
   - 預期結果：`data_4071.curr_read_count_TLC` 大於或等於 `next_gen_threshold_cnt`；`data_4071.sgs_scan_flagged_physical_vb_cnt` 必須等於 1；`data_4071.sgs_scan_flagged_physical_vbNumb[vb_number]` 必須等於 1。代表讀取計數達閾值後，韌體正確將該 VB 標記為 Flagged。

3. [Case03_TLC_WB_SGM_Erase_CleanupCheck]：
   - 動作：在 TLC/WB LUN 上，先透過 Vendor Command 0xD017 注入 SGM Fail 條件（設定 `first_low_vt_scan=1` 等參數），接著執行 Unmap 與 Purge 操作觸發 Erase 以啟動 SGM 掃描流程。掃描結束後，透過 Vendor Command 0x4071 讀取 SGS 參數。
   - 預期結果：`data_4071.sgs_scan_flagged_physical_vb_cnt` 必須等於 0；`data_4071.sgs_scan_flagged_physical_vbNumb[vb_number]` 必須等於 0。代表 SGM 掃描完成後，已處理過的 Flagged VB 狀態被正確清除。

4. [Case04_SLC_EventCount_ConsistencyCheck]：
   - 動作：針對 SLC LUN，記錄 Erase 前的 `sgs_scan_flagged_physical_vb_cnt` (記為 `before`) 與 `sgs_scan_event_cnt_SLC[rc_level+1]` (記為 `last_event_cnt`)。執行 Unmap 與 Purge 觸發 SGM 掃描。掃描結束後，讀取新的 `sgs_scan_flagged_physical_vb_cnt` (記為 `after`) 與 `sgs_scan_event_cnt_SLC[rc_level+1]` (記為 `new_event_cnt`)。
   - 預期結果：必須滿足公式 `(new_event_cnt - last_event_cnt) == (before - after)`。代表 SLC 模式下，Event Count 的增量必須精確對應於被清除的 Flagged VB 數量，驗證計數邏輯的嚴謹性。

5. [Case05_Retention_Bitmap_Logic_Verification]：
   - 動作：根據 D017 注入參數判斷是否為 Retirement Case (`is_retirement_case`)。若 `vb_flagged[vb_number] == 1` 且 `is_retirement_case == True`，檢查 BBT 中該 VB 狀態；若 `is_retirement_case == False` 或 `vb_flagged[vb_number] == 0`，同樣檢查 BBT 狀態。
   - 預期結果：
     - 若 `vb_flagged[vb_number] == 1` 且 `is_retirement_case == True`：該 VB 必須在 BBT 中被標記為 Bad (Retired)。
     - 若 `vb_flagged[vb_number] == 1` 但 `is_retirement_case == False`：該 VB 不得在 BBT 中被標記為 Bad。
     - 若 `vb_flagged[vb_number] == 0`：該 VB 不得在 BBT 中被標記為 Bad。
     此步驟驗證韌體僅在特定條件下才將 VB 加入 Retirement Bitmap，避免誤殺。

6. [Case06_RC_Threshold_Adaptation_Check]：
   - 動作：監控 `sgs_scan_event_cnt_TLC[5]` 或 `sgs_scan_event_cnt_SLC[5]`。當計數值達到 5 時，檢查韌體是否透過 Vendor Command 0xC071 自動更新 `sgs_read_count_threshold_list[rc_level]` 至下一級閾值，並重置 `last_event_cnt` 為 0。
   - 預期結果：`rc_level` 索引必須遞增；`next_trigger_rc` 必須更新為新的 `sgs_read_count_threshold_list[rc_level]` 值；`sgs_scan_event_cnt` 的累計邏輯必須基於新的閾值重新計算，驗證 SGM 機制具備動態適應讀取頻率的閾值調整能力。