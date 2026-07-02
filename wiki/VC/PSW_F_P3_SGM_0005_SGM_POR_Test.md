# Test Spec: SGM (Smart Garbage Management) Read Count Threshold & Event Count Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 SGS (Smart Garbage Scan) 模組在 SLC、TLC 及 Write Booster 三種 LUN 配置下的 Read Count (RC) 閾值觸發機制與 Event Count 累積邏輯：
1. **RC 閾值與 Flag 狀態一致性**：驗證當 SLC/TLC 的 `curr_read_count` 未達 `next_gen_threshold_cnt` 時，`sgs_scan_flagged_physical_vb_cnt` 必須為 0 且特定 VB 未標記；當 RC 達到或超過閾值時，該 VB 必須被標記 (`flagged=1`)，且標記的 VB 必須屬於合法的 Policy Group (如 LOG_PTE, PTE_POOL 等)。
2. **Power Cycle 數據持久性**：驗證在 HW_RESET 或 RESET_N 後，SGS 的 `remain_read_count_trigger_sgs` (TLC/SLC) 不得重置為預設值 `0x1999999999999999`，且 `curr_read_count` 不得減少，確保電源循環不丟失讀取計數狀態。
3. **Erase 觸發 SGM 事件與標記清除**：驗證透過 Vendor Command `0xD017` 注入壞塊並執行 Unmap/Erase 後，觸發 SGM 流程，導致 `sgs_scan_event_cnt` 增加，同時 `sgs_scan_flagged_physical_vb_cnt` 歸零，且被標記的 VB 若符合 Retirement 條件則進入 Retirement Bitmap，否則僅標記清除但不進入 Retirement。
4. **多層級 RC 閾值遞進**：驗證當 `sgs_scan_event_cnt` 達到 1 且 `rc_level < 4` 時，系統會自動切換至下一層級 (`rc_level + 1`) 的 `sgs_read_count_threshold_list`，並重置相關計數器以繼續測試更高 RC 閾值下的行為，直到觸發第 5 層級事件 (`event_cnt[5]`) 為止。

## Test Case (TC) Checkpoints

1. [Case01_SLC_Flagging_Logic_Check]：
   - 動作：配置 SLC LUN (`slc_au=total_au`)，寫入 1 VB 資料，透過 VU `0xC071` 設定 `sgs_scan_static_read_count` 為 `next_trigger_rc - 1`，讀取 1 Byte 觸發計數。讀取 VU `0x4071` 確認 `curr_read_count_SLC` 小於 `next_gen_threshold_cnt`。
   - 預期結果：`sgs_scan_flagged_physical_vb_cnt` 必須等於 0；`sgs_scan_flagged_physical_vbNumb[vb_number]` 必須等於 0。若有任何 VB 被標記，該 VB 必須屬於 `VBPolicy.LOG_PTE` 組別，否則報錯。

2. [Case02_TLC_WB_Flagging_Logic_Check]：
   - 動作：配置 TLC 或 WB LUN (`tlc_au=total_au`)，寫入 1 VB 資料，透過 VU `0xC071` 設定 `sgs_scan_dynamic_read_count` 為 `next_trigger_rc - 1`，讀取 1 Byte。讀取 VU `0x4071` 確認 `curr_read_count_TLC` 小於 `next_gen_threshold_cnt`。
   - 預期結果：`sgs_scan_flagged_physical_vb_cnt` 必須等於 0；`sgs_scan_flagged_physical_vbNumb[vb_number]` 必須等於 0。

3. [Case03_RC_Threshold_Reached_Flagging]：
   - 動作：重複寫入與讀取操作，直到 `curr_read_count` (TLC/SLC) >= `next_gen_threshold_cnt`。此時 `flagged` 變數為 False，進入下一分支檢查。
   - 預期結果：`sgs_scan_flagged_physical_vb_cnt` 必須等於 1；`sgs_scan_flagged_physical_vbNumb[vb_number]` 必須等於 1。若為 SLC，所有被標記的 VB 必須屬於 `VBPolicy.LOG_PTE_SLC` 組別 (包含 LOG_TAB_BLK, CURRENT_PTE, PTE_POOL, USED_BLK_POOL_SLC)。

