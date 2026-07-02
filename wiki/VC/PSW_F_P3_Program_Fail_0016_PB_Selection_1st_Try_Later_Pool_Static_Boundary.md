# Test Spec: VC-40 (14.h) Program Fail on L2 VB Boundary with FW Assert 0x203 Verification

## Verification Criterion (VC)
驗證韌體在 L2 VB (Logical VB) 邊界情境下的錯誤處理機制：
1. **預處理階段**：確認透過 VU 40C1/40DC 獲取當前 L2 VB 與 Next L2 VB，並透過 VU 405E 記錄初始 Bad Block (BB) 計數。透過 VU 40D6 確認剩餘替換區塊數量，並針對 Next L2 VB 注入 Erase Fail (EF) 以強制其進入 Bad Block 狀態。隨後執行連續寫入直到 L2 VB 切換，驗證 BB Table (BBT) 正確更新（BB 計數 +1 且目標區塊被標記）。
2. **主測試階段**：在 L2 VB 即將寫滿（First Empty Physical Page 接近邊界 3308）時，針對該 L2 VB 的特定 Logical Page 注入 Program Fail (PF, fail_type=3)。
3. **核心驗證**：觸發寫入後，預期裝置進入非響應狀態並觸發韌體 Assert。必須嚴格比對韌體 Assert 編號為 `0x203`，代表裝置在發生 Program Fail 後進入初始化掛起狀態，且**未**進入 Read-Only 模式（與一般嚴重錯誤進入 RO 模式不同）。

## Test Case (TC) Checkpoints

1. [PreProcess_BBTable_Update_Check]：
   - 動作：
     1. 透過 `issue_40C1_to_get_open_vb_information` 獲取當前 `L2_vb`，透過 `issue_40DC_to_get_next_open_vb_information` 獲取 `L2_vb_next`。
     2. 透過 `issue_405E_to_get_bad_block_information` 記錄初始 `BB_count`。
     3. 透過 `issue_40D6_to_get_predicted_next_n_replacement_block` 確認替換池狀態，若剩餘替換區塊大於 1 則繼續循環。
     4. 使用 `issue_C012_to_create_program_erase_fail` (fail_type=1) 針對 `L2_vb_next` 的 Block 0, Page 0 注入 Erase Fail。
     5. 執行連續 Write10 (LBA 0, 長度 WRITE_10_MAX_BLOCK_LEN) 直到 `issue_40C1` 回傳的 `L2_vb_new` 不等於初始 `L2_vb`，表示 L2 VB 已切換。
     6. 再次透過 `issue_405E` 獲取新 BB 資訊，並透過 `calculate_bbt` 解析 BB Table。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - `BB_data_new` 中必須包含目標區塊資訊 (`target_data_L2`，即 CE=0, Plane=0, Block=L2_vb_next)，代表該區塊已被正確標記為 Bad Block 並加入替換池。

2. [Boundary_Program_Fail_Assert_0x203_Check]：
   - 動作：
     1. 進入邊界檢查循環，透過 `get_open_vb_info` 獲取 `open_vb`，計算 `physical_page` 對應的 `logical_page`。
        - 若 `physical_page < 1620`，`logical_page = physical_page // 3`。
        - 若 `1620 <= physical_page < 1652`，`logical_page = (physical_page - 1620) // 2 + 540`。
        - 若 `1652 <= physical_page < 3308`，`logical_page = (physical_page - 1652) // 3 + 1096` (540+556)。
        - 若 `physical_page >= 3308` 則跳出循環（此測試需在此邊界前觸發）。
     2. 針對計算出的 `logical_VB` 與 `logical_page`，使用 `issue_C012_to_create_program_erase_fail` (fail_type=3) 注入 Program Fail。
     3. 執行 Write10 (LBA 0, 長度 WRITE_10_MAX_BLOCK_LEN)，並設定 `skip_response_check=True` 以捕獲異常。
     4. 捕獲 `G_TIMEOUT_ALL` 異常後，呼叫 `api.get_fw_assert_number()` 獲取韌體 Assert 編號。
   - 預期結果：
     - 寫入操作必須觸發 `G_TIMEOUT_ALL` 異常，表示裝置無回應。
     - `api.get_fw_assert_number()` 回傳的值必須嚴格等於 `0x203`。
     - 這代表韌體在 L2 VB 邊界發生 Program Fail 時，觸發了特定的 Assert 機制，且裝置狀態為未響應（Unresponsive），而非進入 Read-Only 模式。