# Test Spec: Thermal Protection Hard Cold-Only Stuck Recovery Test

## Verification Criterion (VC)
驗證 UFS 裝置在啟用 Hard Thermal Protection (TP_HARD_COLD_ONLY) 且設定極端溫度閾值（TD_TOOLOW_AREA_ENTER = 180°C, TD_SUPER_HIGH_AREA_ENTER = 80°C）的情境下，當寫入操作觸發韌體熱保護斷言（Assert）時，系統行為符合預期：
1. 寫入命令應因觸發熱保護機制而無回應（Timeout），並記錄特定的韌體 Assert Code。
2. 透過 HW_RESET 或 RESET_N 硬體重啟後，裝置應恢復正常。
3. 驗證在熱保護觸發期間未成功寫入的 LBA 區域，其讀取結果應為預期的空值（CRC32 = 0x00000000），確認寫入操作在斷言發生前已被中止，未造成資料汙染。

## Test Case (TC) Checkpoints
1. [Case01_ColdOnly_Threshold_Setup_Check]：
   - 動作：執行 FormatUnit 初始化 UFS_DEVICE LUN。讀取熱保護閾值暫存器，透過 Vendor Command D0F3 將熱保護模式設定為 `TP_HARD_COLD_ONLY`。接著透過 Vendor Command D0F1 寫入 `WriteThermalStuckThreshold` 結構體，設定 `low_thermal_protection_threshold` 為原始低溫閾值，並將 `high_thermal_protection_threshold` 強制設定為 80（對應 UFS 溫度 = 實際溫度 + 80°C，即實際 0°C 觸發）。
   - 預期結果：閾值設定成功，裝置進入 Cold-Only 熱保護模式，且高溫度觸發點被極度拉低以模擬過熱情境。

2. [Case02_NormalWrite_Verification_Check]：
   - 動作：在閾值設定完成後，針對 `TestNormalLun` (LUN 0) 的 `TestLBA` (LBA 0) 寫入 4KB 資料，並透過 `api.read_compare` 使用 `HW_COMPARE` 方法讀回比對。
   - 預期結果：寫入與讀回資料完全一致，確認在閾值設定初期（尚未觸發極端條件或條件未達標時），寫入功能正常運作。

3. [Case03_ExtremeThreshold_Override_Check]：
   - 動作：透過 Vendor Command D0F1 再次修改 `WriteThermalStuckThreshold`，將 `low_thermal_protection_threshold` 設定為 180（對應 UFS 溫度 180°C，極高閾值），並將 `high_thermal_protection_threshold` 設為原始高溫閾值。此設定旨在確保當前環境溫度或模擬狀態下，寫入操作會立即觸發 `TD_TOOLOW_AREA_ENTER` 或相關熱保護斷言機制（註：根據程式碼邏輯，此處設定意在讓後續寫入觸發保護）。
   - 預期結果：閾值更新成功，為後續的異常寫入測試建立觸發條件。

4. [Case04_WriteTimeout_AssertCode_Check]：
   - 動作：針對 `TestLBA + TestSize` (LBA 1) 發送 Write10 命令寫入 4KB 資料。由於熱保護閾值已設定為極端值，預期寫入操作會觸發韌體熱保護斷言。監控命令回應，預期發生 `TIMEOUT_EXCEPTIONS`。在捕獲異常後，透過 `api.get_fw_assert_number()` 讀取韌體 Assert Code。
   - 預期結果：Write10 命令必須超時（無回應）；讀取的 Assert Code 必須不等於 0x0，代表韌體確實記錄了熱保護觸發的斷言事件，而非無故掛起。

5. [Case05_Reset_Recovery_DataIntegrity_Check]：
   - 動作：針對兩種重置模式（`HW_RESET` 與 `RESET_N`）分別執行重置流程。重置完成後，針對之前嘗試寫入但未成功的 LBA (`TestLBA + TestSize`) 發送 Read10 命令讀取 4KB 資料，並設定 `sw_cmp` 的 `crc32` 為 `ExpectedCRC` (0x00000000)。
   - 預期結果：讀取操作成功完成；讀回資料的 CRC32 校驗碼必須等於 0x00000000。這證明在熱保護斷言觸發導致寫入中止後，該 LBA 區域未被寫入任何垃圾資料，保持了預期的空值狀態，驗證了熱保護機制在阻止非法寫入方面的有效性。