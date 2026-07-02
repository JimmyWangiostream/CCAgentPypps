# Test Spec: UFS Inhibition Manager Lock State Transition & GC Trigger Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 `gInhibitMgr` 模組在硬體重置（HW_RESET）與電源循環（Power Cycle）後的狀態機行為：Case 01 確認在 `INHIBITION_TIME` 硬體設定值內，`gInhibitMgr.lock` 狀態必須嚴格保持為 1（鎖定），且期間禁止 GC 觸發；Case 02 確認當等待時間超過 `INHIBITION_TIME` 後，`gInhibitMgr.lock` 狀態必須自動切換為 0（解鎖），且此後允許 GC 觸發。此測試旨在驗證韌體對 Flash 介面的保護機制（Inhibition）是否正確依硬體計時器運作，並確保解鎖後系統能正常進入垃圾回收（GC）流程。

## Test Case (TC) Checkpoints
1. [Case01_PreInhibition_LockState_GCBlock_Check]：
   - 動作：
     1. 透過 `api.HwSetting` 讀取硬體設定欄位 `INHIBITION_TIME`，獲取抑制時間秒數 `inhibition_time_sec`。
     2. 執行隨機選擇的 HW_RESET（含/不含 Power Down）並進入 Vendor Mode。
     3. 讀取韌體全域變數 `gInhibitMgr.lock`，確認初始狀態為 1。
     4. 執行 "Read back Open Host TLC VB" 操作（模擬 Host 讀取請求）。
     5. 檢查 GC 觸發狀態，確認 GC **未**被觸發。
     6. 進入休眠狀態，等待時間等於 `inhibition_time_sec`。
     7. 再次讀取 `gInhibitMgr.lock`，確認狀態仍為 1。
   - 預期結果：
     - 初始及等待期間，`gInhibitMgr.lock` 的值必須恆等於 1。
     - 在等待期間及解鎖前，GC 機制必須被抑制，狀態檢查結果為 "GC Not Triggered"。
     - 若 `gInhibitMgr.lock` 不等於 1 或 GC 被錯誤觸發，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [Case02_PostInhibition_UnlockState_GCAllow_Check]：
   - 動作：
     1. 在 Case 01 的等待時間 `inhibition_time_sec` 結束後，立即讀取韌體全域變數 `gInhibitMgr.lock`。
     2. 執行短暫延遲 `time.sleep(0.01)` 後，再次讀取 `gInhibitMgr.lock` 以確保狀態穩定。
     3. 執行 "Read back Open Host TLC VB" 操作。
     4. 檢查 GC 觸發狀態，確認 GC **已**被觸發。
   - 預期結果：
     - 兩次讀取的 `gInhibitMgr.lock` 值必須均等於 0。
     - 在抑制時間結束後，GC 機制必須被允許運作，狀態檢查結果為 "GC Triggered"。
     - 若 `gInhibitMgr.lock` 不等於 0 或 GC 未被觸發，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。