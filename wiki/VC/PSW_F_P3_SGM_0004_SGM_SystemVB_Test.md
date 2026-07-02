# Test Spec: UFS SGM (Smart Garbage Management) Read Count Threshold & VB Flagging/Retirement Logic

## Verification Criterion (VC)
驗證 UFS 韌體中 SGS (Smart Garbage Scan) 機制在不同讀取計數 (Read Count, RC) 閾值下的行為邏輯：
1. **Case PTE (Pre-Trim Event)**：驗證當目標 VB 為 PTE 時，在 RC 低於觸發閾值前，SGS 標記計數 (`sgs_scan_flagged_physical_vb_cnt`) 與特定 VB 標記 (`sgs_scan_flagged_physical_vbNumb`) 均為 0；當 RC 達到閾值並觸發 SGM 後，標記計數變為 1，且該 VB 若符合 Retirement 條件則進入 Retirement Bitmap，否則僅標記但不退役。
2. **Case LOG (Log Block)**：驗證當目標 VB 為 LOG 時，透過 SSU (Start/Stop Unit) 命令強制觸發電源循環與狀態重置，確認 SGS 機制在 LOG 區塊上的標記與退役邏輯與 PTE 一致，特別關注 SSU 對韌體狀態機的影響。
3. **Case SWAP (Non-Trigger Flow)**：驗證當讀取計數被手動設定為低於觸發閾值 (`next_trigger_rc - 1`) 時，即使執行 HW_RESET，SGS 機制不應觸發標記或退役，確認 RC 閾值控制的精確性。
4. **動態閾值調整**：驗證當 `sgs_scan_event_cnt` 增加時，韌體是否正確根據 `sgs_scan_window_list` 調整 `next_gen_threshold_cnt` 與 `next_trigger_rc`，確保 SGS 掃描窗口隨壽命增加而動態變化。

## Test Case (TC) Checkpoints

1. **[Case01_PTE_Below_Threshold_No_Flagging]**：
   - 動作：配置 LUN 為全 TLC 模式，寫入全卡資料。透過 VU 0x4071 讀取初始 SGS 參數，獲取 `sgs_read_count_threshold`。透過 VU 0xC071 將 `sgs_scan_static_read_count` 設定為 `threshold - 1`。讀取 PTE VB 號碼。執行 HW_RESET。讀取 VU 0x4071 確認 `curr_read_count_SLC` 未增加（因無背景任務或讀取觸發），並檢查 `sgs_scan_flagged_physical_vb_cnt` 與 `sgs_scan_flagged_physical_vbNumb[PTE_VB]`。
   - 預期結果：`curr_read_count_SLC` 保持不變；`sgs_scan_flagged_physical_vb_cnt` 必須等於 0；`sgs_scan_flagged_physical_vbNumb[PTE_VB]` 必須等於 0。證明在 RC 低於觸發閾值時，SGS 機制不會對 PTE VB 進行標記。

2. **[Case02_PTE_Above_Threshold_Flagging_Check]**：
   - 動作：重置 LUN 配置為全 TLC。寫入全卡資料。獲取當前 RC 與 Threshold。透過 VU 0xC071 將 `sgs_scan_static_read_count` 設定為 `threshold` (觸發條件)。讀取 PTE VB 號碼。執行隨機寫入以觸發 GC 並讓目標 VB 進入 FREE_BLK_QUEUE_TABLE，隨後再次寫入確認 VB 離開 Free Table（模擬 VB 被標記為潛在壞塊或需掃描狀態）。透過 VU 0xD017 注入 SGM 失敗條件（模擬讀取錯誤或老化）。執行隨機寫入觸發 SGM 流程。讀取 VU 0x4071。
   - 預期結果：`sgs_scan_flagged_physical_vb_cnt` 必須等於 1；`sgs_scan_flagged_physical_vbNumb[PTE_VB]` 必須等於 1。證明當 RC 達到閾值且觸發 SGM 時，PTE VB 被正確標記。

3. **[Case03_PTE_Retirement_Bitmap_Verification]**：
   - 動作：在 Case02 觸發 SGM 後，讀取 VU 0x4071 確認 `sgs_scan_flagged_physical_vb_cnt` 變回 0（標記已處理）。透過 VU 0x405E 檢查目標 PTE VB 號碼是否存在於 Retirement Bitmap 中。同時檢查 BBT (Bad Block Table) 狀態。
   - 預期結果：若 D017 注入參數符合 Retirement 條件（如嚴重錯誤），則該 VB 必須在 Retirement Bitmap 中且不在 BBT 的普通壞塊區（或根據 Vendor 定義的 Retirement 邏輯）；若不符合 Retirement 條件，則 VB 不應在 Retirement Bitmap 中。確認 SGS 後的退役決策邏輯正確。

4. **[Case04_LOG_VB_SSU_Trigger_Flow]**：
   - 動作：配置 LUN 為全 TLC。寫入全卡資料。獲取 LOG VB 號碼。執行 SSU (Start/Stop Unit) 命令序列：先發送 `power_condition=0x02` (Stop/Idle) 並等待隊列空，再發送 `power_condition=0x01` (Start/Active) 並等待隊列空。此動作模擬電源循環或深度睡眠喚醒。隨後執行隨機寫入觸發 SGM。讀取 VU 0x4071。
   - 預期結果：`sgs_scan_flagged_physical_vb_cnt` 必須等於 1；`sgs_scan_flagged_physical_vbNumb[LOG_VB]` 必須等於 1。確認 SSU 命令序列能正確觸發韌體狀態更新並允許 SGS 機制對 LOG VB 進行標記，行為與 PTE 一致。

5. **[Case05_Dynamic_Threshold_Adjustment]**：
   - 動作：在 Case02 觸發第一次 SGM 事件後，讀取 VU 0x4071 中的 `sgs_scan_event_cnt_SLC[0]`。確認事件計數為 1。檢查 `sgs_scan_window_list[0]` 的值。計算新的 `next_gen_threshold_cnt` 應為 `current_read_count + sgs_scan_window_list[0]`。透過 VU 0xC071 更新參數，將 `sgs_scan_static_event_cnt[1]` 設為當前事件計數，並更新 `rc_level` 為 1。
   - 預期結果：韌體內部狀態應正確切換至 RC Level 1。下一次觸發 SGS 的閾值應基於新的窗口大小動態調整。確認 `sgs_scan_window_list` 中的值被正確應用於計算新的觸發點，確保 SGS 掃描頻率隨壽命增加而調整。

6. **[Case06_SWAP_Non_Trigger_Control]**：
   - 動作：配置 LUN 為半 SLC 半 TLC。寫入全卡。獲取 SGS 參數。透過 VU 0xC071 將 `sgs_scan_static_read_count` 設定為 `threshold - 1`。執行 HW_RESET。讀取 VU 0x4071 確認 `curr_read_count_SLC` 未增加。檢查 `sgs_scan_flagged_physical_vb_cnt`。
   - 預期結果：`sgs_scan_flagged_physical_vb_cnt` 必須等於 0。作為控制組，確認即使執行 HW_RESET，只要 RC 未達到閾值，SGS 機制絕對不會觸發標記或退役流程，排除韌體初始化時的誤觸發。