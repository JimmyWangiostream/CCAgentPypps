# Test Spec: UFS Firmware Parity Rebuild Verification for Multiple Test Modes

## Verification Criterion (VC)
驗證韌體在 HW_RESET (Spor) 後，針對不同測試模式（TLC, SLC, WB, L1, PTE, LOG）及特定 LUN 配置下的 PTE (Parity Table Entry) 狀態恢復機制：
1. **寫入前狀態控制**：確認在注入錯誤前，系統能正確根據 `TestMode` 切換 Write Booster 狀態，並針對 `TEST_LOG` 模式執行特定的 SSU Sleep/Active 電源循環以觸發邏輯層初始化，而其他模式則執行標準寫入。
2. **錯誤注入精確性**：確認透過 `inject_UECC` 函數，針對計算出的特定物理地址（Die 0, Plane 根據 invalid_plane_list 動態選擇, Block, Page）注入不可修復的 UECC 錯誤，且該地址對應的 LWP 屬於當前 Open VB 的 PTE 區域。
3. **硬體重置與韌體行為**：確認執行 `HW_RESET` 後，韌體是否觸發 Parity Rebuild 機制。
4. **最終狀態驗證**：透過 `direct_read_raw_data_and_check_status` 直接讀取原始資料，驗證在 `REH_Enable=True` 的情況下，讀取狀態是否嚴格等於 `ReadStatus.UECC`。此結果預期為 **UECC**，代表韌體在該特定測試路徑下，**未** 自動修復 PTE 中的 UECC 錯誤，或該錯誤被標記為未修復狀態，用於驗證 Parity Rebuild 機制在特定條件下（如特定 VB 狀態或模式）的邊界行為或預期失敗/保留狀態。

## Test Case (TC) Checkpoints
1. [Case01_TLC_SLC_WB_L1_PTE_Mode_UECC_Check]：
   - 動作：
     1. 針對 `TestMode` 為 `TEST_TLC`, `TEST_SLC`, `TEST_WB`, `TEST_L1`, `TEST_PTE` 的循環：
        - 若為 `TEST_WB`，設定 `WRITEBOOSTER_EN` Flag；否則清除該 Flag。
        - 執行 `reconfig_to_erase_all_lun` 清空 LUN。
        - 呼叫 `write_data_more_than_N_page` 寫入超過 2 頁的資料至對應 LUN，取得 `cursor` (包含 `logical_vb` 和 `first_empty_physical_page`)。
        - 呼叫 `issue_40C1_to_get_open_vb_information` 獲取當前 Open VB 資訊。
        - 呼叫 `get_invalid_plane_list` 獲取無效 Plane 列表。
        - 計算物理地址 `pca`：Die=0, Plane=1 (若 `invalid_plane_list[block]==0`) 或 0 (否則), Block=`cursor.logical_vb`, Page=`cursor.first_empty_physical_page`。
        - 呼叫 `inject_UECC(pca=pca, SLC_enable=...)` 在該物理地址注入 UECC 錯誤。
        - 呼叫 `api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET, powerdown=False)` 執行硬體重啟。
        - 呼叫 `direct_read_raw_data_and_check_status(pca=pca, SLC_enable=..., expect_status=ReadStatus.UECC, REH_Enable=True)` 直接讀取該物理地址的原始 Payload。
   - 預期結果：
     - `direct_read_raw_data_and_check_status` 回傳的狀態必須嚴格等於 `project_api.ReadStatus.UECC`。
     - 這表示在這些測試模式下，經過 HW_RESET 後，韌體並未將該 PTE LWP 的 UECC 錯誤修復為 Normal (0x00000000)，而是保留了 UECC 標記，驗證了 Parity Rebuild 機制在這些特定情境下未觸發自動修復或預期行為為保留錯誤標記。

2. [Case02_LOG_Mode_UECC_Check]：
   - 動作：
     1. 針對 `TestMode` 為 `TEST_LOG`：
        - 清除 `WRITEBOOSTER_EN` Flag。
        - 呼叫 `ssu_sleep_and_active()` 執行 SSU Sleep (Power Condition 0x02) 後 Active (Power Condition 0x01) 的電源循環流程。
        - 呼叫 `get_specific_open_vb_cursor(testMode)` 獲取 LOG 模式的特定 VB Cursor。
        - 呼叫 `issue_40C1_to_get_open_vb_information` 獲取當前 Open VB 資訊。
        - 呼叫 `get_invalid_plane_list` 獲取無效 Plane 列表。
        - 計算物理地址 `pca`：Die=0, Plane=1 (若 `invalid_plane_list[block]==0`) 或 0 (否則), Block=`cursor.logical_vb`, Page=`cursor.first_empty_physical_page`。
        - 呼叫 `inject_UECC(pca=pca, SLC_enable=True)` (LOG 模式通常對應 SLC 行為或特定配置，依 `get_general_parameter` 邏輯，此處 `SLC_en` 由 `testMode != TEST_TLC` 決定，故為 True) 在該物理地址注入 UECC 錯誤。
        - 呼叫 `api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET, powerdown=False)` 執行硬體重啟。
        - 呼叫 `direct_read_raw_data_and_check_status(pca=pca, SLC_enable=True, expect_status=ReadStatus.UECC, REH_Enable=True)` 直接讀取該物理地址的原始 Payload。
   - 預期結果：
     - `direct_read_raw_data_and_check_status` 回傳的狀態必須嚴格等於 `project_api.ReadStatus.UECC`。
     - 這表示在 LOG 模式並經過 SSU 電源循環後，韌體同樣未自動修復 PTE 中的 UECC 錯誤，驗證了該模式下的 Parity Rebuild 行為與 TLC/SLC 等其他模式一致，均保留 UECC 標記。