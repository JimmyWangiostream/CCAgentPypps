# Test Spec: UFS Rain Parity Verification via VU4055 and Direct Read

## Verification Criterion (VC)
驗證 UFS 韌體在 TLC、SLC 及 Write Booster (WB) 三種不同儲存模式下的 Rain Parity 計算正確性與一致性：
1. **硬體資料擷取驗證**：透過 `Direct Read` 指令（PCA 設定 `b4_mode` 區分 TLC/SLC 模式）直接讀取 VB 內特定 CE/Plane 的原始 Payload 前 8 位元，並由 Host 端進行 XOR 運算得出預期 Parity。
2. **韌體 Parity 查詢驗證**：透過 Vendor Command `VU4055` 查詢特定 Rain Group 的韌體內部 Parity 值。
3. **一致性比對**：確認 Host 端手動計算的 Parity 與韌體回報的 Parity 完全一致，驗證韌體在 HW_RESET 後，其內部維護的 Rain Parity 狀態與 Flash 實際儲存的資料（含 FW Spare 區）保持同步，無資料損毀或 Parity 計算錯誤。

## Test Case (TC) Checkpoints
1. [Mode_Coverage_Parity_Check]：
   - 動作：
     1. 針對 `TestMode.TEST_TLC`、`TEST_SLC`、`TEST_WB` 三種模式分別執行循環測試。
     2. 若為 WB 模式，設定 `api.FlagIDN.WRITEBOOSTER_EN` 為 True；否則為 False。
     3. 向指定 LUN 寫入超過 3 頁的資料，取得 `cursor` (VB 資訊) 與 `last_lba`。
     4. 執行 `HW_RESET` (無 Power Down) 以觸發韌體重新初始化並載入 Parity 狀態。
     5. **Host 端計算**：呼叫 `get_raw_data_buffer`，根據 `rain_user` 設定 PCA 的 `b4_mode` (TLC 為 2, SLC 為 1)，遍歷所有 CE 與 Plane (排除無效 Plane)，執行 `api.direct_read` 讀取每個 Page 的 Payload 前 8 位元，並對所有讀取到的 8 位元資料進行 XOR 運算，得到 `parity_manual`。
     6. **韌體端查詢**：呼叫 `project_api.issue_4055_to_get_rain_parity`，傳入相同的 `rain_user` 與計算出的 `group` (基於 `cursor.first_empty_physical_page` 對 `rain_goup_cnt` 取模)，取得韌體回報的 `get_parity`。
     7. 比對 `parity_manual[0:8]` 與 `get_parity[0:8]`。
   - 預期結果：
     - `parity_manual` 必須嚴格等於 `get_parity`。
     - 若不相等，記錄錯誤並拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 此結果證明無論在 TLC、SLC 或 WB 模式下，韌體透過 VU4055 提供的 Parity 值與 Flash 實際儲存的資料 XOR 結果一致，驗證了 Parity 機制在 Reset 後的完整性。

2. [Direct_Read_PCA_Configuration_Check]：
   - 動作：在 `get_raw_data_buffer` 函數中，檢查 PCA 暫存器的設定邏輯：
     1. `l0_op` 設定為 `api.BIT24`。
     2. `b4_mode` 根據 `rain_user` 動態設定：若為 `HOST_TLC_RAIN` 則設為 2，否則設為 1。
     3. `b5_ce` 與 `b6_plane` 遍歷硬體幾何結構 (`max_ce`, `max_plane`)。
     4. `b11_block_h` 與 `b10_block_l` 設定為當前 VB 的 Block 編號。
     5. `l12_fpage` 設定為 `cursor.first_empty_physical_page.value << 5`。
     6. 呼叫 `api.direct_read` 並設定 `block_count=4` 且 `include_FW_spare=True`。
   - 預期結果：
     - 讀取的資料必須包含 FW Spare 區，確保 Parity 計算涵蓋完整的邏輯區塊資料。
     - 讀取的 Page 地址必須精確對應到 VB 內的物理頁面，且跳過 `invalid_plane_list` 標記為無效的 Plane，確保 XOR 運算僅針對有效資料進行。