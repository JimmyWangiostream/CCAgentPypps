# Test Spec: UFS Inhibition Manager Lock State & GC Trigger Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr` 機制在硬體重置（HW_RESET）與電源循環（Power Cycle）後的狀態恢復邏輯，以及抑制時間（Inhibition Time）結束後垃圾回收（GC）觸發的正確性：
1. **初始狀態檢查**：確認韌體初始化後，`gInhibitMgr.lock` 標誌為 1（鎖定狀態），防止非必要的背景操作。
2. **重置後鎖定維持**：執行 HW_RESET（含/不含 Power Down）後，確認 `gInhibitMgr.lock` 仍保持為 1，代表韌體在啟動初期正確維持抑制狀態。
3. **抑制期後解鎖**：等待配置的 `INHIBITION_TIME` 秒數後，確認 `gInhibitMgr.lock` 變更為 0（解鎖狀態），代表抑制機制已過期。
4. **GC 觸發驗證**：在解鎖狀態下，確認系統成功觸發 GC 流程（透過 MS/BF/RD scan 結果或內部狀態標記），驗證背景維護任務在抑制解除後能正常執行。

## Test Case (TC) Checkpoints
1. [Case01_Initial_Lock_Check]：
   - 動作：在 `pre_process` 完成後進入 `step1`，透過 `read_fw_value('gInhibitMgr.lock')` 讀取韌體內部變數 `gInhibitMgr.lock` 的初始值。
   - 預期結果：讀取到的整數值必須等於 1。若不等於 1，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，代表韌體初始化時未正確設定抑制鎖定標誌。

2. [Case02_PowerCycle_Lock_Maintenance_Check]：
   - 動作：執行 `power_cycle()` 函數，該函數隨機選擇兩種重置模式之一：
     a) `Dcmd5ResetType.HW_RESET` 且 `powerdown = False`（僅硬體重置，不斷電）。
     b) `Dcmd5ResetType.HW_RESET` 且 `powerdown = True`（硬體重置並斷電重啟）。
     重置完成並進入 Unit Ready 狀態後，再次透過 `read_fw_value('gInhibitMgr.lock')` 讀取該變數值。
   - 預期結果：讀取到的整數值必須等於 1。這驗證了無論是否經歷完整電源循環，韌體在啟動後的初始階段都必須維持 `gInhibitMgr.lock = 1` 的狀態，確保系統穩定性。

3. [Case03_Inhibition_Time_Expiry_Unlock_Check]：
   - 動作：透過 `get_hwsetting_inhibition_time()` 讀取硬體設定中的 `INHIBITION_TIME` 欄位值（單位為秒），並使用 `time.sleep()` 等待該時間長度。等待結束後，連續兩次讀取 `gInhibitMgr.lock` 的值（中間間隔 0.01 秒以確保狀態穩定）。
   - 預期結果：兩次讀取到的整數值均必須等於 0。若值不等於 0，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。這驗證了抑制計時器在經過指定時間後正確觸發解鎖機制，允許背景任務運行。

4. [Case04_GC_Trigger_Verification]：
   - 動作：在 `gInhibitMgr.lock` 變為 0 之後，執行 `{MS / BF / RD scan}` 流程（註：具體實現依賴於 `need feature owner describe details` 的內部邏輯，通常涉及 Medium Scan, Bad Flash Scan, Read Disturb Scan 等背景掃描任務）。
   - 預期結果：系統必須成功觸發 GC（Garbage Collection）或相關背景維護流程。若掃描結果顯示未觸發 GC，則判定為失敗（`determine fail`）。這驗證了抑制解除後，UFS 控制器的背景維護機制能正確響應並執行垃圾回收，以維持儲存效能與壽命。