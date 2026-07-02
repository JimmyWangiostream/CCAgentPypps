# Test Spec: UFS Inhibition Manager Lock State Transition & GC Trigger Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr.lock` 狀態機在硬體重置（HW_RESET）與電源循環（Power Cycle）後的正確性，以及 Inhibition Time 到期後是否正確解除鎖定並觸發垃圾回收（GC）機制：
1. **初始狀態驗證**：確認韌體初始化後 `gInhibitMgr.lock` 必須為 1（鎖定狀態），防止非預期操作。
2. **重置後狀態維持**：執行 HW_RESET（含/不含 Power Down）後，韌體重新初始化，`gInhibitMgr.lock` 必須恢復為 1，確保系統進入安全初始狀態。
3. **時序解鎖驗證**：在鎖定狀態下等待硬體設定的 `INHIBITION_TIME` 秒數後，`gInhibitMgr.lock` 必須自動變更為 0（解鎖狀態），代表 Inhibition 機制已過期。
4. **GC 觸發驗證**：在鎖定期間（Flow 5）與解鎖後（Flow 9）均需確認 GC 觸發狀態，驗證 Inhibition 機制對後台任務（如 GC）的調度影響是否符合設計預期（註：腳本中 Flow 5/9 的具體檢查邏輯被註釋，但根據 VC 推斷需驗證 GC 在特定條件下的行為）。

## Test Case (TC) Checkpoints
1. [Case01_Initial_Lock_State_Check]：
   - 動作：執行 `pre_process`（空操作），讀取韌體內部變數 `gInhibitMgr.lock` 的值並存入 `self.inhibination_enable`。
   - 預期結果：`self.inhibination_enable` 必須等於 1。若不等於 1，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，代表韌體初始化時 Inhibition Manager 未正確進入鎖定狀態。

2. [Case02_HW_Reset_Lock_Maintenance_Check]：
   - 動作：調用 `power_cycle()` 函數，該函數隨機選擇兩種重置模式之一：
     - 模式 A：`init_tester_to_unit_ready(resetmode=Dcmd5ResetType.HW_RESET, powerdown=False)`
     - 模式 B：`init_tester_to_unit_ready(resetmode=Dcmd5ResetType.HW_RESET, powerdown=True)`
     重置完成後，進入 Vendor Mode，再次讀取 `gInhibitMgr.lock` 的值。
   - 預期結果：無論選擇哪種重置模式，`gInhibitMgr.lock` 必須等於 1。這驗證了 HW_RESET 後韌體恢復機制會強制將 Inhibition Manager 置於鎖定狀態，確保系統穩定性。

3. [Case03_Inhibition_Time_Expiry_Unlock_Check]：
   - 動作：
     1. 讀取硬體設定中的 `INHIBITION_TIME` 欄位（透過 `api.HwSettingField.INHIBITION_TIME`），獲取等待時間 `self.inhibition_time_sec`。
     2. 執行 `time.sleep(self.inhibition_time_sec)` 等待該時長。
     3. 連續兩次讀取 `gInhibitMgr.lock` 的值（間隔 0.01 秒以確保狀態穩定）。
   - 預期結果：`gInhibitMgr.lock` 必須等於 0。若仍為 1，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。這驗證了 Inhibition 機制在經過設定的硬體時長後，會正確地自動解除鎖定，允許後續操作或後台任務進行。

4. [Case04_GC_Trigger_Verification]：
   - 動作：
     1. 在 Flow 5（鎖定狀態下）執行 BBM Scan 並檢查 GC 觸發狀態。
     2. 在 Flow 9（解鎖狀態下）執行 BBM Scan 並檢查 GC 觸發狀態。
     *(註：腳本中具體的 GC 檢查代碼被註釋為 "need feature owner describe details"，但根據測試邏輯，此步驟旨在驗證 Inhibition 狀態對 GC 的影響)*
   - 預期結果：
     - Flow 5：在 `gInhibitMgr.lock == 1` 時，GC 應被抑制或未觸發（具體行為取決於韌體設計，通常 Inhibition 期間會暫停非關鍵後台任務）。
     - Flow 9：在 `gInhibitMgr.lock == 0` 時，GC 應被允許觸發或正常運行。
     - 若 GC 未在預期狀態下觸發，則判定為 Fail。