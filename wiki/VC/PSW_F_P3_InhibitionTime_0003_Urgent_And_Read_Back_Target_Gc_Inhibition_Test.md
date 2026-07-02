# Test Spec: UFS Inhibition Manager Lock State Transition & GC Trigger Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr.lock` 狀態機在硬體重置（HW_RESET）與電源循環（Power Cycle）後的正確性，以及 Inhibition Time 到期後 Urgent GC 觸發機制的有效性：Case 01 確認在 HW_RESET 後，Inhibition Manager 必須立即進入鎖定狀態（Lock=1）以阻止非必要的背景作業；Case 02 確認經過預設的 Inhibition Time 等待後，鎖定狀態必須自動解除（Lock=0），此時若再次執行 Urgent GC 指令，系統必須成功觸發垃圾回收流程，證明 Inhibition 機制已正確過期並允許背景任務執行。

## Test Case (TC) Checkpoints
1. [Case01_PostReset_LockState_Check]：
   - 動作：首先讀取韌體變數 `gInhibitMgr.lock` 的初始值並備份硬體設定的 `INHIBITION_TIME`。接著執行 `power_cycle` 函數，該函數隨機選擇是否包含電源關閉（Powerdown=True/False）的 HW_RESET 流程，將設備初始化至 Unit Ready 狀態並進入 Vendor Mode。重置完成後，立即讀取韌體變數 `gInhibitMgr.lock` 的值。
   - 預期結果：讀取到的 `gInhibitMgr.lock` 數值必須嚴格等於 1。這代表在硬體重置或電源循環後的初始化階段，Inhibition Manager 正確地將鎖定標誌設為啟用，防止韌體在系統尚未完全就緒時執行可能影響穩定性的背景操作（如 GC）。

2. [Case02_InhibitionTimeout_GC_Trigger_Check]：
   - 動作：在 Case 01 確認 Lock=1 後，程式碼執行 `time.sleep(self.inhibition_time_sec)`，等待時間長度等於從硬體設定中讀取的 `INHIBITION_TIME` 值。等待結束後，連續兩次讀取 `gInhibitMgr.lock` 以確保狀態穩定。確認該變數值已變更為 0。隨後，執行 Urgent GC 指令並讀取目標 GC 的相關狀態或結果。
   - 預期結果：`gInhibitMgr.lock` 數值必須嚴格等於 0，代表 Inhibition 計時器已過期且鎖定已解除。同時，Urgent GC 指令必須成功觸發垃圾回收流程（即 GC 被觸發且目標 GC 被正確讀取/執行），若 GC 未被觸發則判定為測試失敗。這驗證了 Inhibition 機制僅在特定時間窗口內生效，過期後系統能正常響應高優先級的背景維護請求。