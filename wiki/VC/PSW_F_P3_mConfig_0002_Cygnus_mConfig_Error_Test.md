# Test Spec: UFS FFU mConfig/pConfig Integrity & OTP Validation Test

## Verification Criterion (VC)
驗證 UFS 裝置在 FFU (Firmware Update) 及 Vendor Command (C056) 情境下，韌體對 mConfig 與 pConfig 資料完整性檢查（Integrity Check）及 OTP (One-Time Programmable) 值比對機制的嚴格性：
1. **FFU Bin 注入錯誤 OTP**：確認當 FW_HW_BIN 中 mConfig 或 pConfig 的 OTP 欄位與裝置實際 OTP 不符時，韌體拒絕寫入並維持原狀，且 DEVICE_FFU_STATUS 寄存器回報 `MICROCODE_VERSION_MISMATCH`。
2. **Vendor Command (C056) 注入錯誤 OTP**：確認透過 Host 發送 Set mConfig/pConfig Data 命令時，若 OTP 值錯誤，裝置必須回報 `TARGET_FAILURE` 與 `CHECK_CONDITION` SCSI Status，且韌體內部配置不被修改。
3. **不可變欄位（File Signature）保護**：確認嘗試修改 mConfig/pConfig 中的 "MCONFIG"/"PCONFIG" 簽名字串（位於 Payload 偏移 0x00 或 Bin 偏移特定位置）時，無論透過 FFU Write Buffer 還是 Vendor Command，裝置均會拒絕執行並回報錯誤。
4. **恢復機制**：確認在錯誤操作後，透過 `HW_RESET` 或 `RESET_N` 初始化，以及後續的 `recover()` 流程，能確保 mConfig/pConfig 資料恢復至預期的備份狀態（Backup State）。

## Test Case (TC) Checkpoints

1. **[TC01_FFU_Wrong_mConfig_OTP_Check]**：
   - 動作：載入當前 FW_HW_BIN，在 `mConfig_in_FW_HW_BIN_offset` (0x5000) + 8 + offset 處注入隨機錯誤 OTP 值 (`error_value`)，並重新簽章 Bin。透過 `send_FFU_and_check_response` (error_case=False) 發送 FFU 寫入指令。隨後執行 `HW_RESET` 或 `RESET_N` 初始化裝置。讀取 `DEVICE_FFU_STATUS` 屬性。
   - 預期結果：FFU 寫入指令應成功發送（無 DLL 層錯誤），但韌體應拒絕應用更新。讀回的 `DEVICE_FFU_STATUS` 必須等於 `MICROCODE_VERSION_MISMATCH` (值為 4)。確認 mConfig/pConfig 資料未發生改變。

2. **[TC02_FFU_Wrong_pConfig_OTP_Check]**：
   - 動作：載入當前 FW_HW_BIN，在 `pConfig_in_FW_HW_BIN_offset` (0x5400) + 8 + offset 處注入隨機錯誤 OTP 值 (`error_value`)，並重新簽章 Bin。透過 `send_FFU_and_check_response` (error_case=False) 發送 FFU 寫入指令。隨後執行 `HW_RESET` 或 `RESET_N` 初始化裝置。讀取 `DEVICE_FFU_STATUS` 屬性。
   - 預期結果：FFU 寫入指令應成功發送，但韌體應拒絕應用更新。讀回的 `DEVICE_FFU_STATUS` 必須等於 `MICROCODE_VERSION_MISMATCH` (值為 4)。確認 mConfig/pConfig 資料未發生改變。

3. **[TC03_VendorCmd_Wrong_mConfig_OTP_Check]**：
   - 動作：建立 temp_mConfig 物件，將其 `OTP_value` 修改為錯誤值（從 [145, 146, 147, 148] 中隨機選擇一個非當前 OTP 的值）。透過 `set_mConfig_pConfig_data_and_check_resp` (error_case=True) 發送 Set mConfig Data Vendor Command。
   - 預期結果：裝置必須回報 `UPIUResponse.TARGET_FAILURE` 且 SCSI Status 為 `CHECK_CONDITION`。韌體內部 mConfig 資料不得被修改。

4. **[TC04_VendorCmd_Wrong_pConfig_OTP_Check]**：
   - 動作：建立 temp_pConfig 物件，將其 `OTP_value` 修改為錯誤值（從 [145, 146, 147, 148] 中隨機選擇一個非當前 OTP 的值）。透過 `set_mConfig_pConfig_data_and_check_resp` (error_case=True) 發送 Set pConfig Data Vendor Command。
   - 預期結果：裝置必須回報 `UPIUResponse.TARGET_FAILURE` 且 SCSI Status 為 `CHECK_CONDITION`。韌體內部 pConfig 資料不得被修改。

5. **[TC05_VendorCmd_C056_Option_3_Check]**：
   - 動作：透過 Vendor Command C056 發送 Set mConfig Data，Payload 長度 4096 Bytes，並設定 Set Option 為 `0x03`。透過 `set_mConfig_pConfig_data_and_check_resp` (error_case=True) 執行。
   - 預期結果：裝置必須回報 `UPIUResponse.TARGET_FAILURE` 且 SCSI Status 為 `CHECK_CONDITION`。此測試驗證特定 Set Option 值在當前 OTP 或配置狀態下是否被視為非法操作。

