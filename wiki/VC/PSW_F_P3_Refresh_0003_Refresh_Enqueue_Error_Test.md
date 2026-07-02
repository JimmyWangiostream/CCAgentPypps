# Test Spec: UFS Vendor Command C087/C088 Invalid Enqueue & Boundary Condition Test

## Verification Criterion (VC)
驗證 UFS 韌體在處理 Vendor Command C088 (Refresh Control) 與 C087 (VB Booking) 時的邊界條件與錯誤處理機制：
1. **C088 狀態機驗證**：確認在「停止 Refresh 執行但允許入隊」(StopRefresh/RefreshCanStillBeEnqueue) 模式下，系統能正確接受後續的 C087 入隊請求，且不會因 Refresh 引擎暫停而拒絕合法的 Booking 請求。
2. **C087 非法參數注入驗證**：針對 C087 命令的多種非法輸入情境（包括：VB Type 與實際 Block 類型不匹配、單一命令超過最大入隊數量限制、跨命令累積超過限制、以及注入不存在的 VB ID），驗證控制器是否嚴格執行參數檢查。
3. **錯誤響應碼驗證**：確認所有非法入隊嘗試均返回標準的 SCSI 錯誤鏈：`UPIUResponse.TARGET_FAILURE`、`ScsiStatus.CHECK_CONDITION`、`SenseKey.ILLEGAL_REQUEST`，且 Sense Data 中的 ASC/ASCQ 必須精確為 `0x1A/0x00` (Invalid Field in CDB)，代表韌體正確識別了無效的 CDB 欄位並拒絕執行。

## Test Case (TC) Checkpoints
1. [C088_StopRefresh_AllowEnqueue_Check]：
   - 動作：透過 `project_api.issue_C088_to_start_or_stop_refresh` 發送參數 `VUC088Paremeter.StopRefreshRefreshCanStillBeEnqueue` 以暫停 Refresh 引擎執行，隨後發送 `VUC088Paremeter.EnableEnqueueInRefreshBQ` 確保入隊緩衝區仍處於啟用狀態。
   - 預期結果：Refresh 引擎進入暫停狀態，但 Booking Queue 保持開放，允許後續 C087 命令將 VB 加入隊列而不被拒絕。

2. [C087_TypeMismatch_TableVB_UsedBlk_Check]：
   - 動作：從 `USED_BLK_POOL_TLC` 獲取 VB 列表，透過 `enqueu_error_case` 發送 C087 命令，將 `VB_type` 設定為 `TableVB`，但實際推送的是已使用的 TLC 資料區塊。
   - 預期結果：返回 `TARGET_FAILURE`，`CHECK_CONDITION`，`ILLEGAL_REQUEST`，ASC=`0x1A`，ASCQ=`0x00`。驗證韌體拒絕將非 Table 類型的區塊標記為 TableVB 進行 Refresh 預訂。

3. [C087_TypeMismatch_HostVB_TableVB_Check]：
   - 動作：從 `LIST_BLK` (通常為 HostVB 或系統保留區) 獲取 VB 列表，透過 `enqueu_error_case` 發送 C087 命令，將 `VB_type` 設定為 `HostVB`，但實際推送的區塊類型與之不符（或反之，視具體實現邏輯，此處為推入 HostVB 類型但實際區塊屬性衝突）。
   - 預期結果：返回 `TARGET_FAILURE`，`CHECK_CONDITION`，`ILLEGAL_REQUEST`，ASC=`0x1A`，ASCQ=`0x00`。驗證韌體拒絕類型不匹配的 VB 預訂請求。

4. [C087_TypeMismatch_HostVB_FreeBlk_Check]：
   - 動作：從 `FREE_BLK_QUEUE_EM1` 獲取空閒區塊列表，透過 `enqueu_error_case` 發送 C087 命令，將 `VB_type` 設定為 `HostVB`，推送空閒區塊。
   - 預期結果：返回 `TARGET_FAILURE`，`CHECK_CONDITION`，`ILLEGAL_REQUEST`，ASC=`0x1A`，ASCQ=`0x00`。驗證韌體拒絕將空閒區塊標記為 HostVB 進行 Refresh 預訂。

5. [C087_TypeMismatch_TableVB_FreeBlk_Check]：
   - 動作：從 `FREE_BLK_QUEUE_TLC` 獲取空閒區塊列表，透過 `enqueu_error_case` 發送 C087 命令，將 `VB_type` 設定為 `TableVB`，推送空閒區塊。
   - 預期結果：返回 `TARGET_FAILURE`，`CHECK_CONDITION`，`ILLEGAL_REQUEST`，ASC=`0x1A`，ASCQ=`0x00`。驗證韌體拒絕將空閒區塊標記為 TableVB 進行 Refresh 預訂。

6. [C087_SingleCmd_OverLimit_Check]：
   - 動作：構建一個包含 `vb_in_Q_limit` (10) + 1 個 VB 的列表，透過 `enqueu_error_case` 在單一 C087 命令中嘗試將這些 VB 以 `HighPriority` 加入隊列。
   - 預期結果：返回 `TARGET_FAILURE`，`CHECK_CONDITION`，`ILLEGAL_REQUEST`，ASC=`0x1A`，ASCQ=`0x00`。驗證韌體嚴格限制單一命令中的最大入隊 VB 數量，超出限制即報錯。

7. [C087_MultiCmd_Accumulated_OverLimit_Check]：
   - 動作：分兩次發送 C087 命令。第一次推送 `vb_in_Q_limit` 個 VB，第二次推送 1 個 VB，總數超過限制。
   - 預期結果：第二次推送時返回 `TARGET_FAILURE`，`CHECK_CONDITION`，`ILLEGAL_REQUEST`，ASC=`0x1A`，ASCQ=`0x00`。驗證韌體在跨命令情境下仍能正確追蹤累計入隊數量並拒絕超限請求。

8. [C087_MultiPriority_Accumulated_OverLimit_Check]：
   - 動作：透過 `get_HP_MP_LP_list` 獲取多個優先級 (HP/MP/LP) 的 VB 列表，總數超過 `vb_in_Q_limit`，並透過 `enqueu_error_case` 依次推送。
   - 預期結果：當累計數量超過限制時，返回 `TARGET_FAILURE`，`CHECK_CONDITION`，`ILLEGAL_REQUEST`，ASC=`0x1A`，ASCQ=`0x00`。驗證韌體在多優先級混合入隊時，依然正確執行總量限制檢查。

9. [C087_NonExistent_VB_Check]：
   - 動作：構建包含不存在 VB ID (`0xFFFF`) 的列表，透過 `enqueu_error_case` 發送 C087 命令嘗試預訂。
   - 預期結果：返回 `TARGET_FAILURE`，`CHECK_CONDITION`，`ILLEGAL_REQUEST`，ASC=`0x1A`，ASCQ=`0x00`。驗證韌體在預訂前會驗證 VB ID 的有效性，拒絕無效 ID 的請求。