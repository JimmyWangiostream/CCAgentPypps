# Test Spec: UFS Device Descriptor PRL String Descriptor Parsing & Validation

## Verification Criterion (VC)
驗證 UFS 主機端韌體在解析 Device Descriptor 中的 Product Revision Level (PRL) 欄位時，能否正確識別並映射至對應的結構體類型（如 `ProductRevisionLevelStringDescriptor410`），並精確提取與驗證 PRL 字串描述符的硬體定義欄位。具體驗證目標為：確認 `b0_length`（描述符長度）、`b1_descriptor_idn`（描述符 ID）、以及 `w2_uc_0` 至 `w8_uc_3`（PRL 字串內容的十六進位表示）的讀取值符合 UFS 規範定義的格式與預期數值，確保韌體對 PRL 字串的解析邏輯無誤。

## Test Case (TC) Checkpoints
1. [PRL_Descriptor_Parsing_Check]：
   - 動作：透過 `api.get_device_descriptor()` 獲取 Device Descriptor 物件，並從中讀取 `b42_product_revision_level` 欄位（此欄位為 PRL 字串描述符的索引或識別碼）。接著呼叫 `api.get_product_revision_level_string_descriptor()` 並傳入該識別碼，獲取具體的 PRL 描述符物件。將該物件強轉為 `ProductRevisionLevelStringDescriptor410` 類型，並記錄以下欄位的數值：`b0_length`、`b1_descriptor_idn`、`w2_uc_0`、`w4_uc_1`、`w6_uc_2`、`w8_uc_3`。
   - 預期結果：
     1. `b0_length` 必須等於該描述符在記憶體中的實際長度（通常為 0x04 或根據具體 PRL 字串長度調整，需符合 UFS 規範中 String Descriptor 的長度定義）。
     2. `b1_descriptor_idn` 必須等於 0x03（代表這是 String Descriptor 類型，依據 UFS 規範，String Descriptor 的 Descriptor ID 固定為 0x03）。
     3. `w2_uc_0` 至 `w8_uc_3` 的數值必須與 Device Descriptor 中 PRL 欄位所指向的實際字串內容一致，且以十六進位格式正確顯示。若 PRL 字串為 "4.10"，則對應的 ASCII 碼十六進位值應正確反映在這些欄位中（例如 '4' 為 0x34, '1' 為 0x31 等），驗證韌體對 PRL 字串的解析與輸出邏輯正確無誤。