6. **[TC06_VendorCmd_C056_Option_0xFF_Check]**：
   - 動作：透過 Vendor Command C056 發送 Set mConfig Data，Payload 長度 4096 Bytes，並設定 Set Option 為 `0xFF`。透過 `set_mConfig_pConfig_data_and_check_resp` (error_case=True) 執行。
   - 預期結果：裝置必須回報 `UPIUResponse.TARGET_FAILURE` 且 SCSI Status 為 `CHECK_CONDITION`。驗證 0xFF 作為 Set Option 時是否觸發驗證失敗。

7. **[TC07_FFU_Modify_mConfig_Signature_Check]**：
   - 動作：載入當前 FW_HW_BIN，在 `mConfig_in_FW_HW_BIN_offset` (0x5000) + offset 處（即 mConfig Payload 起始位置，File Signature 欄位）注入隨機錯誤值 (`error_value`)，覆蓋原本的 "MCONFIG" 字串。重新簽章 Bin。透過 `send_FFU_and_check_response` (error_case=True) 發送 FFU 寫入指令。
   - 預期結果：由於 File Signature 不匹配，韌體應在寫入階段或驗證階段拒絕。Host 端應收到 `UPIUResponse.TARGET_FAILURE` 與 `CHECK_CONDITION` 回應。Bin 資料未寫入裝置。

8. **[TC08_FFU_Modify_pConfig_Signature_Check]**：
   - 動作：載入當前 FW_HW_BIN，在 `pConfig_in_FW_HW_BIN_offset` (0x5400) + offset 處（即 pConfig Payload 起始位置，File Signature 欄位）注入隨機錯誤值 (`error_value`)，覆蓋原本的 "PCONFIG" 字串。重新簽章 Bin。透過 `send_FFU_and_check_response` (error_case=True) 發送 FFU 寫入指令。
   - 預期結果：由於 File Signature 不匹配，韌體應拒絕。Host 端應收到 `UPIUResponse.TARGET_FAILURE` 與 `CHECK_CONDITION` 回應。Bin 資料未寫入裝置。

9. **[TC09_FFU_Modify_Both_Signatures_Check]**：
   - 動作：載入當前 FW_HW_BIN，同時在 mConfig 和 pConfig 的 Signature 欄位（偏移 0x00 處）分別注入 `error_value` 和 `error_value2`。重新簽章 Bin。透過 `send_FFU_and_check_response` (error_case=True) 發送 FFU 寫入指令。
   - 預期結果：由於雙重 Signature 不匹配，韌體應拒絕。Host 端應收到 `UPIUResponse.TARGET_FAILURE` 與 `CHECK_CONDITION` 回應。

10. **[TC10_VendorCmd_Modify_mConfig_Signature_Check]**：
    - 動作：建立 temp_mConfig 物件，將其 `Name_1` 欄位（對應 File Signature "MCONFIG"）修改為隨機錯誤值 (`error_value`)。透過 `set_mConfig_pConfig_data_and_check_resp` (error_case=True) 發送 Set mConfig Data Vendor Command。
    - 預期結果：裝置必須回報 `UPIUResponse.TARGET_FAILURE` 且 SCSI Status 為 `CHECK_CONDITION`。韌體內部 mConfig 資料不得被修改。

11. **[TC11_VendorCmd_Modify_pConfig_Signature_Check]**：
    - 動作：建立 temp_pConfig 物件，將其 `Name_1` 欄位（對應 File Signature "PCONFIG"）修改為隨機錯誤值 (`error_value`)。透過 `set_mConfig_pConfig_data_and_check_resp` (error_case=True) 發送 Set pConfig Data Vendor Command。
    - 預期結果：裝置必須回報 `UPIUResponse.TARGET_FAILURE` 且 SCSI Status 為 `CHECK_CONDITION`。韌體內部 pConfig 資料不得被修改。

12. **[TC12_Recovery_Verification_Check]**：
    - 動作：在完成上述任一錯誤測試案例後，執行 `api.init_tester_to_unit_ready` (使用 HW_RESET 或 RESET_N)。讀取當前 mConfig 與 pConfig 資料。執行 `hw_setting.recover()` 恢復硬體設定，並透過 `project_api.set_mConfig_data` 和 `set_pConfig_data` 寫入預期的備份資料 (`mConfig_in_vu_bkup`, `pConfig_in_vu_bkup`)。再次執行 `api.init_tester_to_unit_ready`。最後讀取 mConfig 與 pConfig 資料並與備份資料進行 `compare_mConfig_data` 和 `compare_pConfig_data` 比對。
    - 預期結果：韌體應能正確恢復至備份狀態。讀回的 mConfig 與 pConfig 資料必須與備份資料完全一致，證明錯誤操作未造成永久性損壞，且恢復機制有效。