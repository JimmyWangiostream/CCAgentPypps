# Test Spec: Thermal Protection VU (D0F1/D0F3) Hard Thermal Stuck Recovery Test

## Verification Criterion (VC)
驗證 UFS 裝置在啟用 Hard Thermal Protection (Hot/Cold Mode) 且設定特定低/高溫閾值後，當寫入操作觸發熱保護機制導致韌體 Assert (Stuck) 時，系統能否正確記錄 Assert Code，並透過 HW_RESET 或 RESET_N 硬體重啟恢復至 Unit Ready 狀態，同時確認異常寫入的資料未殘留於 Flash 中（讀取預期為 CRC 錯誤或無效資料）。

## Test Case (TC) Checkpoints
1. [Case01_HotMode_LowThresh_AssertAndRecovery_Check]：
   - 動作：
     1. 透過 Vendor Command (VU) D0F3 將 Thermal Protection 模式切換為 `TP_HARD_HOT_COLD` 並啟用。
     2. 透過 VU D0F1 寫入熱保護閾值：Low Threshold 設為 100°C (180-80)，High Threshold 設為 `StuckThreshold.high` (對應閾值)。
     3. 對 Normal LUN (LUN 0) 的 LBA 0 執行 4KB Write10 指令，並設定 `fua=1` (Force Unit Access)。
     4. 監控指令回應，預期發生 `TIMEOUT_EXCEPTIONS` (FW Stuck)，並透過 `api.get_fw_assert_number()` 讀取 DME Get Assert Code，驗證其不為 0x0。
     5. 執行 `HW_RESET` (powerdown=False) 進行硬體重啟。
     6. 重啟後，對 LBA 4 (0x1000) 執行 Read10 指令，並設定預期 CRC32 為 0x0。
   - 預期結果：
     - Write10 必須超時，且 FW Assert Code 必須非 0x0 (代表成功捕捉到熱保護觸發的 Assert)。
     - HW_RESET 後裝置需成功恢復至 Unit Ready 狀態。
     - Read10 指令執行後，由於之前的寫入因 FW Stuck 而未完成寫入 Flash，讀取的資料 CRC 應與預期值 (0x0) 不符或讀取失敗，驗證異常寫入未持久化。

2. [Case02_HotMode_HighThresh_AssertAndRecovery_Check]：
   - 動作：
     1. 透過 VU D0F3 將 Thermal Protection 模式切換為 `TP_HARD_HOT_COLD` 並啟用。
     2. 透過 VU D0F1 寫入熱保護閾值：Low Threshold 設為 `StuckThreshold.low` (對應閾值)，High Threshold 設為 160°C (240-80)。
     3. 對 Normal LUN (LUN 0) 的 LBA 0 執行 4KB Write10 指令，並設定 `fua=1`。
     4. 監控指令回應，預期發生 `TIMEOUT_EXCEPTIONS` (FW Stuck)，並透過 `api.get_fw_assert_number()` 讀取 DME Get Assert Code，驗證其不為 0x0。
     5. 執行 `HW_RESET` (powerdown=False) 進行硬體重啟。
     6. 重啟後，對 LBA 4 (0x1000) 執行 Read10 指令，並設定預期 CRC32 為 0x0。
   - 預期結果：
     - Write10 必須超時，且 FW Assert Code 必須非 0x0 (代表成功捕捉到熱保護觸發的 Assert)。
     - HW_RESET 後裝置需成功恢復至 Unit Ready 狀態。
     - Read10 指令執行後，由於之前的寫入因 FW Stuck 而未完成寫入 Flash，讀取的資料 CRC 應與預期值 (0x0) 不符或讀取失敗，驗證異常寫入未持久化。

3. [Case03_HotMode_LowThresh_AssertAndResetN_Recovery_Check]：
   - 動作：
     1. 透過 VU D0F3 將 Thermal Protection 模式切換為 `TP_HARD_HOT_COLD` 並啟用。
     2. 透過 VU D0F1 寫入熱保護閾值：Low Threshold 設為 100°C (180-80)，High Threshold 設為 `StuckThreshold.high`。
     3. 對 Normal LUN (LUN 0) 的 LBA 0 執行 4KB Write10 指令，並設定 `fua=1`。
     4. 監控指令回應，預期發生 `TIMEOUT_EXCEPTIONS` (FW Stuck)，並透過 `api.get_fw_assert_number()` 讀取 DME Get Assert Code，驗證其不為 0x0。
     5. 執行 `RESET_N` (透過 `manual_rst_n()`) 進行硬體重啟。
     6. 重啟後，對 LBA 4 (0x1000) 執行 Read10 指令，並設定預期 CRC32 為 0x0。
   - 預期結果：
     - Write10 必須超時，且 FW Assert Code 必須非 0x0 (代表成功捕捉到熱保護觸發的 Assert)。
     - RESET_N 後裝置需成功恢復至 Unit Ready 狀態。
     - Read10 指令執行後，由於之前的寫入因 FW Stuck 而未完成寫入 Flash，讀取的資料 CRC 應與預期值 (0x0) 不符或讀取失敗，驗證異常寫入未持久化。

4. [Case04_HotMode_HighThresh_AssertAndResetN_Recovery_Check]：
   - 動作：
     1. 透過 VU D0F3 將 Thermal Protection 模式切換為 `TP_HARD_HOT_COLD` 並啟用。
     2. 透過 VU D0F1 寫入熱保護閾值：Low Threshold 設為 `StuckThreshold.low`，High Threshold 設為 160°C (240-80)。
     3. 對 Normal LUN (LUN 0) 的 LBA 0 執行 4KB Write10 指令，並設定 `fua=1`。
     4. 監控指令回應，預期發生 `TIMEOUT_EXCEPTIONS` (FW Stuck)，並透過 `api.get_fw_assert_number()` 讀取 DME Get Assert Code，驗證其不為 0x0。
     5. 執行 `RESET_N` (透過 `manual_rst_n()`) 進行硬體重啟。
     6. 重啟後，對 LBA 4 (0x1000) 執行 Read10 指令，並設定預期 CRC32 為 0x0。
   - 預期結果：
     - Write10 必須超時，且 FW Assert Code 必須非 0x0 (代表成功捕捉到熱保護觸發的 Assert)。
     - RESET_N 後裝置需成功恢復至 Unit Ready 狀態。
     - Read10 指令執行後，由於之前的寫入因 FW Stuck 而未完成寫入 Flash，讀取的資料 CRC 應與預期值 (0x0) 不符或讀取失敗，驗證異常寫入未持久化。