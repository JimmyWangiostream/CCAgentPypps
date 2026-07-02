# Test Spec: UFS Vendor Command SMART Info Retrieval Verification

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command 正確回應 SMART (Self-Monitoring, Analysis and Reporting Technology) 資訊的能力：確認 `buffer_get_smart_info` 函數能成功發起 Vendor Command 請求，並從裝置回傳的 Buffer 中正確解析出 SMART 數據結構。此測試旨在確認韌體與 Host 端 API 介面的通訊協定一致性，確保 Host 能透過標準 Vendor Command 接口讀取裝置內部健康狀態指標（如溫度、寫入量、錯誤計數器等），且無通訊錯誤或資料截斷。

## Test Case (TC) Checkpoints
1. [SMART_Info_Initialization_Check]：
   - 動作：執行 `buffer_get_smart_info()` 函數。該函數內部應封裝特定的 Vendor Command (通常為 UFS Vendor Specific Command，例如 Opcode 0x90 或廠商定義之讀取 SMART 指令)，設定正確的 CDB (Command Descriptor Block) 參數，並透過 UFS 傳輸層發送讀取請求。接著，等待裝置回傳 Sense Data 與 Data-Out Buffer，並由 API 將回傳的二進位資料解析為結構化的 SMART 資訊物件。
   - 預期結果：`buffer_get_smart_info()` 執行完畢後不應拋出 `UFSException` 或任何通訊錯誤；回傳的 SMART 資訊物件必須包含有效的欄位（例如 `temperature`, `total_data_written`, `power_on_hours` 等，具體欄位依 Vendor 定義而定）；Sense Data 中的 Status 必須為 0x00 (Good Status)，代表 Vendor Command 被裝置韌體正確接受並執行，且回傳的 Buffer 長度與預期 SMART 結構體大小一致。