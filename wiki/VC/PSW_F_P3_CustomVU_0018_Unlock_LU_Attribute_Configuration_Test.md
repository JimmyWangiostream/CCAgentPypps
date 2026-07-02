# Test Spec: UFS Configuration Descriptor Lock Mechanism & Vendor Unlock Validation

## Verification Criterion (VC)
驗證 UFS 裝置中 Configuration Descriptor 的鎖定機制（Lock/Unlock）及其對屬性寫入與描述符更新的保護行為：
1. **初始狀態驗證**：確認預設狀態下 `bConfigDescrLock` 為 0x0（未鎖定），且允許正常寫入配置描述符。
2. **重複寫入保護**：驗證在鎖定狀態不變的情況下，重複寫入相同的 `bConfigDescrLock` 值（0x0 或 0x1）時，Host 應收到 `PARAM_ALREADY_WRITTEN` 回應碼，而非 `SUCCESS`。
3. **鎖定後寫入阻斷**：驗證當 `bConfigDescrLock` 設為 0x1（鎖定）後，嘗試寫入 `bConfigDescrLock` 為 0x0（解鎖）應被拒絕（返回 `PARAM_ALREADY_WRITTEN` 或 `GENERAL_FAILURE`），且嘗試更新 Configuration Descriptor 應返回 `GENERAL_FAILURE` 或 `PARAM_ALREADY_WRITTEN`，證明硬體/韌體已阻斷配置變更。
4. **Vendor Command 解鎖機制**：驗證透過 Vendor Command `0xD085` 強制解鎖 LU Attribute Configuration 後，`bConfigDescrLock` 恢復為 0x0，且後續的配置描述符寫入操作應恢復為 `SUCCESS`，證明 Vendor Command 能有效繞過硬體鎖定狀態。

## Test Case (TC) Checkpoints
1. [Initial_Unlocked_State_Check]：
   - 動作：透過 `ReadAttribute` 讀取 `idn=CONFIG_DESCR_LOCK` (0x0B) 的值，確認初始狀態。
   - 預期結果：讀回的值必須等於 `0x0`，代表 Configuration Descriptor 處於未鎖定狀態，允許後續的配置修改。

2. [Config_Write_Success_Check]：
   - 動作：獲取當前 Configuration Descriptor，設定 `b17_write_booster_buffer_type=1`、`b16_write_booster_buffer_preserve_user_space_en=1`、`l18_num_shared_write_booster_buffer_alloc_units=0x1000`，並透過 `WriteDescriptor` 寫入 index=0。
   - 預期結果：`ExecuteCMD.send()` 執行後應無異常，代表在未鎖定狀態下，配置描述符的寫入操作成功。

3. [Write_Lock_Attribute_0x0_AlreadyWritten_Check]：
   - 動作：透過 `WriteAttribute` 寫入 `idn=CONFIG_DESCR_LOCK` 值為 `0x0`（保持未鎖定），並呼叫 `check_already_written` 函數。該函數會嘗試寫入並捕獲 `DLL_RESPONSE_ERROR`，隨後讀取回應碼。
   - 預期結果：回應碼 `b6_query_response` 必須等於 `QueryResponseCode.PARAM_ALREADY_WRITTEN`，證明當屬性值與當前狀態一致時，裝置返回特定錯誤碼而非成功。

4. [Read_Lock_Attribute_0x0_Verification]：
   - 動作：再次透過 `ReadAttribute` 讀取 `idn=CONFIG_DESCR_LOCK`。
   - 預期結果：讀回的值必須等於 `0x0`，確認屬性狀態未發生非預期改變。

5. [Write_Lock_Attribute_0x0_Redundant_Check]：
   - 動作：再次呼叫 `check_already_written` 寫入 `idn=CONFIG_DESCR_LOCK` 值為 `0x0`。
   - 預期結果：回應碼必須等於 `QueryResponseCode.PARAM_ALREADY_WRITTEN`，進一步驗證重複寫入相同值的保護機制。