4. [Case04_PowerCycle_Persistence_Check]：
   - 動作：執行 HW_RESET 或 RESET_N，重新初始化後讀取 VU `0x4071`。
   - 預期結果：
     - `sgs_scan_event_cnt_TLC[rc_level+1]` 與 `sgs_scan_event_cnt_SLC[rc_level+1]` 必須等於 0。
     - `sgs_scan_flagged_physical_vb_cnt` 與 `sgs_scan_flagged_physical_vbNumb[vb_number]` 必須與 Reset 前數值完全一致。
     - `remain_read_count_trigger_sgs_TLC` (或 SLC) 絕對不等於 `0x1999999999999999`。
     - `curr_read_count_TLC` (或 SLC) 必須 >= Reset 前的數值，不得減少。

5. [Case05_Interval_Calculation_Check]：
   - 動作：當 `current_read_count >= next_gen_threshold_cnt` 時，計算 `interval = remain - current_read_count`。
   - 預期結果：`interval` 必須滿足 `1 <= interval <= sgs_scan_window_list[rc_level].value`。若不滿足，則驗證失敗。

6. [Case06_Erase_Trigger_SGM_Event_Increment]：
   - 動作：透過 VU `0xD017` 針對當前 VB 注入壞塊參數，執行 Unmap 與 Purge 觸發 Erase。讀取 VU `0x4071`。
   - 預期結果：
     - 若為 TLC/WB：`sgs_scan_event_cnt_TLC[rc_level+1]` 必須等於 `last_event_cnt + 1` (若之前未達標) 或 `last_event_cnt` (若之前已達標且 flagged=False)。
     - 若為 SLC：`sgs_scan_event_cnt_SLC[rc_level+1] - last_event_cnt` 必須等於 `sgs_scan_flagged_physical_vb_cnt` 的變化量 (Before - After)。

7. [Case07_Flag_Cleared_After_SGM]：
   - 動作：在 Erase 觸發 SGM 後，讀取 VU `0x4071`。
   - 預期結果：
     - 若為 TLC/WB：`sgs_scan_flagged_physical_vb_cnt` 必須等於 0；`sgs_scan_flagged_physical_vbNumb[vb_number]` 必須等於 0。
     - 若為 SLC：所有 `sgs_scan_flagged_physical_vbNumb[i]` 若不等於 0，該 VB 必須屬於 `VBPolicy.LOG_PTE` 組別。

8. [Case08_Retirement_Bitmap_Verification]：
   - 動作：檢查當前 VB 是否進入 Retirement。透過 VU `0x405E` 檢查 Retirement Bitmap，並透過 `check_vb_in_BBT` 確認 BBT 狀態。
   - 預期結果：
     - 若 `is_retirement_case` 為 True 且 VB 之前已被標記 (`vb_flagged[vb_number] == 1`)：`is_bad_blk` 必須為 True (即進入 Retirement)。
     - 若 `is_retirement_case` 為 False：`is_bad_blk` 必須為 False (即未進入 Retirement，僅標記清除)。
     - 若為首次觸發 (`first_time==True`) 或 `flagged==False`：VB 不得進入 Retirement (`is_bad_blk` 應為 False)。

9. [Case09_RC_Level_Switching_Check]：
   - 動作：當 `sgs_scan_event_cnt` 等於 1 且 `rc_level < 4` 時，透過 VU `0xC071` 將 `sgs_scan_dynamic_read_count` (或 static) 設定為 `sgs_read_count_threshold_list[rc_level].value`，並遞增 `rc_level`。
   - 預期結果：系統成功切換至下一 RC 閾值層級，`next_gen_threshold_cnt` 更新為 `current_read_count + sgs_scan_window_list[rc_level].value`，且 `last_event_cnt` 重置為 0，繼續循環直到 `event_cnt[5]` 觸發。