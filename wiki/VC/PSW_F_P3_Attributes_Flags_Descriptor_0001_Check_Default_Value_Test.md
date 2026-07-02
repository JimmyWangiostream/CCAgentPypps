# Test Spec: UFS Descriptor & Attribute/Flag Compliance Verification

## Verification Criterion (VC)
驗證 UFS 裝置在初始化階段，其硬體描述符（Descriptors）、裝置旗標（Flags）及屬性（Attributes）的讀取值與規格書（Specification）或預設配置表（Excel Sheet）的一致性。
1. **Descriptor 完整性檢查**：確認 Device, Configuration, Geometry, RPMB Unit, Power Parameters, Interconnect, String Descriptors (Name, Product, OEM ID, Serial, Revision), Device Health 等共 10 類描述符的結構體欄位（如 `bNumberLU`, `qTotalRawDeviceCapacity`, `UC[]` 字串陣列等）讀取值與預期值完全匹配，或符合特定的 Skip/Not Readable 規則。
2. **Flag/Attribute 權限與值檢查**：確認特定 IDN 的 Flag 或 Attribute 讀取值正確，且針對不可讀（Not Readable, 0xF6）或不可寫（Not Writeable, 0xF7）的項目，UFS 協議層回應正確的 Query Response Code。
3. **動態索引映射檢查**：驗證 String Descriptor (IDN 5) 的 Index 是否正確映射自 Device Descriptor 中的 `b20_manufacturer_name`, `b21_product_name`, `b22_serial_number`, `b23_oem_id` 等欄位值。

## Test Case (TC) Checkpoints

1. [Descriptor_Read_and_Compare_Check]:
   - 動作：
     1. 透過 `ReadDescriptor` 命令讀取以下 IDN 的描述符資料：
        - IDN 0x0 (Device Descriptor): 讀取後解析 `b20_manufacturer_name`, `b21_product_name`, `b22_serial_number`, `b23_oem_id`, `b42_product_revision_level` 並儲存至類別變數。
        - IDN 0x1 (Configuration Descriptor): 讀取並解析。
        - IDN 0x2 (RPMB Unit Descriptor): 使用 Index 0xC4 讀取。
        - IDN 0x4 (Interconnect Descriptor): 讀取。
        - IDN 0x5 (String Descriptors): 使用上述儲存的動態 Index 分別讀取 Manufacturer Name, Product Name, OEM ID, Serial Number, Product Revision Level。
        - IDN 0x7 (Geometry Descriptor): 讀取。
        - IDN 0x8 (Power Parameters Descriptor): 讀取。
        - IDN 0x9 (Device Health Descriptor): 讀取。
     2. 將讀取的原始 Byte Array 與 Excel Sheet (`Descriptors` Sheet) 中定義的 `offset` 對應欄位進行比對。
     3. 針對特定欄位執行特殊邏輯：
        - 若欄位名包含 `bSupportedSecRTypes` 或 `bMaxContexIDNumber`，預期值強制修正為 15。
        - 若欄位名在 `check_if_name_included_special_skip_rule` 定義的 Skip List 中（如 `DeviceDescriptor` 的 `bNumberLU`, `GeometryDescriptor` 的 `qTotalRawDeviceCapacity` 等），則跳過比對（Action=TBD）。
        - 對於 String Descriptor 的 `UC[]` 欄位，將預期字串轉換為 ASCII 碼進行比對。
   - 預期結果：
     - 所有非 Skip 欄位的讀取值必須等於 Excel 中定義的 `target_value`。
     - 若讀取失敗或值不匹配，記錄錯誤並拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - String Descriptor 的 Index 必須與 Device Descriptor 中對應欄位值一致。

2. [Flag_and_Attribute_Read_Check]:
   - 動作：
     1. 透過 `ReadFlag` 命令讀取 IDN 0x1 的 Flag，並解析 `ret_val`。
     2. 透過 `ReadAttribute` 命令讀取 IDN 0x0 的 Attribute，並解析 `ret_val`。
     3. 針對 Excel Sheet (`Attributes_Flags`) 中定義的 Flag 和 Attribute 項目，執行以下檢查：
        - 若 Action 為 `COMPARE`：檢查讀取值是否等於 `target_value`，且 Query Response Code (`b6_query_response`) 必須為 0x0 (PASS)。
        - 若 Action 為 `NOTREADABLE`：檢查 Query Response Code 必須為 0xF6。
        - 若 Action 為 `NOTWRITEABLE`：檢查 Query Response Code 必須為 0xF7。
        - 若 Action 為 `TBD`：跳過檢查。
   - 預期結果：
     - 所有 Flag/Attribute 的讀取回應必須符合預期的 Action 定義。
     - 若讀取值不匹配或 Response Code 錯誤，記錄錯誤並拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

3. [Per_LUN_Special_Attribute_Check]:
   - 動作：
     1. 解析 Excel Sheet (`Attributes_Flags`) 中 `IDN` 關鍵字後的 Per-LUN 屬性數據。
     2. 針對每個 LUN ID (`lun_id`) 和 Selector，透過 `ReadAttribute` 命令讀取對應 IDN 的 Attribute。
     3. 處理特殊 Selector 規則：若欄位名包含 `wcontextconf`，Selector 值需 +1 (因 Spec 從 1 開始)；否則 Selector 為 0。
     4. 若預期值為列表格式（如 `[0x1, 0x2]`），則對列表中每個元素生成獨立的檢查項，分別比對對應 Selector 的值。
     5. 檢查邏輯同 Checkpoint 2：比對值或檢查 Response Code (0xF6/0xF7)。
   - 預期結果：
     - 所有 Per-LUN 屬性的讀取值或 Response Code 必須與 Excel 定義一致。
     - 若有任何 LUN 或 Selector 的檢查失敗，記錄錯誤並拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。