# Test Spec: UFS Vendor Command 0x4010 Page Attribute Validation

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command 0x4010 (Get Page Attribute) 回傳之 LUN Page Attribute 結構完整性與邏輯正確性：針對 Page Index 0x0000 至 0x0CFB (3307) 之 TLC 區域、0x0654 至 0x0673 (1620-1651) 之 MLC 區域、0x0CEC 至 0x0CF3 (3308-3311) 之 SLC 區域，確認回傳之 `page_attribute` 欄位與 `TLC_page_list` (Lower/Upper/Extra) 索引陣列符合硬體定義之分頁邏輯；針對 Page Index 0x0CFC (3312) 及 0x0CFD (3313) 等無效索引，確認裝置正確回傳 SCSI CHECK CONDITION 狀態，且 Sense Key 為 ILLEGAL_REQUEST，ASC/ASCQ 為 0x1A/0x00 (PARAMETER LIST LENGTH ERROR)，以確保韌體對越界請求之錯誤處理機制正常運作。

## Test Case (TC) Checkpoints
1. [Valid_Page_Index_Attribute_Check]:
   - 動作：迴圈遍歷 Page Index 從 0 到 3311。針對每個 Index，透過 `project_api.issue_4010_get_page_attribute` 發送 Vendor Command 0x4010。若 Index <= 3311，檢查 UPIU Response 是否為 `TARGET_SUCCESS`。若成功，解析 Response Data 前 15 Bytes：Bytes 0-2 為 `page_attribute`，Bytes 4-6 為 `TLC_lower`，Bytes 8-10 為 `TLC_upper`，Bytes 12-14 為 `TLC_extra`。將解析結果與 `expected_page_attribute` 函數計算之預期值進行比對。預期邏輯為：Index 0-1619 屬 TLC_lower 組 (Attribute 3)，Index 1652-3307 屬 TLC_upper/extra 組 (Attribute 4/5)，Index 1620-1651 屬 MLC (Attribute 1/2)，Index 3308-3311 屬 SLC (Attribute 0)。
   - 預期結果：UPIU Response 必須為 `TARGET_SUCCESS`；解析出之 `page_attribute` 整數值與 `TLC_page_list` 陣列必須與預期值完全一致。此驗證硬體韌體正確維護並回傳 Flash 分頁屬性映射表，確保 Host 能正確識別不同 LUN 區域之 TLC/MLC/SLC 分頁結構。

2. [Invalid_Page_Index_Error_Handling_Check]:
   - 動作：當 Page Index 為 3312 或 3313 時，發送 Vendor Command 0x4010。檢查 UPIU Response 狀態碼、SCSI Status 及 Sense Data。
   - 預期結果：UPIU Response 必須為 `TARGET_FAILURE`；SCSI Status 必須為 `CHECK_CONDITION`；Sense Key 必須為 `ILLEGAL_REQUEST`；ASC (Additional Sense Code) 必須為 `0x1A`；ASCQ (Additional Sense Code Qualifier) 必須為 `0x00`。此驗證硬體韌體在接收到超出有效 Page Index 範圍 (0-3311) 之請求時，能正確拒絕並回傳標準之參數列表長度錯誤 (Parameter List Length Error)，防止 Host 讀取未定義之記憶體或行為。