# Test Spec: UFS Inhibition Manager Lock State Transition Verification

## Verification Criterion (VC)
驗證 UFS 韌體中的 Inhibition Manager（抑制管理器）在硬體設定（HW Setting）的 `INHIBITION_TIME` 參數變更後，其內部鎖定狀態（`gInhibitMgr.lock`）的時序行為與邊界條件處理：
1. **邊界值 0 秒驗證**：確認當 `INHIBITION_TIME` 設為 0 時，韌體不會進入鎖定狀態（Lock=0），且無需等待即恢復正常。
2. **預設值與非零值驗證**：確認當 `INHIBITION_TIME` 設為預設值或特定非零值（如 180s, 255s 等）時，韌體在 Power Cycle 後會立即進入鎖定狀態（Lock=1），並在經過指定的秒數延遲後，鎖定狀態自動釋放變為 0。
3. **重置機制驗證**：確認測試過程中透過 `HW_RESET`（含/不含 Power Down）重置設備後，韌體能正確讀取新的 HW Setting 並初始化 Inhibition Manager 狀態。

## Test Case (TC) Checkpoints

1. **[TC01_Default_Inhibition_Time_Check]**：
   - 動作：
     1. 透過 `get_hwsetting_inhibition_time()` 讀取當前設備的預設 `INHIBITION_TIME` 值，並備份至 `backup_inhibition_time_sec`。
     2. 執行 `power_cycle()`（隨機選擇是否 Power Down 的 HW_RESET）。
     3. 進入 Vendor Mode 後，透過 `read_fw_value('gInhibitMgr.lock')` 讀取韌體內部變數 `gInhibitMgr.lock` 的值。
     4. 驗證初始狀態：若 `lock != 1`，則報錯。
     5. 執行 `time.sleep(self.inhibition_time_sec)` 等待預設時間。
     6. 再次讀取 `gInhibitMgr.lock`，並額外等待 0.01 秒後第三次讀取以確保狀態穩定。
     7. 驗證最終狀態：若 `lock != 0`，則報錯。
   - 預期結果：
     - Power Cycle 後立即讀取時，`gInhibitMgr.lock` 必須等於 **1**（代表 Inhibition 啟動，設備處於抑制狀態）。
     - 經過 `INHIBITION_TIME` 秒數延遲後，`gInhibitMgr.lock` 必須等於 **0**（代表抑制解除，設備恢復正常操作）。
     - 此步驟驗證韌體在預設設定下，Inhibition Timer 計時與狀態切換邏輯正確。

2. **[TC02_Zero_Sec_Inhibition_Check]**：
   - 動作：
     1. 透過 `hw_setting.set_local_val(api.HwSettingField.INHIBITION_TIME, 0)` 將抑制時間設定為 0 秒。
     2. 透過 `hw_setting.set_to_device()` 將設定寫入設備。
     3. 執行 `power_cycle()`（隨機選擇是否 Power Down 的 HW_RESET）。
     4. 進入 Vendor Mode 後，透過 `read_fw_value('gInhibitMgr.lock')` 讀取韌體內部變數 `gInhibitMgr.lock` 的值。
     5. 驗證狀態：若 `lock != 0`，則報錯。
   - 預期結果：
     - Power Cycle 後立即讀取時，`gInhibitMgr.lock` 必須等於 **0**。
     - 此步驟驗證當抑制時間為 0 時，韌體不會啟動 Inhibition 機制，設備無需等待即可立即進入可操作狀態。

3. **[TC03_Arbitrary_Inhibition_Time_Check]**：
   - 動作：
     1. 遍歷測試列表 `[180, 150, 90, 60, 30, 210, 240, 255, backup_inhibition_time_sec]` 中的每一個 `test_inhibition_time`。
     2. 對每個時間值執行 `set_inhibition_time_test`：
        - 設定 HW Setting 的 `INHIBITION_TIME` 為當前測試值。
        - 寫入設備並執行 `power_cycle()`。
        - 讀取並驗證初始 `gInhibitMgr.lock` 必須為 **1**。
        - 執行 `time.sleep(test_inhibition_time)` 等待指定秒數。
        - 讀取並驗證最終 `gInhibitMgr.lock` 必須為 **0**（包含中間的 0.01s 延遲檢查）。
   - 預期結果：
     - 對於列表中的每一個非零時間值，韌體必須在 Power Cycle 後立即將 `gInhibitMgr.lock` 設為 **1**。
     - 在經過精確對應的 `test_inhibition_time` 秒數後，`gInhibitMgr.lock` 必須準確切換為 **0**。
     - 此步驟驗證 Inhibition Manager 對不同時長參數的計時精度與狀態機轉換的魯棒性，涵蓋短時間（30s）與長時間（255s）情境。