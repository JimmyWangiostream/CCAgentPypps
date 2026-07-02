# Test Spec: UFS REH (Read Error Handling) & Sticky Read Verification with Bit Flip Injection

## Verification Criterion (VC)
驗證 UFS 韌體在 SLC 區塊遭遇特定數量比特翻轉（UECC 錯誤）時，Read Error Handling (REH) 機制能否正確識別錯誤並執行對應的讀取恢復步驟（Read Last Table 切換），同時驗證 Error Recovery Statistics (ERS) 計數器的遞增行為：
1. **Sticky Read 配置驗證**：確認透過 Vendor Command (VUC) 4066 強制將特定 Die/Page Type 的 Read Last Table 設為 Sticky Read 後，後續讀取能正確應用該策略。
2. **REH 步驟觸發驗證**：針對 Normal LUN (LUN 0) 與 Enhanced 1 LUN (LUN 1) 分別注入 150 個比特錯誤，透過 VUC 40D14 設定不同的 REH Big/Small Step，並讀取 VUC 40F9 返回的 `rr_number`，確認韌體是否正確報告了對應的 Big/Small Step 索引及非零的錯誤位元數。
3. **ERS 統計驗證**：比較注入錯誤前後的 ERS 值，確認在觸發 REH 恢復後，對應 Step 的 ERS 計數器數值嚴格大於注入前的備份值，證明錯誤已被統計且恢復機制已執行。
4. **PSA 狀態中斷驗證**：在 Normal LUN 測試結束後，透過寫入 Attribute PSA_STATE 為 OFF 來中斷 PSA (Pre-Soldering Authentication) 流程，確認韌體內部狀態能正確響應此中斷指令。

## Test Case (TC) Checkpoints

1. [LUN_Config_and_Sticky_Read_Setup]：
   - 動作：
     1. 透過 `push_write_config` 配置 LUN 0 為 `MemoryType.NORMAL`，LUN 1 為 `MemoryType.ENHANCED_1`，並啟用這兩個 LUN。
     2. 執行 `issue_C088_to_start_or_stop_refresh` 參數設為 `StopRefreshRefreshCanStillBeEnqueue` 以停止背景 Refresh 但允許入隊。
     3. 初始化 `read_last_ref_table` 並透過 `set_read_last_table` 寫入 Flash Setting。
     4. 針對所有 Die 與 Page Type，隨機選擇 ARC (Adaptive Read Compensation) 值，執行 `issue_4066_force_current_read_last_as_sticky_read` 將 Read Last Table 1 設為 Sticky Read。
     5. 針對 LUN 0 與 LUN 1 分別執行 `pre_condition_flow`：LUN 1 寫入 1 VB 資料；LUN 0 設定 PSA_DATA_SIZE，執行 Unmap，將 PSA_STATE 設為 `PRE_SOLDERING`，再寫入 1 VB 資料。
     6. 透過 `issue_D014_to_set_nand_temperature` 隨機設定 NAND 溫度（-37 至 125 度）並啟用。
     7. 執行 `issue_40BA_to_get_error_recovery_statistics` 取得初始 ERS 備份值 `bk_ers`。
   - 預期結果：LUN 配置成功；Sticky Read 設定返回 `STICKY_READ_STATUS.SUCCESS`；LUN 0 進入 PSA Pre-Soldering 狀態並寫入資料；LUN 1 寫入資料完成；ERS 備份值 `bk_ers` 成功讀取。

2. [REH_Step_Trigger_Verification_LUN0_LUN1]：
   - 動作：
     1. 針對 LUN 0 (PSA) 與 LUN 1 (EM1) 分別執行以下循環：
        a. 寫入 1 VB (4KB * VB Size) 資料至 LBA 0。
        b. 隨機選取 LBA，透過 `issue_4051_to_get_physical_address` 轉換為 PBA (Die, Plane, Block, Page)。
        c. 在該 Page 注入 150 個比特錯誤（透過 `flipbit_on_SLC_single_page`：讀取 Raw Data -> 翻轉 150 bits -> Erase Block -> 寫回 Modified Raw Data）。
        d. 透過 `issue_D014_to_set_read_recovery_module` 設定特定的 REH Big Step (`b`) 與 Small Step (`s`)，其中 `b` 範圍 0-8，`s` 由 `iter_reh_steps` 迭代產生，`isPSA` 根據 LUN 設定 (0 或 1)。
        e. 執行 Host Read 4KB 從該 LBA。
        f. 執行 `issue_40F9_to_get_error_bit_numbers` 讀取 REH 恢復記錄，獲取 `rr_number` 結構。
        g. 執行 `issue_40BA_to_get_error_recovery_statistics` 讀取當前 ERS。
        h. 計算當前 ERS 中對應 Step (`b`, `s`, `isSLC`, `isPSA`) 的值 `val`，並與備份值 `org_val` 比較。
     2. 若 LUN 為 LUN 0，在循環結束後執行 `api.write_attribute(idn=api.AttributeIDN.PSA_STATE, val=api.PSAState.OFF)` 中斷 PSA。
   - 預期結果：
     - **40F9 檢查**：返回的 `rr_number` 結構中，`bigStep.value` 必須等於設定的 `b`，`smallStep.value` 必須等於設定的 `s`，且 `maxErrorBits.value` 必須大於 0。若不符，拋出 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`。
     - **ERS 檢查**：對於每個有效的 REH Step 記錄，當前 ERS 值 `val` 必須嚴格大於備份值 `org_val` (`val > org_val`)。若 `val <= org_val`，記錄錯誤訊息並最終拋出 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`。

3. [Post_Test_Cleanup_and_Verification]：
   - 動作：
     1. 執行 `issue_D014_to_set_nand_temperature` 關閉溫度設定 (`isEnable=0`)。
     2. 執行 `issue_C088_to_start_or_stop_refresh` 參數設為 `StartRefresh` 恢復背景 Refresh。
     3. 檢查 `error_ERS_Message` 列表是否為空。
   - 預期結果：若 `error_ERS_Message` 非空，記錄所有錯誤訊息並拋出 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`；若為空，測試通過，代表所有 REH 步驟均正確觸發且 ERS 計數器正確遞增。