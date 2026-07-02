# Test Spec: UFS Firmware RAIN Recovery & Host Block UECC Handling Test

## Verification Criterion (VC)
驗證韌體在異常掉電（SPOR）後，針對「Temp RAIN VB」中注入的 UECC 錯誤是否會導致系統崩潰或恢復失敗，以及恢復後對 Host Block 中 UECC 錯誤的讀取行為是否符合預期：
1. **Temp RAIN VB UECC 處理**：在 Temp RAIN VB 的特定物理頁（Page）注入 UECC 錯誤後執行 HW_RESET。驗證韌體能否在無 SSU 保護下正常完成初始化並進入 Unit Ready 狀態，確認韌體對 Temp RAIN 結構的容錯機制。
2. **Host Block UECC 讀取行為**：在系統恢復後，針對 Host Block（LBA 0）注入 UECC 錯誤，並透過 `direct_read_raw_data` 進行原始資料讀取。驗證讀取狀態碼是否正確返回 `ReadStatus.UECC`，確認韌體在啟用 REH (Read Error Handling) 機制下，能正確識別並報告 Host 端的 UECC 錯誤，而非靜默修正或返回其他狀態。

## Test Case (TC) Checkpoints
1. [Temp_RAIN_VB_UECC_Injection_SPOR_Check]：
   - 動作：
     1. 針對 `TestNormalLun` 寫入 3 Pages 的 TLC 資料（總大小為 `max_plane * 16KB * 3`），記錄最後 LBA (`last_lba`)。
     2. 針對 `TestEM1Lun` 寫入 4KB SLC 資料，觸發 Temp RAIN VB 的建立。
     3. 透過 `get_specific_open_vb_cursor` 獲取 Temp RAIN VB 的游標資訊。
     4. 呼叫 `inject_UECC_in_Temp_Rain_VB`，遍歷該 VB 的所有 CE 與 Plane（排除無效 Plane 及超出範圍的 CE/Plane），在每個有效的物理頁（Page）注入 UECC 錯誤（`SLC_enable=True`）。
     5. 執行 `api.init_tester_to_unit_ready`，設定為 `HW_RESET` 且 `powerdown=False`（模擬 SPOR 情境）。
   - 預期結果：韌體成功完成 HW_RESET 流程並進入 Unit Ready 狀態，無 Hard Fault 或系統崩潰。這代表韌體在初始化階段能夠處理 Temp RAIN VB 中的 UECC 錯誤，可能透過忽略或標記該 VB 為無效來恢復系統。

2. [Host_Block_UECC_Read_Status_Check]：
   - 動作：
     1. 系統恢復後，針對 `TestNormalLun` 在 `last_lba + 1` 位置寫入 4KB 資料。
     2. 獲取 `TestNormalLun` 中 LBA 0 的 PCA (Physical Cell Address) 資訊。
     3. 呼叫 `inject_UECC` 在該 PCA 對應的物理頁注入 UECC 錯誤（`SLC_enable=False`，即 TLC 模式）。
     4. 呼叫 `direct_read_raw_data_and_check_status`，設定 `expect_status` 為 `project_api.ReadStatus.UECC`，並啟用 `REH_Enable=True`。
   - 預期結果：讀取操作返回的狀態碼必須精確等於 `project_api.ReadStatus.UECC`。這驗證了當 Host Block 發生 UECC 錯誤且啟用 REH 機制時，韌體不會嘗試自動修正（因為 UECC 通常不可修正），而是正確向上層報告 UECC 狀態，符合 UFS 規範中對不可修正錯誤的處理邏輯。