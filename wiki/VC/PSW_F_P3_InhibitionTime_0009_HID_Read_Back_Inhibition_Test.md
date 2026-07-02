# Test Spec: UFS Inhibition Manager Lock State Transition & GC Trigger Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr`（抑制管理器）的狀態機邏輯與垃圾回收（GC）觸發條件：
1. **初始鎖定狀態驗證**：確認在系統初始化完成後，`gInhibitMgr.lock` 標誌位必須嚴格為 `1`，代表抑制機制處於激活鎖定狀態，防止非必要的背景任務干擾。
2. **電源循環與重置兼容性**：驗證在 `HW_RESET` 情境下（無論是否包含 Power Down），韌體能否正確重新初始化並恢復 `gInhibitMgr.lock = 1` 的預期狀態。
3. **抑制時間到期解鎖驗證**：確認經過硬體設定的 `INHIBITION_TIME` 秒數後，`gInhibitMgr.lock` 必須自動切換為 `0`，代表抑制解除，允許系統進入正常操作模式。
4. **GC 觸發行為驗證**：在鎖定狀態（Flow 5）與解鎖狀態（Flow 9）分別執行 HID 指令並讀取目標 GC 狀態，驗證韌體是否根據抑制狀態正確觸發或延遲 GC 流程（註：具體 GC 觸發邏輯需對照 FG 代碼實現，此腳本主要驗證狀態轉換後的行為差異）。

## Test Case (TC) Checkpoints
1. [Case01_Init_Lock_State_Check]：
   - 動作：執行 `pre_process`（空操作），進入 `step1`。首先透過 `read_fw_value('gInhibitMgr.lock')` 讀取韌體內部變數 `gInhibitMgr.lock` 的初始值並存入 `inhibination_enable`。接著呼叫 `get_hwsetting_inhibition_time()` 讀取硬體設定中的 `INHIBITION_TIME` 欄位數值，並備份至 `backup_inhibition_time_sec`。隨後執行 `power_cycle()`，該函數隨機選擇是否執行 Power Down 的 `HW_RESET` 重置流程，並進入 Vendor Mode。重置完成後，再次讀取 `gInhibitMgr.lock` 的值。
   - 預期結果：在 `power_cycle` 完成後，讀取的 `gInhibitMgr.lock` 數值必須嚴格等於 `1`。若不等於 1，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。此結果驗證了無論是否進行 Power Down，韌體在初始化階段均正確將抑制管理器置於鎖定狀態。

2. [Case02_Inhibition_Time_Readback_Check]：
   - 動作：在確認鎖定狀態為 1 後，記錄當前讀取的 `INHIBITION_TIME` 硬體設定值（單位為秒）。此步驟主要用於確保後續的 `time.sleep` 延遲時間與硬體定義的抑制週期完全一致，為解鎖檢查做準備。
   - 預期結果：`self.inhibition_time_sec` 必須為有效的整數值，且該值將作為後續延遲計時的基準。此步驟確保測試環境的硬體設定與測試腳本的行為同步。

3. [Case03_GC_Trigger_During_Lock_Check]：
   - 動作：在 `gInhibitMgr.lock` 仍為 `1` 的狀態下，執行 Flow 4 所述的 "HID + Read back target GC" 操作。這通常涉及發送 HID（Host Initiated Data）指令並查詢目標 GC 的狀態或觸發標誌。
   - 預期結果：根據韌體邏輯，在抑制鎖定期間，GC 觸發應被延遲或抑制。具體預期需對照 FG 代碼，但腳本邏輯暗示此步驟為基準測試，用於與解鎖後的行為進行對比。若此步驟失敗，則代表韌體在鎖定狀態下未能正確處理 HID/GC 請求。

4. [Case04_Inhibition_Expire_Unlock_Check]：
   - 動作：執行 `time.sleep(self.inhibition_time_sec)`，等待硬體設定的抑制時間到期。等待結束後，連續兩次讀取 `gInhibitMgr.lock` 的值（間隔 0.01 秒以確保讀取穩定性）。
   - 預期結果：兩次讀取的 `gInhibitMgr.lock` 數值均必須嚴格等於 `0`。若任一讀取值不等於 0，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此結果驗證了抑制管理器在經過預設時間後，能正確自動解除鎖定狀態。

5. [Case05_GC_Trigger_After_Unlock_Check]：
   - 動作：在確認 `gInhibitMgr.lock` 已變為 `0` 後，再次執行 Flow 8 所述的 "HID + Read back target GC" 操作。
   - 預期結果：與 Case03 相比，此時系統應允許 GC 觸發或正常處理 HID 請求。Flow 9 檢查 "check if gc trigger" 應通過，代表在抑制解除後，韌體正確響應了 GC 觸發條件。若 GC 未觸發，則判定為測試失敗，代表抑制解除機制或 GC 調度器存在缺陷。