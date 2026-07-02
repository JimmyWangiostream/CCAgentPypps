# Test Spec: UFS Device Descriptor & Product Name String Descriptor Retrieval & Validation

## Verification Criterion (VC)
驗證 UFS 主機端韌體透過標準 SCSI/SPC 指令集正確讀取並解析 UFS 裝置描述符（Device Descriptor）與產品名稱字串描述符（Product Name String Descriptor）的能力：確認 `b21_product_name` 欄位能正確指向對應的字串索引，且透過 `get_product_name_string_descriptor` API 讀取的 `ProductNameStringDescriptor410` 結構體中，長度欄位 `b0_length`、描述符 ID `b1_descriptor_idn` 以及後續的字串數據欄位（`w0_uc_0` 至 `wN_uc_N`）均符合 UFS 規範定義的格式與預期內容，確保韌體對 USB/UFS 描述符解析邏輯的正確性。

## Test Case (TC) Checkpoints
1. [Device_Desc_Retrieval_and_Index_Extract]：
   - 動作：呼叫 `api.get_device_descriptor()` 獲取 UFS 裝置描述符物件，並透過 `cast` 確保其為 `DeviceDescriptor410` 類型。記錄日誌並提取該描述符中的 `b21_product_name` 欄位值（即產品名稱字串的描述符索引）。
   - 預期結果：成功獲取 Device Descriptor；`b21_product_name` 欄位必須為一個有效的非負整數索引值，該值將作為後續讀取 Product Name String Descriptor 的參數，代表該 UFS 裝置在配置階段宣告的產品名稱字串索引。

2. [Product_Name_String_Desc_Retrieval_and_Structure_Parse]：
   - 動作：使用上一步取得的 `b21_product_name` 索引，呼叫 `api.get_product_name_string_descriptor(index)` 讀取對應的字串描述符。將返回結果強制轉換為 `ProductNameStringDescriptor410` 類型。記錄並驗證結構體中的 `b0_length`（描述符長度）、`b1_descriptor_idn`（描述符 ID，應為 0x03 表示 String Descriptor）以及依序排列的字串數據欄位（如 `w0_uc_0`, `w1_uc_1` 等，對應 UTF-16LE 編碼的字元）。
   - 預期結果：
     - `b1_descriptor_idn` 必須等於 `0x03`，確認其為標準字串描述符類型。
     - `b0_length` 必須大於等於 4（包含長度欄位與 ID 欄位的最小值），且與實際讀取到的字串數據長度一致。
     - 依序讀取的 `w{i*2+2}_uc_{i}` 欄位數據必須構成有效的 UTF-16LE 編碼字串，且內容與 UFS 裝置內部儲存或供應商定義的產品名稱完全匹配，無亂碼或截斷現象。