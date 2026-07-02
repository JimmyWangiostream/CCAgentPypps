# Test Spec: UFS Inhibition Manager Lock State Transition & BG Task Trigger Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr.lock` 狀態機與硬體 `INHIBITION_TIME` 設定及背景任務（BG Task）觸發時機的嚴格關聯性：
1. **初始狀態驗證**：確認系統上電初始化後，若硬體設定為預設值（非零），`gInhibitMgr.lock` 必須為 `1`（鎖定狀態），且此期間進入/退出 L1/L2 低功耗狀態時，**不得**觸發 BG Task（如 PSA refresh, Read scan UECC 等）。
2. **解鎖機制驗證**：確認在 `gInhibitMgr.lock == 1` 的狀態下，經過指定的 `INHIBITION_TIME` 秒數閒置後，`gInhibitMgr.lock` 必須自動轉變為 `0`（解鎖狀態），且此後進入/退出 L1/L2 時，**必須**觸發 BG Task。
3. **動態參數驗證**：確認透過 `HwSettingField.INHIBITION_TIME` 將抑制時間設為 `0` 並重啟後，系統應立即處於解鎖狀態（`lock == 0`）且允許 BG Task 觸發；恢復原始時間設定並重啟後，系統應重新回到鎖定狀態（`lock == 1`）並遵循時間計時邏輯。

## Test Case (TC) Checkpoints

1. **[Case01_Initial_Lock_State_Check]**：
   - 動作：執行 `pre_process`（空操作），讀取韌體變數 `gInhibitMgr.lock` 並記錄為 `inhibination_enable`。接著執行 `power_cycle()`（隨機選擇 HW_RESET 帶/不帶 Power Down），進入 Unit Ready 狀態並進入 Vendor Mode。再次讀取 `gInhibitMgr.lock`。
   - 預期結果：讀取的 `gInhibitMgr.lock` 數值必須等於 `1`。若不等於 1，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這代表在硬體抑制時間未過或預設為鎖定狀態時，韌體正確維持了 Inhibit Manager 的鎖定狀態。

2. **[Case02_BG_Task_Blocking_Verification]**：
   - 動作：記錄當前 BG Task 事件狀態（註：腳本中註記需 Feature Owner 描述細節，但邏輯上此步驟旨在確認當前鎖定狀態下無 BG 活動）。接著執行 `Enter L1/L2` 然後 `Exit L1/L2` 的電源狀態轉換操作。檢查 BG Task 事件觸發標誌。
   - 預期結果：BG Task 事件（如 PSA refresh/other refresh/read scan UECC）**不得**被觸發。若觸發，則判定為失敗。這驗證了在 `gInhibitMgr.lock == 1` 期間，系統禁止背景維護任務執行。

3. **[Case03_Inhibition_Time_Wait_And_Unlock]**：
   - 動作：執行 `time.sleep(self.inhibition_time_sec)` 等待硬體設定的抑制時間過去。隨後連續兩次讀取 `gInhibitMgr.lock` 以確保狀態穩定。
   - 預期結果：讀取的 `gInhibitMgr.lock` 數值必須等於 `0`。若不等於 0，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這代表經過指定的抑制時間後，Inhibit Manager 正確解除了鎖定狀態。

4. **[Case04_BG_Task_Enabling_Verification]**：
   - 動作：記錄當前 BG Task 事件狀態。接著執行 `Enter L1/L2` 然後 `Exit L1/L2` 的電源狀態轉換操作。檢查 BG Task 事件觸發標誌。
   - 預期結果：BG Task 事件（如 PSA refresh/other refresh/read scan UECC）**必須**被觸發。若未觸發，則判定為失敗。這驗證了在 `gInhibitMgr.lock == 0` 期間，系統允許並觸發背景維護任務。

5. **[Case05_Zero_Inhibition_Time_Unlock]**：
   - 動作：透過 `api.HwSettingField.INHIBITION_TIME` 將硬體抑制時間設定為 `0` 並寫入裝置。執行 `power_cycle()` 重啟系統。進入 Vendor Mode 後，讀取 `gInhibitMgr.lock`。
   - 預期結果：讀取的 `gInhibitMgr.lock` 數值必須等於 `0`。若不等於 0，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這代表當抑制時間設為 0 時，系統上電後不應進入鎖定狀態，應立即允許 BG Task。

6. **[Case06_Original_Time_Restore_Lock]**：
   - 動作：將 `INHIBITION_TIME` 恢復為備份的原始值 `self.backup_inhibition_time_sec` 並寫入裝置。執行 `power_cycle()` 重啟系統。進入 Vendor Mode 後，讀取 `gInhibitMgr.lock`。
   - 預期結果：讀取的 `gInhibitMgr.lock` 數值必須等於 `1`。若不等於 1，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這代表恢復原始設定後，系統重新進入鎖定狀態。

7. **[Case07_Final_Time_Wait_Verification]**：
   - 動作：執行 `time.sleep(self.inhibition_time_sec)` 等待恢復後的抑制時間過去。隨後連續兩次讀取 `gInhibitMgr.lock`。
   - 預期結果：讀取的 `gInhibitMgr.lock` 數值必須等於 `0`。若不等於 0，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這代表在恢復原始設定並等待足夠時間後，系統正確從鎖定狀態轉變為解鎖狀態，完成整個狀態機循環驗證。