# Test Spec: Null Pattern Timeout Verification

## Verification Criterion (VC)
驗證測試框架在無實際硬體交互情境下的基礎時序控制與超時機制：確認 `sw_timeout` API 在指定秒數（10秒）後能正確觸發邏輯中斷，並驗證日誌系統能準確記錄輪詢狀態與超時事件，確保測試腳本不會因無限循環而掛起。

## Test Case (TC) Checkpoints
1. [Timeout_Trigger_Check]：
   - 動作：初始化時間戳記 `t` 為當前系統時間，進入無限 `while True` 循環。在每次循環中執行 `time.sleep(1)` 暫停 1 秒，並透過 `logger.info` 輸出 'polling...' 訊息。持續執行此循環，直到 `api.sw_timeout(t, sec=10)` 函數返回 True（即經過時間超過 10 秒），隨後執行 `logger.info('timeout.')` 並使用 `break` 跳出循環。
   - 預期結果：測試腳本必須在啟動後約 10 秒內結束執行，不會進入死鎖或無限等待狀態；日誌中應包含連續約 10 條 'polling...' 記錄，最後一條為 'timeout.'，證明軟體超時計時器運作正常且邏輯分支正確。