6. [Config_Write_Redundant_Success_Check]：
   - 動作：再次執行與步驟 2 相同的 Configuration Descriptor 寫入操作（包含 Write Booster 參數設定）。
   - 預期結果：寫入操作應成功（無異常），證明在未鎖定狀態下，即使配置內容未變，寫入指令仍被接受並執行（或視為無效但成功）。

7. [Vendor_Unlock_0xD085_Issue]：
   - 動作：呼叫 `project_api.issue_D085_unlock_LU_attribute_configuration()` 發送 Vendor Command `0xD085`。
   - 預期結果：此步驟應成功執行，作為後續解鎖狀態的觸發點。

8. [Post_Unlock_Attribute_Read_Check]：
   - 動作：透過 `ReadAttribute` 讀取 `idn=CONFIG_DESCR_LOCK`。
   - 預期結果：讀回的值必須等於 `0x0`，確認 Vendor Command 已將鎖定位元重置為未鎖定狀態。

9. [Post_Unlock_Config_Write_Success_Check]：
   - 動作：再次執行 Configuration Descriptor 寫入操作。
   - 預期結果：寫入操作應成功，證明解鎖後配置寫入功能完全恢復。

10. [Lock_Attribute_0x1_Set_Check]：
    - 動作：透過 `WriteAttribute` 寫入 `idn=CONFIG_DESCR_LOCK` 值為 `0x1`（鎖定）。
    - 預期結果：寫入操作應成功，狀態切換為鎖定。

11. [Read_Lock_Attribute_0x1_Verification]：
    - 動作：透過 `ReadAttribute` 讀取 `idn=CONFIG_DESCR_LOCK`。
    - 預期結果：讀回的值必須等於 `0x1`，確認硬體狀態已正確更新為鎖定。

12. [Write_Lock_Attribute_0x0_Rejected_Check]：
    - 動作：呼叫 `check_already_written` 嘗試寫入 `idn=CONFIG_DESCR_LOCK` 值為 `0x0`（試圖解鎖）。
    - 預期結果：回應碼必須等於 `QueryResponseCode.PARAM_ALREADY_WRITTEN`（或 `GENERAL_FAILURE`，視實作而定，但腳本預期為 `PARAM_ALREADY_WRITTEN` 或 `GENERAL_FAILURE` 均視為合法阻斷），證明在鎖定狀態下無法透過標準 WriteAttribute 指令將狀態改回 0x0。

13. [Config_Write_Locked_Rejection_Check]：
    - 動作：嘗試寫入 Configuration Descriptor（index=0），並捕獲回應碼。
    - 預期結果：回應碼 `b6_query_response` 必須等於 `QueryResponseCode.GENERAL_FAILURE` 或 `QueryResponseCode.PARAM_ALREADY_WRITTEN`。這證明在 `bConfigDescrLock=0x1` 時，硬體/韌體阻斷了對 Configuration Descriptor 的寫入，確保配置不被非法修改。

14. [Vendor_Unlock_0xD085_Second_Issue]：
    - 動作：再次呼叫 `project_api.issue_D085_unlock_LU_attribute_configuration()` 發送 Vendor Command `0xD085`。
    - 預期結果：此步驟應成功執行，作為恢復寫入權限的觸發點。

15. [Post_Unlock_Attribute_Read_Check_2]：
    - 動作：透過 `ReadAttribute` 讀取 `idn=CONFIG_DESCR_LOCK`。
    - 預期結果：讀回的值必須等於 `0x0`，確認 Vendor Command 再次成功將鎖定位元重置為未鎖定狀態。

16. [Final_Config_Write_Success_Check]：
    - 動作：再次執行 Configuration Descriptor 寫入操作。
    - 預期結果：寫入操作應成功，證明經過 Vendor Command 解鎖後，配置寫入功能完全恢復，測試流程結束。