# Test Spec: UFS Serial Number String Descriptor Write Protection & Integrity Test

## Verification Criterion (VC)
驗證 UFS 裝置在透過 Vendor Command (C04A) 修改 Serial Number String Descriptor (IDN=0x05) 時的韌體保護機制與資料一致性：
1. **錯誤注入防護**：當嘗試寫入超出 Descriptor 定義長度（Size > 64 Bytes，具體為 65 Bytes）的資料時，韌體必須拒絕該寫入請求，返回 Sense Data ASC 0x26 (INVALID FIELD IN CDB) 或狀態碼 0，且 Descriptor 內容必須保持不變。
2. **正常寫入驗證**：當寫入符合長度規範（Size = 64 Bytes）且內容合法的資料時，韌體必須成功更新 Descriptor，讀回資料必須與寫入資料完全一致。
3. **恢復機制驗證**：在成功寫入新資料後，再次寫入原始備份資料，韌體必須能正確還原 Descriptor 至初始狀態，確保資料可逆性與完整性。

## Test Case (TC) Checkpoints
1. [Case01_ErrorCase_LengthViolation_Check]：
   - 動作：
     1. 透過 `pattern_get_device_descriptor` 讀取 Device Descriptor，提取 `b22_serial_number` 作為該 LUN 的 Serial Number Index (`assignd_index_for_idn5`)。
     2. 透過 `pattern_get_descriptor(5)` 讀取當前 Serial Number String Descriptor 並備份為 `descriptor_backup`。
     3. 構造錯誤寫入 Payload：設定 `size_of_descriptor.value = 65` (超出標準 64 Bytes 限制)，`string_type_identifier.value = 5`。
     4. 修改 Payload 內容：從 Descriptor 第 2 位元開始截取至 `end_offset` (64)，並在 `setting_payload[3]` (offset 3) 處數值 +1 以產生差異。若 Payload 長度不足則補 0。
     5. 呼叫 `project_api.issue_C04A_to_set_serial_number_string(serial_number, True)` 發送寫入指令。
     6. 檢查回應 `rsp`：驗證 `rsp.b32_sense_data.b12_asc` 是否等於 `0x26` 或 `rsp.upiu.b7_status == 0`。
     7. 清除命令佇列後，再次讀取 Descriptor (`pattern_get_descriptor(5)`) 並與 `descriptor_backup` 進行比對。
   - 預期結果：
     - 寫入指令必須失敗，Sense Data ASC 必須為 `0x26` (或狀態碼為 0)，代表韌體正確拒絕了長度違規的寫入請求。
     - 讀回後的 Descriptor 資料必須與 `descriptor_backup` **完全相等**，證明錯誤寫入未對 Flash 中的 Descriptor 造成任何污染或變更。

2. [Case02_NormalWrite_Integrity_Check]：
   - 動作：
     1. 構造正常寫入 Payload：設定 `size_of_descriptor.value = 64`，`string_type_identifier.value = 5`。
     2. 修改 Payload 內容：從 Descriptor 第 2 位元開始截取至 `end_offset` (63)，並在 `setting_payload[3]` 處數值 +1，同時在 `descriptor_setting[setting_value_offset + 2]` (即 offset 5) 處數值 +1 以產生特定差異模式。若 Payload 長度不足則補 0。
     3. 呼叫 `project_api.issue_C04A_to_set_serial_number_string(serial_number)` 發送寫入指令。
     4. 讀取寫入後的 Descriptor (`pattern_get_descriptor(5)`) 並與構造時使用的 `descriptor_setting` 進行比對。
   - 預期結果：
     - 寫入指令必須成功（無異常拋出）。
     - 讀回後的 Descriptor 資料必須與 `descriptor_setting` **完全相等**，證明韌體正確解析並寫入了符合長度規範的 Payload，且資料完整性無損。

3. [Case03_Recovery_Rollback_Check]：
   - 動作：
     1. 構造恢復寫入 Payload：設定 `size_of_descriptor.value = 64`，`string_type_identifier.value = 5`。
     2. 使用 Case 01 中備份的原始資料 `descriptor_backup`，從第 2 位元開始截取至 `end_offset` (63) 作為 Payload 內容。若長度不足則補 0。
     3. 呼叫 `project_api.issue_C04A_to_set_serial_number_string(serial_number)` 發送寫入指令，將 Descriptor 還原。
     4. 讀取寫入後的 Descriptor (`pattern_get_descriptor(5)`) 並與 `descriptor_backup` 進行比對。
   - 預期結果：
     - 寫入指令必須成功。
     - 讀回後的 Descriptor 資料必須與 `descriptor_backup` **完全相等**，證明韌體支援資料還原，且經過正常寫入與恢復流程後，Descriptor 狀態與初始狀態一致，無殘留髒資料。