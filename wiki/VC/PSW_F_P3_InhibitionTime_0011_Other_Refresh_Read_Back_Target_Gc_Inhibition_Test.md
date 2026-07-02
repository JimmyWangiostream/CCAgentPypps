# Test Spec: UFS Inhibit Manager Lock State Transition Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr.lock` 狀態機在硬體重置（HW_RESET）與電源循環（Power Cycle）後的正確性與時序行為：Case 01 確認在執行 HW_RESET（含與不含 Power Down）後，韌體初始化階段 `gInhibitMgr.lock` 必須嚴格鎖定為 1，代表系統處於禁止干擾的初始化保護狀態；Case 02 確認在等待硬體設定的 `INHIBITION_TIME` 時長結束後，該鎖定狀態必須自動解鎖為 0，代表系統已進入正常操作模式且允許 GC 等背景任務觸發。此測試旨在確保 Inhibit Manager 的時鐘計時與狀態切換邏輯符合硬體規格，防止初始化期間的非法存取或背景任務衝突。

## Test Case (TC) Checkpoints
1. [Case01_PostReset_LockState_Check]：
   - 動作：首先透過 `get_hwsetting_inhibition_time` 讀取硬體設定中的 `INHIBITION_TIME` 欄位並備份。接著執行 `power_cycle` 函數，該函數隨機選擇兩種重置模式之一：模式 A 為 `Dcmd5ResetType.HW_RESET` 且 `powerdown=False`（僅硬體重啟不斷電），模式 B 為 `Dcmd5ResetType.HW_RESET` 且 `powerdown=True`（硬體重啟並觸發完整電源循環）。重置完成並進入 Vendor Mode 後，立即透過 `read_fw_value('gInhibitMgr.lock')` 讀取韌體內部變數 `gInhibitMgr.lock` 的值。
   - 預期結果：無論選擇模式 A 或 B，讀取到的 `gInhibitMgr.lock` 數值必須嚴格等於 1。若數值不等於 1，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此結果驗證了在 HW_RESET 後的韌體初始化初期，Inhibit Manager 確實處於鎖定狀態，阻止外部或內部非關鍵操作。

2. [Case02_PostInhibition_UnlockState_Check]：
   - 動作：在 Case 01 確認鎖定狀態為 1 後，程式碼執行 `time.sleep(self.inhibition_time_sec)`，等待時間長度等於硬體設定的 `INHIBITION_TIME`（單位為秒）。等待結束後，連續兩次讀取 `gInhibitMgr.lock` 的值（中間間隔 0.01 秒以確保讀取穩定性）。
   - 預期結果：兩次讀取到的 `gInhibitMgr.lock` 數值必須均嚴格等於 0。若數值不等於 0，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此結果驗證了在經過預期的 Inhibition 時間後，韌體自動將鎖定狀態解除，允許系統進入正常運行狀態（此時應允許 GC 觸發，對應程式碼中 flow 9 的邏輯預期）。