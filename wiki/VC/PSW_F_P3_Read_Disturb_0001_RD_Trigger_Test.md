# Test Spec: UFS Read Disturb (RD) Management Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Read Disturb (RD) 背景掃描機制的精確觸發條件、計數器更新邏輯及 Vendor Command (VU) 狀態一致性：
1. **RD 禁用狀態檢查**：確認當 RD 背景任務被 D018 命令禁用時，即使 VB Read Count (RC) 超過閾值，RD 觸發計數器 (`prdh_rand_trig_cnt`, `prdh_seq_trig_cnt`) 及健康報告計數器 (`vbs_scanned_by_read_disturb_counter`) 均保持不變。
2. **RD 啟用與掃描觸發檢查**：確認當 RD 背景任務啟用後，若目標 VB 的 RC 超過設定的 `RC_TH`，韌體必須觸發 RD 掃描。驗證 Smart Info 中的隨機觸發計數 (`prdh_rand_trig_cnt`) 或序列觸發計數 (`prdh_seq_trig_cnt`) 嚴格增加 1，且健康報告中的 `vbs_scanned_by_read_disturb_counter` 與 `read_disturb_in_background_counter` 同步增加。
3. **RC_TH 動態更新與 VU 一致性檢查**：確認 RD 掃描完成後，韌體會根據擦寫次數 (EC) 與區塊類型 (SLC/TLC, Open/Closed) 動態計算新的 `RC_TH` 並寫入內部表。透過 VU 40CB 命令讀取 `FlushRCTableThreshold_RC_TH_VB` 必須等於該計算值，且 `TotalReadCount_RC_VB` 必須等於當前實際 RC。同時驗證 `CECCThreshold_ReadDisturbScan` 等於配置中的 `RBER_FB_SF_4`，且 `IsScanTaskIdle` 狀態為 1。
4. **邊界條件與數據完整性**：驗證在 `RC_TH` 設為極大值 (Boundary Case) 時，RD 不應觸發；並最終透過 `read_compare` 確保 RD 掃描過程未導致資料損壞。

## Test Case (TC) Checkpoints

1. [RD_Disabled_No_Trigger_Check]：
   - 動作：針對 Normal LUN (TLC) 或 EM1 LUN (SLC) 寫入資料以建立 Open/Closed Block。讀取目標 VB 的初始 RC 與 Smart Info/Health Report 基線。透過 VU 命令將目標 VB 的 RC 設定為 `RC_ALL_WL_SCAN + 1` (Selection2) 或 `10` (Selection1)。執行 D018 命令設定 `flag=1` 禁用 RD 背景任務。重複讀取目標 LBA 10-100 次以累積 RC。再次讀取 Smart Info 與 Health Report。
   - 預期結果：Smart Info 中的 `prdh_rand_trig_cnt` 與 `prdh_seq_trig_cnt` 增加值必須為 0；Health Report 中的 `vbs_scanned_by_read_disturb_counter` 與 `read_disturb_in_background_counter` 增加值必須為 0。證明 RD 機制在禁用狀態下不會因 RC 超標而誤觸發。

2. [RD_Enabled_Selection1_Trigger_Check]：
   - 動作：保持 RD 禁用狀態，將目標 VB 的 RC 設定為 `10` (Selection1 條件)。執行 D018 命令設定 `flag=0` 啟用 RD 背景任務。輪詢等待 RD 掃描進入 Idle 狀態。讀取 Smart Info 與 Health Report。
   - 預期結果：Smart Info 中的 `prdh_rand_trig_cnt` 必須增加 1 (代表 RC < RC_ALL_WL_SCAN 的隨機觸發)；`prdh_seq_trig_cnt` 不變。Health Report 中的 `vbs_scanned_by_read_disturb_counter` 與 `read_disturb_in_background_counter` 必須各增加 1。驗證 RD 在啟用後能正確識別低閾值觸發條件。

3. [RD_Enabled_Selection2_Trigger_Check]：
   - 動作：重置 LUN 配置與寫入記錄。針對目標 VB 設定 RC 為 `RC_ALL_WL_SCAN * 1000000 + 1` (Selection2 條件)。執行 D018 命令設定 `flag=0` 啟用 RD 背景任務。輪詢等待 RD 掃描進入 Idle 狀態。讀取 Smart Info 與 Health Report。
   - 預期結果：Smart Info 中的 `prdh_seq_trig_cnt` 必須增加 1 (代表 RC >= RC_ALL_WL_SCAN 的序列觸發)；`prdh_rand_trig_cnt` 不變。Health Report 中的 `vbs_scanned_by_read_disturb_counter` 與 `read_disturb_in_background_counter` 必須各增加 1。驗證 RD 能正確區分高閾值觸發條件。

4. [RC_TH_Dynamic_Update_and_VU_Consistency_Check]：
   - 動作：在 RD 觸發掃描完成後，透過 VU 40CA 讀取當前 `RC_TH` 表，並透過 VU 40CB 讀取 `TotalReadCount_RC_VB`、`FlushRCTableThreshold_RC_TH_VB`、`CECCThreshold_ReadDisturbScan` 及 `IsScanTaskIdle`。計算理論上的新 `RC_TH` (基於當前 EC、VB 類型 SLC/TLC、Open/Closed 及 mConfig 參數)。
   - 預期結果：
     1. `FlushRCTableThreshold_RC_TH_VB` 必須等於計算出的理論新 `RC_TH` 值。
     2. `TotalReadCount_RC_VB` 必須等於當前讀取的實際 RC 值。
     3. `CECCThreshold_ReadDisturbScan` 必須等於 mConfig 中的 `RBER_FB_SF_4` 欄位數值。
     4. `IsScanTaskIdle` 必須等於 1。
     5. 若為非 Boundary Case，新的 `RC_TH` 必須大於掃描前的 `RC_TH` (韌體根據 EC 老化自動提升閾值)。

5. [Boundary_Case_No_RD_Trigger_Check]：
   - 動作：將目標 VB 的 `RC_TH` 設定為 `MAX_VALUE - 10` (0xFFFFFFFA)。執行 D018 啟用 RD 並輪詢 Idle。讀取 Smart Info 與 Health Report。
   - 預期結果：Smart Info 中的 `prdh_rand_trig_cnt` 與 `prdh_seq_trig_cnt` 增加值必須為 0；Health Report 計數器增加值必須為 0。證明當 RC 遠低於極高閾值時，RD 不會觸發。

6. [Data_Integrity_After_RD_Check]：
   - 動作：在所有 RD 觸發與 RC_TH 更新檢查完成後，執行 `api.read_compare` 對之前寫入的 write_record 進行全量讀取比對。
   - 預期結果：讀取比對必須全部通過 (Pass)。證明 Read Disturb 掃描過程（包括潛在的 CECC 修正或資料搬移）未導致任何資料損壞或比特翻轉。