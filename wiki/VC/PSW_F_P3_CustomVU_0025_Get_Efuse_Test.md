# Test Spec: UFS Efuse Data Consistency Verification (VU 40F4 vs X-Memory)

## Verification Criterion (VC)
驗證 UFS 裝置內部 Efuse 資料的一致性與存取路徑正確性：確認透過 Vendor Command (VU 40F4) 讀取的 Efuse 資料，與直接透過 SRAM 地址 `0xF8F80800` 進行 X-Memory 讀取所獲得的資料完全一致。此測試旨在排除韌體層級資料轉換錯誤或硬體記憶體映射異常，確保 Efuse 設定值在兩種不同存取機制下保持數值相同（Byte-for-Byte Match）。

## Test Case (TC) Checkpoints
1. [Efuse_Data_Consistency_Check]：
   - 動作：
     1. 執行 Vendor Command `VU 40F4`，呼叫 `project_api.issue_40F4_to_get_eFus()` 獲取韌體層級解析後的 Efuse 結構體資料 (`vu_data.efuse`)。
     2. 執行 X-Memory 讀取指令 `api.read_Xmemory`，指定 SRAM 起始地址為 `0xF8F80800`，獲取原始二進位資料 (`efuse_data_from_xmemory`)。
     3. 遍歷 `vu_data.efuse` 列表中的每一個 Efuse 項目，將 SRAM 原始資料按每 4 個位元組 (Little-Endian) 轉換為整數 (`value_from_sram`)，並與 Vendor Command 返回的對應項目數值 (`value_from_vu`) 進行逐項比對。
   - 預期結果：
     - 所有索引 `i` 對應的 `value_from_sram` 必須嚴格等於 `vu_data.efuse[i].value`。
     - 若任何一項不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常並記錄具體偏移量與十六進位數值差異。
     - 此結果證明 Vendor Command 40F4 的資料擷取邏輯與底層 X-Memory 硬體映射在地址 `0xF8F80800` 處呈現完全一致的硬體狀態。