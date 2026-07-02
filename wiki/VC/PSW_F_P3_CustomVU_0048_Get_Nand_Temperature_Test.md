# Test Spec: UFS Vendor Command D08A NAND Temperature Control Validation

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command D08A 設定 NAND 溫度閾值（Threshold）的硬體行為與韌體響應機制：Case 01 確認在有效範圍內（20°C + 37°C offset）設定溫度時，韌體能正確更新內部狀態並透過 Command 4021 回傳正確的計算後溫度值；Case 02 確認當設定值超過上限（126°C）時，韌體應拒絕該請求並拋出 DLL_RESPONSE_ERROR 異常；Case 03 確認當設定值低於下限（-38°C）時，韌體同樣應拒絕請求並拋出異常；Case 04 為恢復步驟，確認透過關閉 `bEnableSetVuTemp` 標誌可重置或停用該虛擬溫度設定功能，確保測試環境乾淨。

## Test Case (TC) Checkpoints
1. [Case01_Valid_Temp_Set_Check]：
   - 動作：透過 `get_flash_setting()` 獲取 CE 數量（`ce_num`），初始化 `SetNandTemperature` 結構體，設定 `bEnableSetVuTemp = 1`，`Use_Delayed_fake_tmeperatures = 0`，並將 `NAND_TEMPERATURE_DIE_0` 至 `NAND_TEMPERATURE_DIE_3`（依 `ce_num` 動態設定）的值設為 20。執行 `project_api.issue_D08A_set_vu_temperature` 發送 Vendor Command D08A。隨後執行 `project_api.issue_4021_get_nand_temperature` 讀取當前 NAND 溫度。
   - 預期結果：D08A 命令執行成功無異常；讀回的 `GetNandTemperature.temperature_of_die_0.value`（以及對應 CE 的 die 溫度）必須嚴格等於 `20 + 37 = 57`。這代表韌體在接收 D08A 後，正確將設定的基礎溫度與內部偏移量（37）相加，並更新至內部溫度監控結構體中。

2. [Case02_Over_Threshold_Error_Check]：
   - 動作：初始化 `SetNandTemperature` 結構體，設定 `bEnableSetVuTemp = 1`，`Use_Delayed_fake_tmeperatures = 0`，並將所有 DIE 溫度值設為 126（超過硬體定義的上限閾值）。執行 `project_api.issue_D08A_set_vu_temperature` 發送 Vendor Command D08A，並捕獲可能拋出的 `DLL_RESPONSE_ERROR` 異常。
   - 預期結果：必須觸發 `DLL_RESPONSE_ERROR` 異常（`rsp_fail` 為 True），代表韌體在接收 D08A 時進行了邊界檢查，拒絕了超出合法範圍（>126）的溫度設定請求，防止硬體過熱或邏輯錯誤。

3. [Case03_Under_Threshold_Error_Check]：
   - 動作：初始化 `SetNandTemperature` 結構體，設定 `bEnableSetVuTemp = 1`，`Use_Delayed_fake_tmeperatures = 0`。將溫度值設為 -38，並透過 `temp.to_bytes(2, byteorder='little', signed=True)` 轉換為 Little-Endian 的 payload 格式，賦值給 `NAND_TEMPERATURE_DIE_0` 至 `NAND_TEMPERATURE_DIE_3`。執行 `project_api.issue_D08A_set_vu_temperature` 發送 Vendor Command D08A，並捕獲可能拋出的 `DLL_RESPONSE_ERROR` 異常。
   - 預期結果：必須觸發 `DLL_RESPONSE_ERROR` 異常（`rsp_fail` 為 True），代表韌體在接收 D08A 時進行了邊界檢查，拒絕了低於合法範圍（<-38）的溫度設定請求，確保溫度監控邏輯的完整性。

4. [Case04_Disable_VuTemp_Recovery_Check]：
   - 動作：初始化 `SetNandTemperature` 結構體，將 `bEnableSetVuTemp` 設為 0，`Use_Delayed_fake_tmeperatures` 設為 0。執行 `project_api.issue_D08A_set_vu_temperature` 發送 Vendor Command D08A。
   - 預期結果：命令執行成功無異常。此步驟用於驗證當 `bEnableSetVuTemp` 為 0 時，韌體不會應用虛擬溫度設定，從而恢復系統至預設或關閉虛擬溫度監控的狀態，確保後續測試不受殘留狀態影響。