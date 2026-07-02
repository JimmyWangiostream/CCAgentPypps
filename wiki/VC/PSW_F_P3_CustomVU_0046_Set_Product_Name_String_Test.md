# Test Spec: UFS Descriptor String Modification & Validation (C04A/C04B)

## Verification Criterion (VC)
驗證 UFS 裝置在透過 Vendor Command (C04A/C04B) 修改 String Descriptor (Product Name 與 Serial Number) 時的韌體行為與資料一致性：
1. **C04B (Product Name)**：驗證正常寫入流程能正確更新 Descriptor 內容，且寫入後讀回值與預期 payload 完全一致；驗證恢復流程能將資料還原至初始狀態。
2. **C04A (Serial Number)**：驗證錯誤情境（長度超限 65 bytes）下，裝置必須拒絕寫入並返回 ASC 0x26 (Invalid Field in CDB)，且 Descriptor 內容保持不變；驗證正常寫入流程（64 bytes）能正確更新，並驗證恢復流程能還原至初始狀態。
3. **核心邏輯**：確認韌體在處理 String Descriptor 修改時，具備邊界檢查機制（Boundary Check），且資料持久化（Persistence）與讀取一致性（Read-After-Write Consistency）符合 UFS 規範。

## Test Case (TC) Checkpoints

1. **[C04B_ProductName_Normal_Write_Check]**：
   - 動作：透過 `pattern_get_device_descriptor` 讀取 Device Descriptor 取得 Product Name Index (`b21_product_name`)，接著呼叫 `pattern_get_descriptor(5)` 讀取當前 Product Name Descriptor 並備份為 `descriptor_backup`。建立 `ProductNameString` 物件，將 payload 的第 3 個 byte (`setting_value_offset=3`) 數值加 1，並透過 `project_api.issue_C04B_to_set_serial_product_string` 發送 Vendor Command 寫入修改後的資料。寫入後再次讀取 Descriptor 並與修改後的預期值 (`descriptor_setting`) 進行逐 byte 比對。
   - 預期結果：Vendor Command 執行成功；讀回之 Descriptor 資料必須與 `descriptor_setting` 完全一致（特別是第 3 個 byte 已增加 1），代表韌體正確接受了 Product Name 的修改請求並更新了內部儲存結構。

2. **[C04B_ProductName_Recovery_Check]**：
   - 動作：使用初始備份的 `descriptor_backup` 資料，重新建構 `ProductNameString` payload，並再次呼叫 `project_api.issue_C04B_to_set_serial_product_string` 發送 Vendor Command 將資料還原。讀取當前 Descriptor 並與 `descriptor_backup` 進行逐 byte 比對。
   - 預期結果：Vendor Command 執行成功；讀回之 Descriptor 資料必須與 `descriptor_backup` 完全一致，代表韌體支援資料還原，且無殘留狀態或損壞。

3. **[C04A_SerialNumber_Error_Boundary_Check]**：
   - 動作：透過 `pattern_get_device_descriptor` 取得 Serial Number Index (`b22_serial_number`)，讀取當前 Descriptor 並備份。建立 `SerialNumberString` 物件，將 `size_of_descriptor` 設定為 65 (超過 UFS 規範最大長度 64)，並將 payload 第 3 個 byte 加 1。呼叫 `project_api.issue_C04A_to_set_serial_number_string` 並強制觸發錯誤檢查 (`True`)。捕獲回應，檢查 `rsp.b32_sense_data.b12_asc` 是否等於 `0x26` 且 `rsp.upiu.b7_status` 為 0。最後讀取 Descriptor 並與 `descriptor_backup` 比對。
   - 預期結果：Vendor Command 必須失敗，Sense Data 中的 ASC 欄位必須精確等於 `0x26` (Invalid Field in CDB)，表示韌體正確拒絕了長度違規的寫入請求；讀回之 Descriptor 資料必須與 `descriptor_backup` 完全一致，證明錯誤寫入未造成任何資料污染。

4. **[C04A_SerialNumber_Normal_Write_Check]**：
   - 動作：建立 `SerialNumberString` 物件，將 `size_of_descriptor` 設定為合法的 64，payload 第 3 個 byte 加 1。呼叫 `project_api.issue_C04A_to_set_serial_number_string` 發送正常寫入請求。讀取 Descriptor 並與預期修改後的值 (`descriptor_setting`) 進行逐 byte 比對。
   - 預期結果：Vendor Command 執行成功；讀回之 Descriptor 資料必須與 `descriptor_setting` 完全一致，代表韌體在長度合法的情況下正確更新了 Serial Number。

5. **[C04A_SerialNumber_Recovery_Check]**：
   - 動作：使用初始備份的 `descriptor_backup` 資料，重新建構 `SerialNumberString` payload (長度 64)，並呼叫 `project_api.issue_C04A_to_set_serial_number_string` 發送還原請求。讀取 Descriptor 並與 `descriptor_backup` 進行逐 byte 比對。
   - 預期結果：Vendor Command 執行成功；讀回之 Descriptor 資料必須與 `descriptor_backup` 完全一致，代表韌體能正確處理 Serial Number 的資料還原操作。