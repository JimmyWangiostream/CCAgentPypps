# Test Spec: SWL (Static Wear Leveling) Refresh Mechanism Verification with Manual EC Injection

## Verification Criterion (VC)
驗證 UFS 韌體中 Static Wear Leveling (SWL) 機制在特定 VB (Virtual Block) 的 Erase Count (EC) 被強制置零且觸發 Refresh 流程後的硬體狀態遷移與計數器行為：
1. **EC 注入與觸發邏輯**：確認透過 Vendor Command `C083` 將指定 `VBListNum` (如 INDEX_BLK, CURRENT_L1, CURRENT_L2_EM1 等) 的 EC 強制設為 0，並透過 `C072` 設定 SWL 閾值，確保該 VB 滿足 Refresh 條件。
2. **Booking Queue 優先級驗證**：確認在 Refresh 啟動前，透過 `40C5` 查詢的 Booking Queue 中，目標 VB 必須正確入隊，且其 `TheBookingUser` 欄位必須包含對應的 Priority (`BOOKING_IN_LP` 或 `BOOKING_IN_MP`) 與 User (`SWL_REFRESH_LOW_GAP` 或 `SWL_REFRESH_HIGH_GAP`) 標記。
3. **Refresh 執行與狀態遷移**：確認透過 Vendor Command `C088` 啟動 Refresh 並等待 BKOPS Idle 後，目標 VB 的 `VBListNum` 必須從原始 Pool (如 STATIC, DYNAMIC, ICS) 遷移至對應的 Free Block Queue (如 `FREE_BLK_QUEUE_EM1`, `FREE_BLK_QUEUE_TLC`, `FREE_BLK_QUEUE_TABLE`)。
4. **計數器一致性檢查**：確認 SWL 相關的全域計數器 (`totalSWLTriggerCount`, `totalSWLRefreshDoneCount`, `totalSWLRefreshMissCount`) 在 Refresh 前後呈現精確的遞增關係（Trigger +1, Done/Miss 總和 +1），且 `totalSWLJudgeCount` 與 `totalSWLRefreshBookCount` 在預處理階段已正確遞增。

## Test Case (TC) Checkpoints

1. [Pre_Process_EC_Initialization_and_Config]：
   - 動作：執行 `pre_process` 清除抑制模式，讀取 FW Geometry 計算 SLC/TLC VB Size，備份原始 VB 循環計數器 (`VB_list_cycle_address`)。針對所有組合 (Refresh Case, Trigger Case, Threshold Case, Config Case) 進行初始化：
     - 若 `ConfigCase.EM1_larger_than_30`，設定 SLC Ratio 為 0.5；否則為 0.25。
     - 根據 `Refresh Case` 決定 Pool 類型：`INDEX_BLK`/`TMP_CODE_BLK` -> `ICS`；`CURRENT_L2_EM1` 或 (`CURRENT_L1` 且 EM1>30) -> `Static`；其他 -> `Dynamic`。
     - 針對目標 `Refresh Case` 執行特定寫入操作以建立 VB：
       - `CURRENT_L1`: 寫入 16KB 至 TLC LUN (FUA=1)。
       - `CURRENT_L2_EM1`: 寫入 128MB 至 SLC LUN (FUA=0)。
       - `CURRENT_L2_TLC`: 寫入 128MB 至 TLC LUN (FUA=0)。
       - `CURRENT_L2_TLC_WB`: 啟用 `WRITEBOOSTER_EN` 旗標後寫入 128MB 至 SLC LUN，隨後關閉旗標。
     - 透過 `issue_4098` 獲取初始 Wear Leveling 資訊 (`wear_leveling_A`) 並建立 VB 索引字典。
     - 透過 `issue_C088` 停止 Refresh 並允許入隊 (`StopRefreshRefreshCanStillBeEnqueue`)。
     - 計算並設定 EC 閾值：根據 Pool 類型與 Threshold Case (TH1/TH2)，設定 `set_ec` 為對應閾值 +1。
     - 透過 `set_all_VB_erase_count` (Payload `C083`) 將目標 VB 的 EC 強制設為 0，其他 VB 設為 `set_ec`。
     - 若 `TriggerCase.is_cold`，透過 `set_ftl_version` 設定對應 Partition 的 Global Version 為 `Current + Delta_Threshold + 1`；否則設定 `set_version_dict`。
     - 透過 `issue_C072` 設定 SWL 全域 EC Gap 閾值。
   - 預期結果：目標 VB 的 EC 在 RAM 中被寫入為 0；SWL 閾值已正確配置；VB 版本號已根據 Trigger Case 更新，確保韌體識別該 VB 為需要 Refresh 的候選者。

