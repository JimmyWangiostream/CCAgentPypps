# Test Spec: UFS Inhibition Manager Lock State Transition & GC Suppression Test

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr` 模組在硬體重置（HW_RESET）與電源循環（Power Cycle）後的狀態機行為，以及 Inhibition Time 設定對背景垃圾回收（GC）觸發的抑制機制：
1. **初始鎖定狀態驗證**：確認在系統初始化完成後，`gInhibitMgr.lock` 標誌必須為 `1`，代表系統處於禁止觸發 GC 的保護期內。
2. **電源循環後狀態保持**：執行 HW_RESET（含/不含 Power Down）後，韌體重新載入並初始化，`gInhibitMgr.lock` 必須重新恢復為 `1`，確保每次冷啟動或熱重置後保護機制均正確初始化。
3. **抑制期結束狀態轉換**：在 `gInhibitMgr.lock` 為 `1` 的狀態下，等待由 HwSetting 讀取的 `INHIBITION_TIME` 時長，隨後驗證 `gInhibitMgr.lock` 必須轉變為 `0`，代表保護期結束，系統允許觸發背景任務。
4. **GC 觸發邏輯互斥驗證**：
   - 在 `lock = 1` 期間（Flow 5），即使觸發 Automatic PSA Refresh，GC **不得**被觸發（若觸發則判定為 Fail，因為應被抑制）。
   - 在 `lock = 0` 期間（Flow 9），經過相同的 Automatic PSA Refresh 後，GC **必須**被觸發（若未觸發則判定為 Fail，因為抑制已解除，GC 應正常運作）。

## Test Case (TC) Checkpoints
1. [Case01_Init_Lock_State_Check]：
   - 動作：執行 `pre_process`（空操作），進入 `step1`。讀取韌體內部變數 `gInhibitMgr.lock` 並儲存至 `inhibination_enable`。記錄當前硬體設定的 `INHIBITION_TIME` 為 `inhibition_time_sec`。
   - 預期結果：`inhibination_enable` 的值必須嚴格等於 `1`。若不等於 1，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，代表韌體初始化階段未正確設置 Inhibition Manager 的鎖定狀態。

2. [Case02_PowerCycle_Lock_State_Persistence_Check]：
   - 動作：執行 `power_cycle()` 函數。該函數隨機選擇兩種重置模式之一：
     - 模式 A：`Dcmd5ResetType.HW_RESET` 且 `powerdown = False`（熱重置）。
     - 模式 B：`Dcmd5ResetType.HW_RESET` 且 `powerdown = True`（冷重置/掉電重啟）。
     重置完成後，進入 Vendor Mode，並再次讀取 `gInhibitMgr.lock`。
   - 預期結果：無論選擇哪種重置模式，讀取到的 `gInhibitMgr.lock` 值必須為 `1`。這驗證了無論硬體重置類型為何，韌體在重新初始化時都會正確重置 Inhibition Manager 的狀態。

3. [Case03_Inhibition_Period_GC_Suppression_Check]：
   - 動作：在確認 `gInhibitMgr.lock == 1` 後，執行 "Automatic PSA Refresh" 並讀取目標 GC 狀態（Background Only）。隨後，程式碼記錄此為 Flow 5，並檢查 GC 是否觸發。
   - 預期結果：GC **不應**被觸發。根據程式碼邏輯 `check if gc trigger , if triggered determine fail`，如果在 `lock=1` 期間 GC 被觸發，測試將失敗。這驗證了 Inhibition 機制成功抑制了背景 GC 的執行。

4. [Case04_Inhibition_Time_Expiry_State_Transition_Check]：
   - 動作：執行 `time.sleep(self.inhibition_time_sec)`，等待由 `HwSettingField.INHIBITION_TIME` 定義的完整抑制時間。等待結束後，連續兩次讀取 `gInhibitMgr.lock`（中間間隔 0.01 秒以確保狀態穩定），並儲存至 `inhibination_enable`。
   - 預期結果：`inhibination_enable` 的值必須嚴格等於 `0`。若不等於 0，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。這驗證了經過預設的抑制時間後，Inhibition Manager 的鎖定標誌會正確釋放。

5. [Case05_Post_Inhibition_GC_Trigger_Check]：
   - 動作：在確認 `gInhibitMgr.lock == 0` 後，再次執行 "Automatic PSA Refresh" 並讀取目標 GC 狀態（Background Only）。隨後，程式碼記錄此為 Flow 9，並檢查 GC 是否觸發。
   - 預期結果：GC **必須**被觸發。根據程式碼邏輯 `check if gc trigger , if not triggered determine fail`，如果在 `lock=0` 期間 GC 未被觸發，測試將失敗。這驗證了抑制解除後，背景垃圾回收機制能正常響應 PSA Refresh 事件並啟動。