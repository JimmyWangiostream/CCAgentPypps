# Test Spec: UFS Descriptor Consistency & Vendor Command 4040 Verification

## Verification Criterion (VC)
驗證 UFS 裝置在初始化階段，透過標準 UPIU Read Descriptor 命令讀取的各 Descriptor 欄位（Manufacturer Name, Product Name, OEM ID, Product Revision, Serial Number, Manufacturer Date/ID）與透過 Vendor Command 0x4040 讀取的 `AllManufacturingSetting` 結構體數據之間的一致性。此測試旨在確認韌體內部製造資訊存儲區與標準 UFS 描述符映射表之間的數據同步機制正確無誤，防止因韌體更新或配置錯誤導致 Host 端讀取到的製造資訊與內部記錄不符。

## Test Case (TC) Checkpoints
1. [Descriptor_Read_and_Extract_Check]：
   - 動作：執行 `pre_process` 流程，首先透過 `pattern_get_device_descriptor` 發送 UPIU Read Descriptor (IDN=DEVICE) 命令，解析 Device Descriptor 結構體，提取以下欄位並儲存至類別成員變數：
     - `b20_manufacturer_name` (Manufacturer Name Index)
     - `b21_product_name` (Product Name Index)
     - `b22_serial_number` (Serial Number Index)
     - `b42_product_revision_level` (Product Revision Level)
     - `b23_oem_id` (OEM ID Index)
     - `w24_manufacturer_id` (Manufacturer ID)
     - `w18_manufacturer_date` (Manufacturer Date)
     接著，針對上述提取的 Index，分別發送 UPIU Read Descriptor (IDN=STRING, Index=對應Index) 命令，讀取對應的 String Descriptor 原始資料 (bytearray)，並透過 `dumpfile` 儲存至 `manufacture_name.bin`, `product_string_name.bin`, `oem_id.bin`, `product_revision_level.bin`, `serial_number.bin`。同時，透過 `project_api.get_smart_info` 讀取 Smart Info Payload 偏移量 0x4A8 處的 8 Bytes 數據，解析為 `ats_times` 並記錄日誌。
   - 預期結果：所有 Descriptor 讀取命令回應狀態碼為 SUCCESS；提取的 Index 值必須為有效的非負整數；Smart Info 中的 ATS Timer 數據必須成功解析為整數；各 String Descriptor 原始資料必須包含有效的字串內容（非空或全零）。

2. [VendorCmd_4040_Data_Integrity_Check]：
   - 動作：執行 `test_4040` 流程，呼叫 `project_api.issue_4040_to_get_all_manufacturing_setting()` 發送 Vendor Command 0x4040，獲取 `AllManufacturingSetting` 結構體 (`all_manufacturing_name`)。該結構體包含 `manufacturer_name`, `product_name_string`, `oem_id`, `product_revision_level`, `serial_number_string`, `manufacturer_date`, `manufacturer_id` 等欄位。
   - 預期結果：Vendor Command 回應狀態碼為 SUCCESS；`all_manufacturing_name` 結構體內的各欄位必須被正確填充，無解析錯誤。

3. [Cross_Reference_Data_Comparison_Check]：
   - 動作：將步驟 1 讀取的 String Descriptor 原始資料與步驟 2 讀取的 Vendor Command 數據進行逐欄位比對。具體比對邏輯如下：
     - **Manufacturer Name**：取 `manufacture_name_descriptor` 原始資料的第 2 至 17 位元組 (offset 2, length 16)，與 `all_manufacturing_name.manufacturer_name.payload` 進行 `bytearray` 相等性比對。
     - **Product Name String**：取 `product_string_name_descriptor` 原始資料的第 2 至 33 位元組 (offset 2, length 32)，與 `all_manufacturing_name.product_name_string.payload` 進行比對。
     - **OEM ID**：取 `oem_id_descriptor` 原始資料的第 2 至 63 位元組 (offset 2, length 62)，與 `all_manufacturing_name.oem_id.payload` 進行比對。
     - **Product Revision Level**：取 `product_revision_level_descriptor` 原始資料的第 2 至 9 位元組 (offset 2, length 8)，與 `all_manufacturing_name.product_revision_level.payload` 進行比對。
     - **Serial Number String**：取 `serial_number_descriptor` 原始資料的第 2 至 63 位元組 (offset 2, length 62)，與 `all_manufacturing_name.serial_number_string.payload` 進行比對。
     - **Manufacturer Date**：比對 `all_manufacturing_name.manufacturer_date.value` 與步驟 1 從 Device Descriptor 提取的 `self.device_manufacture_date`。
     - **Manufacturer ID**：比對 `all_manufacturing_name.manufacturer_id.value` 與步驟 1 從 Device Descriptor 提取的 `self.device_manufacture_id`。
   - 預期結果：所有上述比對條件必須全部為 True。若任一欄位比對失敗，腳本必須拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。這代表 Vendor Command 0x4040 返回的製造資訊與 UFS 標準描述符中定義的製造資訊完全一致，驗證了韌體中製造資訊存儲區與描述符映射表的一致性。