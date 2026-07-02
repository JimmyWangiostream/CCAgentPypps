# Test Spec: UFS DUT Environment Initialization & Hardware Capability Detection

## Verification Criterion (VC)
驗證測試框架在執行階段對 DUT (Device Under Test) 硬體環境的偵測邏輯與專案配置覆蓋機制：確認腳本能正確讀取並記錄關鍵硬體參數（CE 數量、M1/M2 控制器型號、UFS 版本、Vendor ID），並透過 `set_to_specific_project` API 強制覆寫這些參數，以確保後續測試邏輯能基於特定的模擬硬體環境（如 M1=25, M2=20, M3=5, M4=1, Vendor=52, UFS Ver=1024）執行，而非依賴實際連接的實體 DUT 狀態。

## Test Case (TC) Checkpoints
1. [Hardware_Capability_Detection_and_Logging]：
   - 動作：初始化 DUT 實例，依序檢查並記錄以下硬體屬性：
     1. 檢查 `dut.ce_num` 是否大於 0，若成立則記錄 CE (Channel Engine) 數量。
     2. 檢查 `dut.m1` 是否大於 `api.M1.PS8311` (即 8325)，若成立則記錄 M1 控制器型號資訊。
     3. 檢查 `dut.m2` 是否等於 `api.M2.KIOXIA_BICS9_CTLC`，若成立則記錄 M2 為 Kioxia BICS9 控制器。
     4. 檢查 `dut.ufs_version` 是否大於 `0x210` (UFS 2.1)，若成立則記錄 UFS 版本資訊。
     5. 檢查 `dut.vendor_id` 是否等於 `api.VendorID.MICRON`，若成立則記錄 Vendor 為 Micron。
   - 預期結果：Logger 應輸出對應的硬體偵測資訊；此步驟僅為偵測與記錄，不改變 DUT 內部狀態，僅驗證框架對硬體識別 API 的呼叫正確性。

2. [Project_Configuration_Override]：
   - 動作：呼叫 `dut.set_to_specific_project` 函數，強制設定以下硬體參數：
     - M1 = 25
     - M2 = 20
     - M3 = 5
     - M4 = 1
     - vendor_id = 52
     - ufs_version = 1024
   - 預期結果：DUT 的內部硬體模擬狀態被覆寫為指定值；此動作模擬了一個特定的專案環境，確保後續測試步驟（若存在）將基於這些固定的硬體參數進行邏輯判斷，忽略實際連接 DUT 的真實硬體規格。