# Test Spec: UFS Power Rail Current Measurement Baseline Verification

## Verification Criterion (VC)
驗證 UFS 裝置在特定測試腳本執行階段（Step 1），其供電軌（Power Rails）的電流消耗數值是否可被 SDK 正確讀取並記錄。此測試主要確認 `VCC`、`VCCQ2` 以及 `VCCQ` 三個關鍵電源軌的即時電流測量功能是否正常運作，並檢查程式碼中是否存在針對 `VCCQ` 通道的測量邏輯錯誤（即代碼中重複測量 `VCC` 而非 `VCCQ` 的潛在 Bug）。

## Test Case (TC) Checkpoints
1. [Power_Rail_Current_Measurement_Check]：
   - 動作：執行 `step1` 函數，透過 `_sdk.measure_current` API 分別讀取 `lib.CurrentChannel.VCC`、`lib.CurrentChannel.VCCQ2` 以及 `lib.CurrentChannel.VCC`（注意：代碼中第三個呼叫錯誤地使用了 VCC 而非 VCCQ）的即時電流值，並將結果列印至標準輸出。
   - 預期結果：
     1. `VCC` 通道測量值必須為有效的浮點數或整數電流讀數（單位通常為 mA 或 uA，視 SDK 定義而定），且非零或非錯誤碼。
     2. `VCCQ2` 通道測量值必須為有效的電流讀數。
     3. 第三個列印輸出（標記為 `vccq`）實際上顯示的是 `VCC` 通道的測量值，而非 `VCCQ` 通道。這意味著在當前程式碼邏輯下，**無法驗證 `VCCQ` 通道的真實電流狀態**，該變數 `vccq_result` 的內容與 `vcc_result` 完全相同。若測試目標包含驗證 `VCCQ` 電流，則此步驟將導致驗證失敗或數據誤導，因為預期結果應為 `vccq_result.current` 等於 `VCCQ` 通道的獨立測量值，但實際行為為重複讀取 `VCC`。