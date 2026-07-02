# Test Spec: UFS Device Descriptor & Serial Number String Descriptor Retrieval & Validation

## Verification Criterion (VC)
驗證 UFS 主機端韌體透過標準 USB/UFS 描述符獲取機制，正確讀取並解析 Device Descriptor 中的序列號索引，並進一步透過該索引成功獲取 Serial Number String Descriptor。驗證重點在於確認 `b22_serial_number` 欄位所指向的索引值能正確映射至對應的 String Descriptor 結構，且該 Descriptor 的長度 (`b0_length`)、描述符類型 (`b1_descriptor_idn`) 以及內部字串數據 (`w*_uc_*`) 能被完整且準確地讀取與記錄，確保設備序列號資訊的完整性與格式正確性。

## Test Case (TC) Checkpoints
1. [Device_Descriptor_Serial_Index_Extract]：
   - 動作：呼叫 `api.get_device_descriptor()` 獲取 UFS 設備的 Device Descriptor 物件，並將其強轉為 `api.DeviceDescriptor410` 類型。從該物件中提取 `b22_serial_number` 欄位的數值，此數值代表 Serial Number String Descriptor 在設備描述符列表中的索引（Index）。
   - 預期結果：成功獲取 Device Descriptor；`b22_serial_number` 欄位必須為一個有效的非零索引值（通常為 1 或更高，視設備固件配置而定），該值將作為後續獲取 String Descriptor 的關鍵參數。

2. [Serial_Number_String_Descriptor_Retrieval]：
   - 動作：使用上一步驟獲取的 `b22_serial_number` 索引值，呼叫 `api.get_serial_number_descriptor(index)` 獲取對應的 String Descriptor 物件，並將其強轉為 `api.SerialNumberStringDescriptor410` 類型。
   - 預期結果：成功獲取 Serial Number String Descriptor 物件；該物件必須存在且結構完整，未發生空指標或索引越界錯誤。

3. [String_Descriptor_Structure_Validation]：
   - 動作：對獲取的 `SerialNumberStringDescriptor410` 物件進行詳細解析與日誌記錄。檢查 `b0_length` 欄位以確認描述符總長度；檢查 `b1_descriptor_idn` 欄位以確認其值為 3（String Descriptor 的標準類型 ID）；遍歷 `serial_str_desc._length` 指定的範圍，逐一讀取並記錄每個字詞（Word）欄位（如 `w0_uc_0`, `w1_uc_1` 等）的十六進制數值。
   - 預期結果：
     - `b1_descriptor_idn` 必須等於 0x03（代表 String Descriptor）。
     - `b0_length` 必須大於等於 4（最小長度：1 byte length + 1 byte type + 2 bytes string data）。
     - 所有讀取的 `w*_uc_*` 欄位數值必須為有效的 UTF-16LE 編碼字元，且總長度與 `b0_length` 一致。這確認了設備序列號字串數據在記憶體中的佈局正確，無截斷或亂碼。