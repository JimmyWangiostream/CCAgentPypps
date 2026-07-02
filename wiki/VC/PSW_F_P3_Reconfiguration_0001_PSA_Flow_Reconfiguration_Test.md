# Test Spec: UFS LUN Reconfiguration & PSA State Machine Validation

## Verification Criterion (VC)
驗證 UFS 裝置在 Power Saving Area (PSA) 狀態機轉換過程中的 LUN 重配置（Reconfiguration）行為與錯誤處理機制：
1. **PSA State Transition & Locking**：驗證在 PSA State 從 OFF 轉換至 PRE_SOLDERING、LOADING_COMPLETE 及 SOLDERED 的過程中，`bConfigDescrLock` (Attribute 0x0B) 對 LUN 配置寫入的影響。特別是在 `SOLDERED` 狀態下，若 Erase Count (EC) > 30，強制拒絕 LUN 重配置並返回 `PARAM_ALREADY_WRITTEN` 錯誤碼。
2. **EC Threshold Enforcement**：驗證韌體內部邏輯嚴格執行 EC 閾值檢查。當 EC <= 30 時允許重配置；當 EC > 30 時，無論 PSA 狀態為何（除特定允許情境外），均應拒絕重配置。
3. **Health Report Warning Mapping**：驗證當 EC > 30 且 PSA State 為 OFF 時，Enhanced Health Report (0x40FE) 中的 `lun_reconfig_ec_warning` 欄位（偏移量 0x140）必須被硬體/韌體標記為 1，否則視為驗證失敗。
4. **Vendor Command Recovery**：驗證測試結束後，透過 Vendor Command (Write Parameter, Cmd Set 0x0F) 清除 PSA 狀態並恢復初始配置，確保測試環境乾淨。

## Test Case (TC) Checkpoints

1. [Case01_Unlock_EC_Low_Allow_Reconfig]：
   - 動作：
     1. 將 LUN0 配置為 Normal，LUN1 配置為 Enhanced_1，其餘禁用。
     2. 透過 Vendor Command 設定 VB Erase Count (EC) 為隨機值 0~30。
     3. 發送 VU D085 解鎖 LU Attribute Configuration，並寫入 Attribute 0x0B (`bConfigDescrLock`) 為 0x0 (UNLOCK)。
     4. 在 PSA State 為 OFF、PRE_SOLDERING、LOADING_COMPLETE 時，隨機分配 Normal/EM1 LUN 的 Allocation Units (AU) 比例並發送 Write Configuration Descriptor。
   - 預期結果：所有 PSA 狀態下的 Write Configuration Descriptor 均應成功返回 `QueryResponseCode.SUCCESS`。韌體應允許 LUN 資源重新分配。

2. [Case02_Lock_EC_Any_Reconfig_Fail]：
   - 動作：
     1. 設定 EC 為任意值 (0~30)。
     2. 發送 VU D085 解鎖後，寫入 Attribute 0x0B (`bConfigDescrLock`) 為 0x1 (LOCK)。
     3. 嘗試發送 Write Configuration Descriptor 進行 LUN 重配置。
   - 預期結果：Write Configuration Descriptor 應失敗，返回 `QueryResponseCode.GENERAL_FAILURE`。韌體應在硬體層面或韌體驅動層面攔截寫入請求，因為配置描述符被鎖定。

3. [Case03_EC_High_PSA_Off_Reconfig_Fail_With_Warning]：
   - 動作：
     1. 設定 EC 為隨機值 31~100。
     2. 確保 Attribute 0x0B 為 UNLOCK (0x0)。
     3. 將 PSA State 設為 OFF。
     4. 嘗試發送 Write Configuration Descriptor 進行 LUN 重配置。
     5. 發送 Vendor Command 0x40FE 讀取 Enhanced Health Report。
   - 預期結果：
     1. Write Configuration Descriptor 應失敗，返回 `QueryResponseCode.GENERAL_FAILURE`。
     2. Enhanced Health Report 中偏移量 0x140 處的 `lun_reconfig_ec_warning` 欄位數值必須嚴格等於 1。這代表韌體檢測到 EC 超過閾值並觸發了警告標記。

4. [Case04_EC_High_PSA_Soldered_Reconfig_Fail_With_Different_Code]：
   - 動作：
     1. 設定 EC 為隨機值 31~100。
     2. 確保 Attribute 0x0B 為 UNLOCK (0x0)。
     3. 將 PSA State 設為 SOLDERED。
     4. 嘗試發送 Write Configuration Descriptor 進行 LUN 重配置。
   - 預期結果：Write Configuration Descriptor 應失敗，返回 `QueryResponseCode.PARAM_ALREADY_WRITTEN`。這與 Case 03 的 `GENERAL_FAILURE` 不同，代表在 SOLDERED 狀態下，韌體將 EC 超限視為「配置已鎖定/不可變更」的特定錯誤碼，而非通用失敗。

5. [Case05_PSA_State_Transition_Interruption_Check]：
   - 動作：
     1. 在 PSA State 從 OFF 轉為 PRE_SOLDERING 的過程中（Loop 0），強制寫入 PSA State 為 OFF 以中斷流程。
     2. 在 PSA State 從 PRE_SOLDERING 轉為 LOADING_COMPLETE 的過程中（Loop 1），強制寫入 PSA State 為 OFF 以中斷流程。
     3. 完成所有狀態轉換後，執行 HW_RESET 硬體重啟。
     4. 在 SOLDERED 狀態下，對 LUN0 (PSA LUN) 寫入 16MB (BLOCK4K_SIZE_16M_BYTE) 的固定模式資料。
     5. 再次驗證 LUN 重配置行為。
   - 預期結果：
     1. 中斷操作不應導致裝置掛起或不可恢復錯誤。
     2. HW_RESET 後，裝置應正確進入 SOLDERED 狀態。
     3. 寫入 16MB 資料應成功，證明 PSA 區域在 SOLDERED 狀態下可正常進行大規模寫入操作。
     4. 最終的 LUN 重配置驗證應符合 Case 04 的邏輯（若 EC > 30 則返回 PARAM_ALREADY_WRITTEN）。

6. [Case06_Post_Process_Cleanup]：
   - 動作：
     1. 執行 `post_process`，透過 Vendor Command 寫入特定 Payload (Data[0]=0x04, Data[4]=0x01 等) 清除 PSA 狀態。
     2. 恢復備份的 VB Erase Count。
     3. 恢復備份的 Configuration Descriptors。
   - 預期結果：裝置應恢復到測試前的初始配置狀態，PSA 狀態應被清除，VB Erase Count 應與測試前一致，確保後續測試不受污染。