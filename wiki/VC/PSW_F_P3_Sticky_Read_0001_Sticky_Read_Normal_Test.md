# Test Spec: UFS REH Sticky Read & Read Last Table Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Read Error Handling (REH) 模組的 Read Last Table 寫入/讀取一致性，以及 Sticky Read 機制在不同 LUN 類型（Normal/TLC, EM1/SLC, PSA）下的狀態切換邏輯：
1. **Read Last Table Integrity**：確認 Vendor Command `0xD014` 設定的 Read Last Offset 能透過 `0x4014` 精確讀回，且數值完全匹配。
2. **Sticky Read Activation**：確認 Vendor Command `0x4066` 強制將當前 Read Last 設為 Sticky Read 後，狀態寄存器正確回報 `STICKY_READ_ENTERED` 且 Offset 與設定值一致。
3. **Sticky Read Threshold Logic**：
   - **Normal/EM1 LUN**：確認當 ERS (Error Recovery Statistics) Dummy Read Value 的差異值 (`diff`) 小於 `mConfig.REH_ENTER_COUNT_STICKY_ON` 閾值時，Sticky Read 狀態維持為 `ENTERED`；若差異大於等於閾值，則狀態變更為 `NOT_ENTERED`。
   - **PSA LUN**：確認 PSA 情境下使用固定閾值 `1` 作為判斷標準（`diff >= 1` 則 `NOT_ENTERED`）。
4. **PSA State Interruption**：確認在 PSA LUN 測試結束後，透過寫入 `PSA_STATE` Attribute 為 `OFF`，能正確中斷 PSA 流程並驗證韌體內部狀態。

## Test Case (TC) Checkpoints

1. [ReadLastTable_Set_Get_Verify]：
   - 動作：針對指定 Die (CE)、Page Type 及 Table Index (`LAST_TABLE_1` 或 `LAST_TABLE_2`)，透過 `issue_D014_to_set_last_table_content` 寫入隨機生成的 Offset 值（範圍 -80 至 80，轉換為 Unsigned Byte）。隨後立即透過 `issue_4014_to_get_read_recovery_info_read_last` 讀回該 Table 內容。
   - 預期結果：讀回的 Offset 數值（`offset1`, `offset2`, `offset3`）必須與寫入的 Offset 數值完全相等。若不相等，觸發 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`，代表 Read Last Table 寫入機制失效。

2. [StickyRead_Force_Enter_Check]：
   - 動作：針對同一個 Die/Page/Table，透過 `issue_4066_force_current_read_last_as_sticky_read` 強制將當前 Read Last 設為 Sticky Read。隨後透過 `issue_4066_get_sticky_read_status_and_offset` 查詢狀態。
   - 預期結果：
     1. `result` 欄位必須為 `STICKY_READ_STATUS.SUCCESS`。
     2. `stickyReadStatus` 欄位必須為 `STICKY_READ_OUTPUT_STATUS.STICKY_READ_ENTERED`。
     3. 讀回的 Sticky Offset 必須與步驟 1 中設定的 Read Last Offset 完全一致。

3. [Normal_LUN_Sticky_Threshold_Verification]：
   - 動作：
     1. 獲取 `mConfig` 中的 `REH_ENTER_COUNT_STICKY_ON` 閾值（例如 428h 地址對應值）。
     2. 記錄當前 ERS Dummy Read Value (`val_bk`)。
     3. 執行 25 次 Host Read 10 指令（LBA 隨機選定，QD=1）。
     4. 再次讀取 ERS Dummy Read Value (`val`)，計算差異 `diff = val - val_bk`。
     5. 根據邏輯判斷預期狀態：若 `diff < sticky_threshold`，預期狀態為 `STICKY_READ_ENTERED`；否則為 `STICKY_READ_NOT_ENTERED`。
     6. 透過 `issue_4066_get_sticky_read_status_and_offset` 讀取實際 Sticky Read 狀態。
   - 預期結果：實際讀回的 `stickyReadStatus` 必須與步驟 5 計算出的預期狀態完全匹配。此驗證確保韌體在 Normal (TLC) 和 EM1 (SLC) LUN 上，能正確根據 ERS 數據變化量與 mConfig 閾值來決定 Sticky Read 是否失效。

4. [PSA_LUN_Sticky_Threshold_Verification]：
   - 動作：
     1. 針對 PSA LUN (LUN 3)，執行與步驟 3 相同的 25 次 Host Read 流程。
     2. 計算 ERS Dummy Read Value 差異 `diff`。
     3. 根據 PSA 特殊邏輯判斷預期狀態：若 `diff >= 1`，預期狀態為 `STICKY_READ_NOT_ENTERED`；若 `diff < 1`（即 diff=0），預期狀態為 `STICKY_READ_ENTERED`。
     4. 讀取實際 Sticky Read 狀態。
   - 預期結果：實際狀態必須與步驟 3 的 PSA 邏輯判斷結果一致。此驗證確保 PSA 情境下使用固定閾值 1 進行 Sticky Read 狀態切換。

5. [PSA_State_Interruption_Check]：
   - 動作：在 PSA LUN 測試循環結束後，透過 `api.write_attribute` 將 `PSA_STATE` Attribute 寫入 `api.PSAState.OFF`。隨後呼叫 `set_LUN_configuration` 重新配置 LUN。
   - 預期結果：韌體應正確處理 PSA 狀態關閉指令，中斷 PSA 流程。雖然腳本未直接斷言內部狀態碼，但此步驟為驗證 PSA 狀態機在外部控制下的響應行為，確保後續測試不會受殘留 PSA 狀態干擾。