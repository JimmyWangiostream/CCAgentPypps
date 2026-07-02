# Test Spec: UFS SGM (Sudden Garbage Collection Management) Read Count Threshold & Event Count Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 SGM (Sudden Garbage Collection Management) 機制在不同 LUN 類型 (TLC/SLC/WB) 及多層級 Read Count (RC) 閾值下的行為一致性：
1. **SGD 參數設置與標記邏輯**：確認透過 Vendor Command `0xC071` 設置動態/靜態 RC 計數器後，當讀取次數觸發閾值時，目標 Virtual Block (VB) 必須被正確標記為 `sgs_scan_flagged_physical_vbNumb = 1`，且總標記數 `sgs_scan_flagged_physical_vb_cnt` 符合預期。
2. **Erase 觸發 SGM 事件計數**：確認對已標記 VB 執行 Unmap/Erase 操作後，韌體內部 SGM 事件計數器 (`sgs_scan_event_cnt`) 的增量必須嚴格等於「被清除的標記 VB 數量」減去「因壞塊管理 (BBT) 被歸檔至 REVOKE_BLK 的 VB 數量」。
3. **標記清除與退休狀態驗證**：確認 SGM 觸發後，非退休 (Retirement) 的 VB 標記必須清零；對於觸發 `D017` 壞塊注入的 VB，必須透過 Vendor Command `0x405E` 驗證其狀態已正確更新至 Retirement Bitmap (BBT)，且未觸發壞塊的 VB 不得進入 Retirement 狀態。

## Test Case (TC) Checkpoints

1. [Case01_TLC_WB_SLC_Flagging_Check]：
   - 動作：針對 TLC_L2, WB_L2, SLC_L2 三種配置，分別寫入指定數量的 VB。透過 `issue_4071_to_get_SGD_scan_parameter` 獲取初始 SGS 參數。接著針對每個 VB，透過 `issue_C071_to_set_SGD_scan_parameters` 將對應的動態或靜態 RC 計數器設置為 `next_trigger_rc - 1`，並對該 VB 執行 1 Byte 讀取操作 (`read_data`) 以模擬讀取計數累積。最後再次讀取 SGS 參數。
   - 預期結果：
     - **TLC_L2/WB_L2**：`sgs_scan_flagged_physical_vb_cnt` 必須等於寫入的 VB 總數加上之前累積的 `revoke_vb_list` 長度；每個寫入 VB 的 `sgs_scan_flagged_physical_vbNumb[vb_number]` 必須等於 `1`。
     - **SLC_L2**：`sgs_scan_flagged_physical_vb_cnt` 必須大於等於 1；且所有被標記的 VB 必須屬於 `VBPolicy.LOG_PTE_SLC_RVK` 定義的群組 (LOG_TAB_BLK, CURRENT_PTE, PTE_POOL, 或 USED_BLK_POOL_SLC)。
     - **ALLTYPE**：`sgs_scan_flagged_physical_vb_cnt` 必須大於等於 `7 - len(revoke_vb_list)` (即至少 6 個 TLC + 1 個 SLC)；TLC VB 的標記必須為 1；非 TLC 且被標記的 VB 必須屬於 `VBPolicy.LOG_PTE_SLC_RVK` 群組。

2. [Case02_Erase_EventCount_Increment_Check]：
   - 動作：記錄擦除前的 `sgs_scan_flagged_physical_vb_cnt` (記為 `physical_cnt_before_erase`)。針對所有寫入的 VB 執行 Unmap/Erase 操作 (`unmap_data` + `purge_operation`)。擦除後立即讀取 SGS 參數，獲取新的 `sgs_scan_flagged_physical_vb_cnt` (記為 `physical_cnt_after_erase`) 以及對應層級 (`rc_level+1`) 的 `sgs_scan_event_cnt`。計算事件計數增量 `delta_event = event_cnt - last_event_cnt` 與標記 VB 數量增量 `diff = physical_cnt_before_erase - physical_cnt_after_erase` (需根據 LUN 類型調整 TLC/SLC 的減去項)。
   - 預期結果：
     - **TLC_L2/WB_L2**：`sgs_scan_event_cnt_TLC[rc_level+1]` 的增量必須等於 `total_vb_cnt - len(current_revoke_vb_list)`。
     - **SLC_L2**：`sgs_scan_event_cnt_SLC[rc_level+1]` 的增量必須嚴格等於 `diff` (即擦除前後標記 VB 數量的差值)。
     - **ALLTYPE**：TLC 事件計數增量必須等於 `vb_num * 2 - len(current_revoke_vb_list)`；SLC 事件計數增量必須等於 `diff` (其中 diff 已扣除 6 個 TLC 的影響)。若不等，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

3. [Case03_Flag_Cleanup_Retirement_Bitmap_Check]：
   - 動作：在 SGM 觸發後，檢查 `sgs_scan_flagged_physical_vbNumb` 狀態。對於每個 VB，若其為 `current_revoke_vb_list` 中的一員，其標記應保持為 1 (若仍在 REVOKE 流程中) 或根據邏輯清零；若非 Revoke 且非觸發壞塊的 VB，其標記必須為 0。接著，針對在 Step 9 中透過 `issue_D017_to_create_SGM_fail` 注入壞塊的 VB (idx == fail_idx)，透過 Vendor Command `0x405E` 檢查該 VB 是否出現在 Retirement Bitmap 中 (`check_vb_in_BBT`)。同時檢查未注入壞塊的 VB 是否錯誤地出現在 Retirement Bitmap 中。
   - 預期結果：
     - **標記清理**：非 Revoke 且非壞塊的 VB，其 `sgs_scan_flagged_physical_vbNumb` 必須為 `0`。
     - **壞塊退休**：若 `is_retirement_case == True` (即注入了 D017 壞塊)，則 `check_vb_in_BBT` 必須返回 `True` (表示 VB 已進入 Retirement Bitmap)。
     - **正常區塊**：若 `is_retirement_case == False`，則 `check_vb_in_BBT` 必須返回 `False` (表示 VB 未進入 Retirement Bitmap)。若違反此規則，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。