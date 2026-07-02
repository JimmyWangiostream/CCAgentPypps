# Test Spec: UFS Power Parameters Descriptor Retrieval & Validation

## Verification Criterion (VC)
驗證 UFS 主機控制器透過標準 Get Parameters 命令（Opcode 0x06）成功讀取裝置的 Power Parameters Descriptor (IDN 0x41) 的能力，並確認韌體解析出的電源參數結構完整性：
1. 確認 `api.get_power_params_descriptor()` 能正確從 UFS 裝置讀取 Descriptor 資料。
2. 確認讀取的 Descriptor 類型為 `PowerParametersDescriptor410`。
3. 確認 Descriptor 中的長度欄位 (`b0_length`) 與描述符 ID (`b1_descriptor_idn`) 符合 UFS 規範定義。
4. 確認 Descriptor 內部的電流消耗級別（ICC Levels）欄位被正確解析並輸出，涵蓋 VCC、VCCQ 及 VCCQ2 三組電源軌的 Active ICC Levels 數據，確保韌體對 Descriptor 記憶體映射（Memory Mapping）與位元偏移計算（Offset Calculation）正確無誤。

## Test Case (TC) Checkpoints
1. [Descriptor_Retrieval_and_Structure_Validation]：
   - 動作：執行 `api.get_power_params_descriptor()` 向 UFS 裝置發送 Get Parameters 命令（IDN=0x41），獲取返回的 Descriptor 物件。將該物件強制轉型（Cast）為 `api.PowerParametersDescriptor410` 類型。記錄 Descriptor 的類別名稱、`b0_length`（Descriptor 長度）以及 `b1_descriptor_idn`（描述符 ID，應為 0x41）。
   - 預期結果：命令執行成功，無錯誤狀態碼返回；Descriptor 類別名稱確認為 `PowerParametersDescriptor410`；`b1_descriptor_idn` 數值必須等於 0x41；`b0_length` 數值必須大於 0 且符合該版本 Descriptor 的預期長度（通常為 0x20 或根據裝置能力動態調整）。

2. [VCC_Current_Levels_Parsing_Check]：
   - 動作：遍歷 Descriptor 物件中的 `w{i * 2 + 2}_active_icc_levels_vcc_{i}` 欄位（其中 `i` 從 0 到 `power_desc._length - 1`）。讀取並記錄每個索引 `i` 對應的 VCC 電源軌在特定 Active ICC Level 下的電流消耗值。
   - 預期結果：所有讀取的 VCC 電流值必須為有效的非負整數；欄位索引計算邏輯 `i * 2 + 2` 必須正確對應到 Descriptor 資料結構中 VCC ICC Levels 的起始偏移位置，確保沒有發生記憶體越界或數據錯位。

3. [VCCQ_Current_Levels_Parsing_Check]：
   - 動作：遍歷 Descriptor 物件中的 `w{i * 2 + 34}_active_icc_levels_vccq_{i}` 欄位（其中 `i` 從 0 到 `power_desc._length - 1`）。讀取並記錄每個索引 `i` 對應的 VCCQ 電源軌在特定 Active ICC Level 下的電流消耗值。
   - 預期結果：所有讀取的 VCCQ 電流值必須為有效的非負整數；欄位索引計算邏輯 `i * 2 + 34` 必須正確對應到 Descriptor 資料結構中 VCCQ ICC Levels 的起始偏移位置（相對於 Descriptor 起始地址的偏移量），驗證韌體對 VCCQ 數據區塊的定位準確性。

4. [VCCQ2_Current_Levels_Parsing_Check]：
   - 動作：遍歷 Descriptor 物件中的 `w{i * 2 + 66}_active_icc_levels_vccq2_{i}` 欄位（其中 `i` 從 0 到 `power_desc._length - 1`）。讀取並記錄每個索引 `i` 對應的 VCCQ2 電源軌在特定 Active ICC Level 下的電流消耗值。
   - 預期結果：所有讀取的 VCCQ2 電流值必須為有效的非負整數；欄位索引計算邏輯 `i * 2 + 66` 必須正確對應到 Descriptor 資料結構中 VCCQ2 ICC Levels 的起始偏移位置，驗證韌體對 VCCQ2 數據區塊的定位準確性，確保三組電源軌的參數解析互不干擾且覆蓋完整。