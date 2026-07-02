# Test Spec: UFS Device State Management & Secure Erase Protection Test

## Verification Criterion (VC)
驗證 UFS 裝置在進入「RAM 狀態 (Device State = 1)」後的行為保護機制與電源循環 (POR) 後的狀態恢復：Case 01 確認透過 Vendor Command (VU 40FC) 將裝置狀態設為 1 後，SRAM 暫存器 `0xF8F80800` 的 bit 38 與 FW 狀態均正確更新為 1；Case 02 確認在 Device State = 1 的保護狀態下，執行 Vendor Command C083 (設定 Erase Count) 時，韌體應拒絕該操作並回傳 SCSI CHECK CONDITION 狀態，Sense Data 必須為 ASC 0x24/ASCQ 0x00 (Illegal Request: Invalid Field in CDB)，證明寫入/擦除保護機制生效；Case 03 確認執行 HW_RESET 並觸發 SSU 電源循環後，裝置狀態必須完全重置，SRAM 暫存器 `0xF8F80800` 的 bit 38 與 FW 狀態均恢復為 0，代表裝置已回到初始就緒狀態。

## Test Case (TC) Checkpoints
1. [Case01_DeviceState_Set_Check]：
   - 動作：透過 `project_api.set_device_state` 發送 VU 40FC 命令，參數設定 `Device_state=1` 且 `only_in_ram=True`，僅修改 RAM 中的狀態暫存器。接著讀取 SRAM 位址 `0xF8F80800` 的 payload，提取第 38 個 byte (`payload[38]`) 作為 Device State 值；同時透過 `project_api.get_FW_states_in_RAM` 讀取韌體內部狀態。
   - 預期結果：SRAM `0xF8F80800` 的 bit 38 數值必須等於 1；韌體內部 Device State 數值必須等於 1。若任一數值不等於 1，則判定為狀態設定失敗。

2. [Case02_SecureErase_Protection_Check]：
   - 動作：在 Device State 維持為 1 的狀態下，發送 Vendor Command C083。參數設定 `VB_Num=CHANGE_THE_EC_ONLY_IN_RAM`，`Parameter0=SET_EC_TABLE`，`RC_TH_Value=0`，並載入 4KB 的 `data_payload`。檢查命令回應的 UPIU 結構。
   - 預期結果：回應必須為失敗狀態。具體檢查條件如下：
     - `response.upiu.b6_response` 必須等於 `TARGET_FAILURE`。
     - `response.upiu.b7_status` 必須等於 `CHECK_CONDITION`。
     - Sense Data 中的 `b12_asc` 必須等於 `0x24`。
     - Sense Data 中的 `b13_ascq` 必須等於 `0x0`。
     此結果證明在 Device State = 1 時，韌體強制阻斷了 Erase Count 的寫入操作，並正確回傳 "Invalid Field in CDB" 錯誤碼。

3. [Case03_POR_State_Reset_Check]：
   - 動作：執行 `api.init_tester_to_unit_ready`，設定 `Dcmd5ResetType.HW_RESET` 並開啟 `powerdown=True`，觸發帶有 SSU (Secure Storage Unit) 的硬體重置與電源循環。待裝置重新上線後，再次讀取 SRAM 位址 `0xF8F80800` 的 payload，提取第 38 個 byte；並讀取韌體內部狀態。
   - 預期結果：SRAM `0xF8F80800` 的 bit 38 數值必須等於 0；韌體內部 Device State 數值必須等於 0。這代表 HW_RESET 與 SSU 流程成功清除了 RAM 中的異常狀態標記，裝置恢復至預設的 Normal/Ready 狀態。