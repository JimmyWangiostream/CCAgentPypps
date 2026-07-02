# Test Spec: D0FB Firmware State Persistence & ISR Timeout Verification

## Verification Criterion (VC)
驗證韌體在 RAM 中設定的 `POWER_ON_WB_EN` (Power-On Write Buffer Enable) 狀態機行為：Case 01 確認當韌體狀態設為 1 (Enable) 時，執行 `RESET_N` (非硬體重啟) 後，該標誌位元應保持為 1，證明非揮發性狀態在軟重置下未丟失；Case 02 確認當韌體狀態設為 0 (Disable) 時，執行 `RESET_N` 後，該標誌位元應變更為 0，驗證狀態同步機制；Case 03 為關鍵時序驗證，確認當韌體狀態設為 2 (Trigger ISR/Timeout) 時，後續的 `ReadFlag` 指令會觸發韌體內部 ISR 處理並導致命令超時 (TIMEOUT_EXCEPTIONS)，以此驗證韌體在特定狀態下對 Host 命令的阻塞或延遲響應行為。

## Test Case (TC) Checkpoints
1. [Case01_PowerOnWBEn_Enable_NoChange_Check]：
   - 動作：透過 `ExecuteCMD.SetFlag` 將 `POWER_ON_WB_EN` 設為 1，接著呼叫 `project_api.issue_D0FB_set_fw_state_in_ram(0)` 將韌體內部 RAM 狀態設為 0 (對應 Enable 邏輯)，執行 `init_tester_to_unit_ready` 並指定 `Dcmd5ResetType.RESET_N` (非硬體重啟/軟重置)。重置完成後，透過 `ExecuteCMD.ReadFlag` 讀取 `POWER_ON_WB_EN` 的值。
   - 預期結果：讀回的值 `val` 必須等於 1。這證明在 `RESET_N` 情境下，韌體設定的 Power-On Write Buffer Enable 狀態被保留或正確恢復，未被重置為預設值。

2. [Case02_PowerOnWBEn_Disable_Change_Check]：
   - 動作：重置 LUN 配置，再次透過 `project_api.issue_D0FB_set_fw_state_in_ram(1)` 將韌體內部 RAM 狀態設為 1 (對應 Disable 邏輯)，執行 `init_tester_to_unit_ready` 並指定 `Dcmd5ResetType.RESET_N`。重置完成後，透過 `ExecuteCMD.ReadFlag` 讀取 `POWER_ON_WB_EN` 的值。
   - 預期結果：讀回的值 `val` 必須等於 0。這證明在 `RESET_N` 情境下，若韌體狀態指示為 Disable，則 Host 讀取的標誌位元會正確反映為 0，驗證狀態機在軟重置後的邏輯一致性。

3. [Case03_ISR_Timeout_Trigger_Check]：
   - 動作：透過 `project_api.issue_D0FB_set_fw_state_in_ram(2)` 將韌體內部 RAM 狀態設為 2 (對應 Trigger ISR/Timeout 邏輯)。隨後立即發送 `ExecuteCMD.ReadFlag` 指令讀取 `POWER_ON_WB_EN`。
   - 預期結果：`ExecuteCMD.send` 或 `read_response` 必須拋出 `api.TIMEOUT_EXCEPTIONS` 異常。這證明當韌體處於狀態 2 時，Host 發送的讀取命令會被韌體內部 ISR 機制攔截或延遲處理，導致命令超時，驗證韌體在特定異常或維護狀態下的命令阻塞行為。