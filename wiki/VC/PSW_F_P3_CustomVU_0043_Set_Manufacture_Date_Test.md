# Test Spec: C04E Vendor Command Manufacture Date Modification and Recovery Test

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command (C04E) 修改製造日期 (Manufacture Date) 的韌體行為與資料持久性：Case 01 確認在正常情境下，透過 C04E 將製造日期增加 3 個單位後，Device Descriptor 中的 `w18_manufacturer_date` 欄位必須正確更新為新值，證明 Vendor Command 寫入機制運作正常；Case 02 為恢復流程，確認將製造日期重置回原始值後，Device Descriptor 中的 `w18_manufacturer_date` 欄位必須恢復為原始值，證明韌體能正確處理逆向修改並維持資料一致性，無殘留錯誤狀態。

## Test Case (TC) Checkpoints
1. [Case01_Increment_Manufacture_Date_Check]：
   - 動作：首先透過 `pattern_get_device_descriptor` 讀取 Device Descriptor，擷取原始製造日期 `device_manufacture_date` (對應 Descriptor 偏移量 0x18 的 `w18_manufacturer_date`)。接著建立 `ManufactureDate` 結構體，將目標值設定為 `原始值 + 3`。呼叫 `project_api.issue_C04E_to_set_manufacture_date` 發送 Vendor Command 執行寫入。寫入完成後，再次呼叫 `pattern_get_device_descriptor` 讀取 Device Descriptor，並解析 `w18_manufacturer_date` 欄位。將讀回的值與預期值 (原始值 + 3) 進行比對，預期值需透過 `to_bytes(length=2, byteorder='big')` 轉換為整數以確保位元組序一致。
   - 預期結果：讀回的 `w18_manufacturer_date` 數值必須嚴格等於 `原始值 + 3`。若不相等，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。此結果驗證 Vendor Command C04E 能成功修改非易失性記憶體中的製造日期欄位，且韌體讀取邏輯正確解析 Big-Endian 格式。

2. [Case02_Recover_Original_Manufacture_Date_Check]：
   - 動作：在 Case 01 的基礎上，建立新的 `ManufactureDate` 結構體，將目標值設定為 `device_manufacture_date_backup` (即 Case 01 執行前的原始製造日期)。再次呼叫 `project_api.issue_C04E_to_set_manufacture_date` 發送 Vendor Command 執行寫入。寫入完成後，第三次呼叫 `pattern_get_device_descriptor` 讀取 Device Descriptor，並解析 `w18_manufacturer_date` 欄位。將讀回的值與原始值進行比對，預期值需透過相同的位元組序轉換邏輯計算。
   - 預期結果：讀回的 `w18_manufacturer_date` 數值必須嚴格等於 `device_manufacture_date_backup`。若不相等，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。此結果驗證韌體在經歷一次修改後，能正確接受並應用恢復指令，確保製造日期欄位可逆且資料狀態與預期完全一致，無資料損毀或鎖定現象。