2. [Pre_Refresh_Judge_Counters_Check]：
   - 動作：再次透過 `issue_4098` 獲取 Wear Leveling 資訊 (`wear_leveling_B`)。檢查 SWL 預處理計數器：
     - 若 Pool 為 `ICS`：檢查 `totalSWLJudgeCount_of_ICS_pool`, `totalSWLJudgePassCount_of_ICS_pool`, `totalSWLRefreshBookCount_of_ICS_pool` 是否均比 `wear_leveling_A` 增加 1。
     - 若 Pool 為 `Static`：檢查 `totalSWLJudgeCount_of_static_pool`, `totalSWLJudgePassCount_of_static_pool`, `totalSWLRefreshBookCount_of_static_pool` 是否均比 `wear_leveling_A` 增加 1。
     - 若 Pool 為 `Dynamic`：檢查 `totalSWLJudgeCount_of_dynamic_pool`, `totalSWLJudgePassCount_of_dynamic_pool`, `totalSWLRefreshBookCount_of_dynamic_pool` 是否均比 `wear_leveling_A` 增加 1。
   - 預期結果：上述計數器必須精確遞增 1，代表韌體在預處理階段已正確識別目標 VB 並將其加入 SWL 評估流程。

3. [Booking_Queue_Priority_and_Enqueue_Check]：
   - 動作：根據 `ThresholdCase` 決定預期優先級：
     - `TH1`: `Priority = BOOKING_IN_LP`, `BookingUser = SWL_REFRESH_LOW_GAP`。
     - `TH2`: `Priority = BOOKING_IN_MP`, `BookingUser = SWL_REFRESH_HIGH_GAP`。
     - 透過 `issue_40C5` 獲取 Booking Queue (`booking_q_before`)。
     - 遍歷 Queue，尋找 `VBListNum` 等於當前 `refresh_case` 的 Entry。
     - 驗證該 Entry 的 `TheBookingUser` 欄位 (Mask `0x700` 與 `MAX_BOOKING_USER_COUNT-1`) 必須同時包含預期的 `Priority` 與 `BookingUser`。
   - 預期結果：目標 VB 必須存在於 Booking Queue 中，且其優先級標記與當前 Threshold Case 嚴格匹配。若未找到或標記錯誤，測試失敗。

4. [Refresh_Execution_and_State_Transition_Check]：
   - 動作：
     - 透過 `issue_C088` 啟動 Refresh (`StartRefresh`)。
     - Polling 等待 BKOPS 進入 Idle 狀態。
     - 透過 `issue_4098` 獲取 Refresh 後 Wear Leveling 資訊 (`wear_leveling_C`)。
     - 檢查 SWL 執行計數器：
       - `totalSWLTriggerCount` (對應 Pool) 必須比 `wear_leveling_B` 增加 1。
       - `totalSWLRefreshMissCount` + `totalSWLRefreshDoneCount` 的總和必須比 `wear_leveling_B` 的總和增加 1。
     - 檢查目標 VB 的狀態遷移：
       - 若 `refresh_case` 為 `CURRENT_L1`，跳過此步驟 (因邏輯分支 break)。
       - 否則，遍歷所有 VB，找到 `VBListNum` 在 `wear_leveling_B` 中等於 `refresh_case` 的 VB。
       - 驗證該 VB 在 `wear_leveling_C` 中的 `VBListNum` 必須變更為對應的 Free Block Queue：
         - `ICS` Pool -> `FREE_BLK_QUEUE_TABLE`。
         - `Static` Pool -> `FREE_BLK_QUEUE_EM1`。
         - `Dynamic` Pool -> `FREE_BLK_QUEUE_TLC`。
       - 同時驗證該 VB 的 `OpenVBType` 可能發生變化 (若不同則記錄 Log，但不一定失敗，除非邏輯要求嚴格一致，此處主要檢查 VBListNum 遷移)。
   - 預期結果：SWL Trigger 計數器 +1，Done/Miss 總計數 +1。目標 VB 必須從原始 Pool (Static/Dynamic/ICS) 成功遷移至對應的 Free Block Queue，證明 Refresh 操作已物理執行並更新邏輯映射。

5. [Post_Process_Rollback]：
   - 動作：執行 `post_process`，將備份的 `erase_cnt_buffer_backup` 寫回 SRAM (`VB_list_cycle_address`)，恢復原始狀態。
   - 預期結果：系統狀態恢復至測試前，確保後續測試不受影響。