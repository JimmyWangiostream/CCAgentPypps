# Test Spec: UFS C04F Vendor Command WWYY Configuration Verification

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command (C04F) 修改 Device Health Descriptor 中 `q5_vendor_prop_info_1` (WWYY 欄位) 的寫入與讀回一致性：Case 01 確認在初始狀態下，將 WWYY 值增加 3 後寫入，讀回 Health Descriptor 的對應欄位必須精確等於 `初始值 + 3`，驗證韌體能正確處理 Vendor Command 的寫入請求；Case 02 確認在修改後，將 WWYY 值恢復為初始備份值寫入，讀回 Health Descriptor 的對應欄位必須精確等於 `初始備份值`，驗證韌體在多次 Vendor Command 操作下的狀態恢復機制與資料完整性，確保無殘留狀態或寫入失敗。

## Test Case (TC) Checkpoints
1. [Case01_Increment_WWYY_Check]：
   - 動作：透過 `pattern_get_device_descriptor` 初始化裝置資訊，接著呼叫 `pattern_get_health_descriptor` 讀取 Device Health Descriptor (IDN=0x03, Index=0x00)，從回應資料的 offset 5-6 (Big Endian) 提取 `wwyy_from_health_descriptor` 作為初始值 `wwyy_backup`。建立 `WWYY` 結構體，將其 `wwyy.value` 設定為 `wwyy_backup + 3`，並透過 `project_api.issue_C04F_to_set_wwyy` 發送 Vendor Command C04F 進行寫入。寫入完成後，再次呼叫 `pattern_get_health_descriptor` 讀取 Health Descriptor，提取新的 `wwyy_from_health_descriptor` 數值。
   - 預期結果：新讀取的 `wwyy_from_health_descriptor` 數值必須嚴格等於 `wwyy_backup + 3`。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表 Vendor Command C04F 未能正確更新 Health Descriptor 中的 WWYY 欄位。

2. [Case02_Recover_WWYY_Check]：
   - 動作：在 Case 01 的基礎上，建立新的 `WWYY` 結構體，將其 `wwyy.value` 設定為步驟 1 中儲存的 `wwyy_backup` 初始值。再次透過 `project_api.issue_C04F_to_set_wwyy` 發送 Vendor Command C04F 進行寫入。寫入完成後，第三次呼叫 `pattern_get_health_descriptor` 讀取 Health Descriptor，提取 `wwyy_from_health_descriptor` 數值。
   - 預期結果：新讀取的 `wwyy_from_health_descriptor` 數值必須嚴格等於 `wwyy_backup`。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體在恢復初始設定時未能正確覆寫 Health Descriptor 中的 WWYY 欄位，或存在狀態鎖定問題。