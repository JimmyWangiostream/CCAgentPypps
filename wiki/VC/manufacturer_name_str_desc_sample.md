# Test Spec: UFS Device Descriptor Manufacturer String Descriptor Retrieval & Validation

## Verification Criterion (VC)
驗證 UFS 主機端韌體透過 USB/UFS 標準描述符獲取機制，正確讀取並解析 Device Descriptor 中指定的 Manufacturer Name String Descriptor 的能力。重點在於確認 `b20_manufacturer_name` 索引值能正確映射至對應的 String Descriptor，並驗證該 Descriptor 的結構完整性（長度、ID、以及具體的 Unicode 字元數據欄位 `w2_uc_0` 至 `w16_uc_7`）是否符合 UFS 規範定義的格式。

## Test Case (TC) Checkpoints
1. [Device_Desc_Mfr_Index_Extract]：
   - 動作：呼叫 `api.get_device_descriptor()` 獲取完整的 Device Descriptor，並透過 `cast` 確保型別為 `DeviceDescriptor410`。從返回的物件中讀取 `b20_manufacturer_name` 欄位（此為 String Descriptor Index），記錄該索引值。
   - 預期結果：成功獲取 Device Descriptor；`b20_manufacturer_name` 必須為一個有效的非零整數索引值（通常為 1 或特定 Vendor 定義的索引），代表該裝置在 String Descriptor 表中對應的位置。

2. [String_Desc_Retrieval_Structure_Check]：
   - 動作：使用上一步取得的 `b20_manufacturer_name` 作為參數，呼叫 `api.get_manufacturer_name_string_descriptor(index)` 獲取對應的 String Descriptor。透過 `cast` 確保型別為 `ManufacturerNameStringDescriptor410`。記錄返回物件的所有欄位值，包括 `b0_length`、`b1_descriptor_idn` 以及後續的 Unicode 字元欄位。
   - 預期結果：
     - `b0_length` 必須大於 2（至少包含 bLength 和 bDescriptorType 兩個位元組）。
     - `b1_descriptor_idn` 必須等於 0x03（代表 String Descriptor 類型）。
     - 後續欄位 `w2_uc_0` 至 `w16_uc_7` 必須包含有效的 Unicode 1.1 或 2.0 編碼數據，且總長度與 `b0_length` 一致。

3. [Unicode_Data_Integrity_Verification]：
   - 動作：檢查 `ManufacturerNameStringDescriptor410` 物件中的具體字元欄位：`w2_uc_0`, `w4_uc_1`, `w6_uc_2`, `w8_uc_3`, `w10_uc_4`, `w12_uc_5`, `w14_uc_6`, `w16_uc_7`。
   - 預期結果：這些欄位必須包含合法的 16-bit Unicode 字元值，且組合起來應能正確解碼為製造商名稱（例如 "Samsung", "Kioxia" 等，視具體硬體而定）。若欄位值為 0x0000 或無意義數據，則視為驗證失敗，表示 String Descriptor 未正確配置或讀取錯誤。