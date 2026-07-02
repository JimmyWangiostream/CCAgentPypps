# Test Spec: UFS FTL VB Allocation & State Transition Verification

## Verification Criterion (VC)
驗證 UFS 韌體在不同記憶體類型（TLC/SLC/EM1）與不同邏輯層級（L2/L1/WB）下的 Virtual Block (VB) 分配與狀態遷移機制：
1. **TLC L2 驗證**：確認在 Normal LUN (LUN 0) 寫入一個完整 TLC VB 大小資料後，韌體正確將預期的 Next Open VB 分配為當前 L2 Open VB，且該 VB 的 FTL Group Type 正確標記為 MLC Pool (`current_blk_pool_mlc = 7`)。
2. **EM1 L2 驗證**：確認在 Enhanced Memory 1 LUN (LUN 1) 寫入一個完整 SLC VB 大小資料後，韌體正確將預期的 Next Open VB 分配為當前 EM1 L2 Open VB，且該 VB 的 FTL Group Type 正確標記為 SLC Pool (`current_blk_pool_slc = 6`)。
3. **L1 Small Chunk 驗證**：確認在 Normal LUN 啟用 Write Booster 關閉狀態下，透過連續 Write10 + Unmap 循環觸發 L1 (Small Chunk) 層級遷移，當 L1 Open VB 發生改變時，新的 L1 Open VB 必須與寫入過程中最後更新的 Next Open VB 一致，且該 VB 屬於指定的 L1 Group (`current_l1 = 13`)。
4. **WB (Write Booster) L2 驗證**：確認在 Normal LUN 啟用 Write Booster 狀態下，寫入 SLC VB 大小資料後，韌體正確將 Next Open VB 分配為 WB L2 Open VB，且該 VB 的 FTL Group Type 正確標記為 MLC Pool (`current_blk_pool_mlc = 7`)。

## Test Case (TC) Checkpoints

1. **[TLC_L2_Allocation_Check]**：
   - 動作：
     1. 透過 `issue_40DC_to_get_next_open_vb_information(0)` 讀取 TLC Next Open VB (`DM_NORMAL_HOST_VB`)，記錄為 `last_next_tlc_openvb`。
     2. 針對 Normal LUN (LUN 0) 執行 `sequential_write`，寫入大小為 `self.tlc_vb_size` (由 `fw_geometry.l88_vb_size_u1` 計算) 的資料。
     3. 再次讀取 Next Open VB 資訊，獲取當前 TLC L2 Open VB (`L2_Open_logical_VB_Host_TLC_number`)。
     4. 透過 `get_vb_info()` 讀取 FTL VB List，解析 `rep_data` 中對應 `last_next_tlc_openvb` 的 VB 資訊，檢查其 `group` 欄位（Bit 0-5）。
   - 預期結果：
     - 當前 TLC L2 Open VB 的數值必須嚴格等於寫入前的 `last_next_tlc_openvb`。
     - 該 VB 在 FTL VB List 中的 `group` 欄位數值必須等於 `current_blk_pool_mlc` (7)，代表該 VB 已正確分配至 MLC Pool 並作為 L2 層級使用。

2. **[EM1_L2_Allocation_Check]**：
   - 動作：
     1. 透過 `issue_40DC_to_get_next_open_vb_information(0)` 讀取 EM1 Next Open VB (`DM_NORMAL_SHARE_VB_0`)，記錄為 `last_next_slc_openvb`。
     2. 針對 EM1 LUN (LUN 1) 執行 `sequential_write`，寫入大小為 `self.slc_vb_size` (由 `fw_geometry.l84_vb_size_u0` 計算) 的資料。
     3. 再次讀取 Next Open VB 資訊，獲取當前 EM1 L2 Open VB (`open_logical_VB_number_for_EM1_L2_Host`)。
     4. 透過 `get_vb_info()` 讀取 FTL VB List，解析 `rep_data` 中對應 `last_next_slc_openvb` 的 VB 資訊，檢查其 `group` 欄位。
   - 預期結果：
     - 當前 EM1 L2 Open VB 的數值必須嚴格等於寫入前的 `last_next_slc_openvb`。
     - 該 VB 在 FTL VB List 中的 `group` 欄位數值必須等於 `current_blk_pool_slc` (6)，代表該 VB 已正確分配至 SLC Pool 並作為 EM1 L2 層級使用。

3. **[L1_Small_Chunk_Transition_Check]**：
   - 動作：
     1. 確保 Write Booster 關閉 (`api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)`)。
     2. 讀取 L1 Next Open VB (`DM_NORMAL_SHARE_VB_1`)，記錄為 `last_next_L1_openvb`。
     3. 呼叫 `write_unmap_cycle`，在 Normal LUN 上執行連續的 Write10 (16KB chunk) 與 Unmap 操作，直到 L1 Open VB 發生變化。
     4. 在循環中，每 1000 次寫入檢查一次 Next Open VB，若 `DM_NORMAL_SHARE_VB_1` 改變則更新 `last_next_L1_openvb` 並返回新的 VB 號碼。
     5. 寫入結束後，讀取當前 L1 Open VB (`L1_open_VB_S_CHUNK_logical_number`)。
     6. 透過 `get_dedicate_vb_group(current_l1)` 確認最終 L1 VB 的 Group Type 是否為 `current_l1` (13)。
   - 預期結果：
     - 最終讀取的 L1 Open VB 數值必須等於 `write_unmap_cycle` 返回的最後一個 Next Open VB 號碼。
     - 該 VB 的 FTL Group Type 必須等於 `current_l1` (13)，代表 L1 Small Chunk 層級的 VB 分配與遷移邏輯正確。

4. **[WB_L2_Allocation_Check]**：
   - 動作：
     1. 確保 Write Booster 啟用 (`api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)`)。
     2. 透過 `issue_40DC_to_get_next_open_vb_information(0)` 讀取 WB Next Open VB (`DM_NORMAL_WB_VB_0`)，記錄為 `last_next_wb_openvb`。
     3. 針對 Normal LUN (LUN 0) 執行 `sequential_write`，寫入大小為 `self.slc_vb_size` 的資料。
     4. 再次讀取 Next Open VB 資訊，獲取當前 WB L2 Open VB (`open_logical_VB_number_for_Write_Booster_WB_L2`)。
     5. 透過 `get_vb_info()` 讀取 FTL VB List，解析 `rep_data` 中對應 `last_next_wb_openvb` 的 VB 資訊，檢查其 `group` 欄位。
   - 預期結果：
     - 當前 WB L2 Open VB 的數值必須嚴格等於寫入前的 `last_next_wb_openvb`。
     - 該 VB 在 FTL VB List 中的 `group` 欄位數值必須等於 `current_blk_pool_mlc` (7)，代表 WB 緩衝區溢流或分配時正確使用了 MLC Pool 的 VB。