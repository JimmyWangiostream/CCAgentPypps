# Test Spec: UFS OEM ID String Descriptor Retrieval & Structure Validation

## Verification Criterion (VC)
驗證 UFS 主機端韌體透過標準 SCSI/SPC 命令序列正確讀取 UFS 裝置的 OEM ID String Descriptor 結構完整性：確認 `get_oem_id_string_descriptor` API 能根據 Device Descriptor 中的 `b23_oem_id` 欄位值，精準定位並讀取對應的 OEM 字串描述符；驗證讀回之 `OEMIDStringDescriptor410` 結構體中，長度欄位 (`b0_length`)、描述符 ID (`b1_descriptor_idn`) 以及後續的字串資料欄位 (`w0_uc_*` 至 `wN_uc_*`) 均符合 UFS 規範定義的格式與預期數值，確保韌體對 Vendor Specific 描述符的解析邏輯正確無誤。

## Test Case (TC) Checkpoints
1. [OEM_ID_Descriptor_Readback_Check]：
   - 動作：呼叫 `api.get_device_descriptor()` 取得 UFS 裝置標準 Device Descriptor，提取其中的 `b23_oem_id` 欄位數值；接著呼叫 `api.get_oem_id_string_descriptor(device_desc.b23_oem_id)` 並傳入該 ID，讀取回傳之 `OEMIDStringDescriptor410` 物件；記錄並檢查該物件的 `b0_length`、`b1_descriptor_idn` 以及所有字串資料欄位（如 `w0_uc_0`, `w1_uc_1` 等）的十六進位數值。
   - 預期結果：`b0_length` 必須等於該描述符的實際總長度（包含長度欄位本身）；`b1_descriptor_idn` 必須對應至 UFS 規範中定義的 OEM ID String Descriptor ID；所有字串資料欄位 (`w*_uc_*`) 必須為有效的 ASCII 或 UTF-16 編碼字元，且數值與 UFS 裝置內部儲存之實際 OEM 資訊完全一致，無截斷或亂碼。