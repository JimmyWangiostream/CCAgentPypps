# Test Spec: UFS Inhibition Manager Lock State Transition & GC Trigger Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr.lock` 狀態機在硬體重置（HW_RESET）與電源循環（Power Cycle）後的正確性，以及 Inhibition Time 設定對垃圾回收（GC）觸發時機的影響：Case 01 確認在 HW_RESET 後（無論是否包含 Power Down），韌體初始化階段 `gInhibitMgr.lock` 必須嚴格為 1（鎖定狀態），且在此鎖定期間執行 Purge 與 Read back 操作時，目標 GC 流程不得被觸發；Case 02 確認經過預設的 `INHIBITION_TIME` 等待期後，`gInhibitMgr.lock` 狀態必須自動釋放為 0（解鎖狀態），此時再次執行 Purge 與 Read back 操作，系統必須成功觸發目標 GC 流程。此測試旨在驗證 Inhibition 機制能有效防止初始化階段的非必要 GC 干擾，並在時間到期後正確恢復正常操作。

## Test Case (TC) Checkpoints
1. [Case01_Post_Reset_Lock_State_Check]:
   - 動作：透過 `get_hwsetting_inhibition_time` 讀取硬體設定中的 `INHIBITION_TIME` 並備份；執行 `power_cycle` 函數，該函數隨機選擇 `Dcmd5ResetType.HW_RESET` 搭配 `powerdown=False` 或 `powerdown=True` 進行硬體重置與初始化；初始化完成後，透過 `read_fw_value('gInhibitMgr.lock')` 讀取韌體內部變數 `gInhibitMgr.lock` 的值。
   - 預期結果：`gInhibitMgr.lock` 的讀取值必須嚴格等於 1。若讀取值不等於 1，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。此結果驗證了在 HW_RESET 後的韌體啟動初期，Inhibition Manager 處於鎖定狀態，阻止了外部命令或內部流程的干擾。

2. [Case02_Locked_GC_Inhibition_Check]:
   - 動作：在確認 `gInhibitMgr.lock == 1` 後，執行 `Purge` 指令並對目標 GC 區域進行 `Read back` 操作（僅限 FG 模式）；隨後檢查系統日誌或狀態標誌，確認 GC 觸發事件。
   - 預期結果：GC 觸發事件必須為「未觸發」（Not Triggered）。若 GC 被觸發，則判定測試失敗。此結果驗證了在 Inhibition 鎖定期間，即使有讀寫請求，系統也不會啟動垃圾回收流程，確保了初始化階段的穩定性。

3. [Case03_Post_Inhibition_Unlock_State_Check]:
   - 動作：執行 `time.sleep(self.inhibition_time_sec)` 等待預設的 Inhibition 時間過去；隨後連續兩次讀取 `gInhibitMgr.lock` 的值（中間間隔 0.01 秒以確保讀取穩定性）。
   - 預期結果：兩次讀取的 `gInhibitMgr.lock` 值均必須嚴格等於 0。若讀取值不等於 0，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。此結果驗證了 Inhibition 計時器到期後，鎖定狀態被正確釋放，系統恢復正常操作許可。

4. [Case04_Unlocked_GC_Trigger_Check]:
   - 動作：在確認 `gInhibitMgr.lock == 0` 後，再次執行 `Purge` 指令並對目標 GC 區域進行 `Read back` 操作（僅限 FG 模式）；隨後檢查系統日誌或狀態標誌，確認 GC 觸發事件。
   - 預期結果：GC 觸發事件必須為「已觸發」（Triggered）。若 GC 未被觸發，則判定測試失敗。此結果驗證了在 Inhibition 解除後，系統能夠正常響應並執行垃圾回收流程，確保儲存空間的有效管理。