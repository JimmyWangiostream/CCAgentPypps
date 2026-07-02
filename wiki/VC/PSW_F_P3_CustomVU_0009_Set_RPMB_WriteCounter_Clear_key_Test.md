# Test Spec: UFS RPMB Multi-Region Write Counter & Key Lifecycle Test

## Verification Criterion (VC)
驗證 UFS 裝置在支援多個 RPMB (Replay Protected Memory Block) 區域（Region 0-3）的情境下，韌體對 RPMB 金鑰管理與寫入計數器（Write Counter）的處理邏輯：
1. **配置階段**：確認透過 Vendor Command 或 API 寫入 Configuration Descriptor 時，`b12_rpmb_region_enable` 欄位能正確啟用指定的 RPMB 區域（本測試設定為全部 4 個區域），且各區域大小設定正確。
2. **金鑰清除與重設**：確認針對每個 RPMB 區域執行 `D079_Clear_RPMB_Key` 後，該區域的 RPMB 金鑰被清除，導致後續讀取計數器時觸發 `SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常，並能透過 `rpmb_key_programming()` 成功重新程式化金鑰。
3. **寫入計數器設定與驗證**：確認透過 `D078` Vendor Command 設定隨機寫入計數器（Write Counter）後，韌體能正確儲存該值，且透過 `rpmb_read_counter()` 讀回的值必須與設定值完全一致（Bit-for-Bit Match）。
4. **最終狀態一致性**：確認在所有區域的金鑰被再次清除後，讀回之寫入計數器必須為 `0x00000000`，驗證金鑰清除操作是否同時重置了計數器狀態（或確認計數器在無金鑰狀態下讀取行為符合規範）。

## Test Case (TC) Checkpoints
1. [Config_Desc_RPMB_Region_Enable_Check]：
   - 動作：呼叫 `api.get_config_descriptors()` 取得當前配置，建立 `ConfigDescriptor310` 物件，設定 `b2_conf_desc_continue = DISABLE`，並根據 `config_region_num` (設為 4) 設定 `b12_rpmb_region_enable` 為 `REGION_0_ENABLE | REGION_1_ENABLE | REGION_2_ENABLE | REGION_3_ENABLE`。同時設定 `b13_rpmb_region1_size` 至 `b15_rpmb_region3_size` 均為 1。透過 `ExecuteCMD.WriteDescriptor` 發送 `DescriptorIDN.CONFIGURATION` 寫入命令，隨後再次讀取配置描述符並記錄 Header 與 Unit 資訊。
   - 預期結果：裝置應接受配置寫入；讀回之 `b12_rpmb_region_enable` 欄位數值必須包含所有 4 個區域的 Enable 位元；`b13` 至 `b15` 的區域大小欄位必須為 1；Logger 應輸出正確的 Descriptor Header 與 Unit 結構資訊，確認硬體配置已更新。

2. [RPMB_Key_Clear_and_Reprogram_Check]：
   - 動作：針對 Region 0 至 Region 3 依序執行以下流程：
     1. 呼叫 `project_api.issue_D079_Clear_RPMB_Key(region=index)` 清除該區域金鑰。
     2. 建立 `RPMB` 物件並嘗試呼叫 `rpmb.rpmb_read_counter()`。
     3. 捕獲 `SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常，確認金鑰已清除。
     4. 呼叫 `rpmb.rpmb_key_programming()` 重新程式化金鑰。
   - 預期結果：在步驟 2 中，讀取計數器操作必須拋出 `SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常，證明金鑰清除機制生效；在步驟 4 後，金鑰應成功寫入，為後續計數器設定做準備。

3. [RPMB_WriteCounter_Set_and_Verify_Check]：
   - 動作：針對 Region 0 至 Region 3 依序執行：
     1. 產生一個隨機 32 位元整數 `set_writecounter` (範圍 0x00000001 至 0xFFFFFFFF)。
     2. 呼叫 `project_api.issue_D078_to_set_RPMB_WriteCounter(write_counter=set_writecounter, region=index)` 發送 Vendor Command 設定計數器。
     3. 呼叫 `rpmb.rpmb_read_counter()` 讀取當前計數器值。
     4. 比對讀回值與 `set_writecounter`。
   - 預期結果：讀回之 `write_counter` 數值必須嚴格等於 `set_writecounter`。若不相等，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此步驟驗證 Vendor Command D078 能正確更新硬體內的 RPMB Write Counter 暫存器。

4. [RPMB_Final_Key_Clear_and_Zero_Check]：
   - 動作：針對 Region 0 至 Region 3 依序執行：
     1. 呼叫 `project_api.issue_D079_Clear_RPMB_Key(region=index)` 清除金鑰。
     2. 嘗試 `rpmb.rpmb_read_counter()` 並捕獲異常後，呼叫 `rpmb.rpmb_key_programming()` 重新程式化金鑰。
     3. 再次呼叫 `rpmb.rpmb_read_counter()` 讀取計數器。
     4. 檢查讀回值是否等於 0。
   - 預期結果：讀回之 `write_counter` 數值必須等於 `0x00000000`。若不等於 0，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此步驟驗證在金鑰被清除並重新程式化後，RPMB 的寫入計數器是否被硬體或韌體重置為零，確保測試環境的初始狀態一致性。