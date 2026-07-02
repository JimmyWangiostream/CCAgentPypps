# Test Spec: Micron Health Report Retrieval & MConfig Initialization

## Verification Criterion (VC)
驗證韌體在初始化階段能否正確調用 `project_api.get_micron_health_report` 介面以獲取設備的健康狀態報告（Health Report），並確認該步驟能正確解析或初始化與 Micron 特定格式相關的 MConfig 數據結構。同時確認在 `ENG2_WA` 標誌為 True 的工程模式下，系統能正常進入該獲取流程而不因空實現的 `pre_process` 或 `step1` 中的邏輯斷點（`pass`）導致異常崩潰，確保健康報告獲取路徑的可用性。

## Test Case (TC) Checkpoints
1. [Health_Report_Get_Check]:
   - 動作：執行 `step1`，調用 `project_api.get_micron_health_report()` 函數，獲取返回的 `response` 和 `health_report` 兩個對象，並初始化局部變數 `x=0`。
   - 預期結果：函數執行成功，無異常拋出；`health_report` 應包含有效的 Micron 設備健康狀態數據（如介質錯誤計數、擦除計數等），`response` 應為正確的狀態碼或數據包，證明韌體與 Host 端或特定 API 層關於 Micron 健康報告的通訊協議實現正確。

2. [MConfig_Fetch_Check]:
   - 動作：雖然代碼中 `step1` 註釋提及 "get mconfig follow mConfig Format in FFU bin"，但實際代碼僅調用了 `get_micron_health_report`。驗證此步驟是否間接依賴或預設了 MConfig 的獲取邏輯已內置於 `get_micron_health_report` 中，或者確認當前實現僅聚焦於 Health Report 而暫未實現具體的 MConfig 解析（因代碼中 `x=0` 且無後續 MConfig 讀取動作）。
   - 預期結果：若 `get_micron_health_report` 內部封裝了 MConfig 讀取，則 `health_report` 中應包含 MConfig 相關字段；若未封裝，則此步驟僅驗證 Health Report 獲取路徑通暢，不驗證具體 MConfig 數據內容，符合當前代碼邏輯。

3. [Engineer_WA_Flag_Check]:
   - 動作：檢查全局變數 `ENG2_WA` 的值。
   - 預期結果：`ENG2_WA` 必須為 `True`，表明此測試用例運行在工程模式（Engineering Workaround）下，允許執行可能涉及特定硬體行為或暫不穩定的健康報告獲取操作，而不觸發標準生產模式的嚴格檢查。