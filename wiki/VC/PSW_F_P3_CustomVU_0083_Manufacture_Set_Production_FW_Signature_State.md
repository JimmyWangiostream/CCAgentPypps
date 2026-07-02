# Test Spec: UFS Vendor Command Illegal Access & State Dependency Validation

## Verification Criterion (VC)
驗證 UFS 裝置在特定硬體狀態（Device State != 0，即非 Idle/Ready 狀態）下，對非法 Vendor Command (VC) 的錯誤處理機制：
1. **狀態依賴性檢查**：確認當 `issue_40E2` 返回的 Device State 不為 0 時，系統進入「禁用 VC」測試流程；若為 0，則僅獲取 VB 列表資訊而不執行後續 VC 測試。
2. **非法 VC 拒絕機制**：針對三類非法 VC 指令（No-Data, Data-In, Data-Out），驗證裝置是否正確拒絕執行並返回標準 SCSI Sense 錯誤。
3. **錯誤碼一致性**：確認所有非法 VC 請求均返回 `UPIUResponse.TARGET_FAILURE`、`ScsiStatus.CHECK_CONDITION` 以及 Sense Data 中的 `ASC (Additional Sense Code) == 0x24`（代表 "Logical Unit Not Supported" 或 "Invalid Field in CDB" 等具體非法指令錯誤），確保韌體不會因接收非法 Opcode 或 Function Code 而崩潰或產生未定義行為。

## Test Case (TC) Checkpoints
1. [State_Check_and_VU_Disable_Flow]：
   - 動作：執行 `project_api.issue_40E2_to_get_device_state()` 獲取當前裝置狀態 (`device_state`) 及剩餘狀態變更次數。
     - 分支 A：若 `device_state == 0`，執行 `project_api.issue_406D_get_VB_list_info()` 獲取 VB 列表資訊並結束測試。
     - 分支 B：若 `device_state != 0`，記錄日誌 "Start Test for disable vu"，並呼叫 `issue_vu_illegal_test()` 執行非法 VC 測試。
   - 預期結果：
     - 當 `device_state == 0` 時，測試應順利獲取 VB 資訊且無錯誤拋出。
     - 當 `device_state != 0` 時，測試應進入 `issue_vu_illegal_test` 流程，並對後續列出的所有 No-Data、Data-In、Data-Out 類型的非法 VC 進行驗證。

2. [No_Data_Illegal_VU_Rejection]：
   - 動作：針對 `no_data_list` 中的每一個 Opcode（如 "D00D", "D00E" 等共 41 個指令），執行 `issue_no_data_vu_check_error`。具體行為為：構建 `micron_vendor_cmd`，設定 `b0_opcode` 為對應值，`b1_func` 為 `0xD0`，`d8_split_pkg_index` 為 0，`d4_random_stamp` 為隨機值。透過 `send_data_in_vcmd` 發送請求（`keep_error=True`），並檢查回應。
   - 預期結果：對於列表中的每一個指令，回應必須滿足以下條件：
     - `response.upiu.b6_response` 等於 `api.UPIUResponse.TARGET_FAILURE`。
     - `response.upiu.b7_status` 等於 `api.ScsiStatus.CHECK_CONDITION`。
     - `response.b32_sense_data.b12_asc` 等於 `0x24`。
     - 若任一指令未返回上述組合，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。

3. [Data_In_Illegal_VU_Rejection]：
   - 動作：針對 `data_in_list` 中的每一個 Opcode（如 "400F", "4010" 等共 64 個指令），執行 `issue_data_in_vu_check_error`。具體行為為：構建 `micron_vendor_cmd`，設定 `b0_opcode` 為對應值，`b1_func` 為 `0x40`，`w2_transfer_length` 為 `0x1000`，`d4_random_stamp` 為隨機值。透過 `send_data_in_vcmd` 發送請求（`keep_error=True`），並檢查回應。
   - 預期結果：對於列表中的每一個指令，回應必須滿足以下條件：
     - `response.upiu.b6_response` 等於 `api.UPIUResponse.TARGET_FAILURE`。
     - `response.upiu.b7_status` 等於 `api.ScsiStatus.CHECK_CONDITION`。
     - `response.b32_sense_data.b12_asc` 等於 `0x24`。
     - 若任一指令未返回上述組合，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。

4. [Data_Out_Illegal_VU_Rejection]：
   - 動作：針對 `data_out_list` 中的每一個 Opcode（如 "C012", "C04A" 等共 26 個指令），執行 `issue_data_out_vu_check_error`。具體行為為：構建 `micron_vendor_cmd`，設定 `b0_opcode` 為對應值，`b1_func` 為 `0xC0`，`w2_transfer_length` 為 4096，`d4_random_stamp` 為隨機值。準備 4096 字節的 payload，透過 `send_data_out_vcmd` 發送請求（`keep_error=True`），並檢查回應。
   - 預期結果：對於列表中的每一個指令，回應必須滿足以下條件：
     - `response.upiu.b6_response` 等於 `api.UPIUResponse.TARGET_FAILURE`。
     - `response.upiu.b7_status` 等於 `api.ScsiStatus.CHECK_CONDITION`。
     - `response.b32_sense_data.b12_asc` 等於 `0x24`。
     - 若任一指令未返回上述組合，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。