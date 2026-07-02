# Test Spec: UFS VB List Consistency & Write Booster State Verification

## Verification Criterion (VC)
驗證 UFS 裝置在多重 LUN 配置、Write Booster (WB) 緩衝區填充及 Flush 完成後，韌體內部虛擬區塊 (VB) 列表的邏輯一致性與狀態機轉換：
1. **初始狀態驗證**：確認在預設配置下，透過 Vendor Command (VU 0x406D) 獲取的 VB 列表與韌體內部計算邏輯 (`calculate_by_vb_list`) 生成的列表完全一致，確保基礎 VB 映射無誤。
2. **多 LUN 與 WB 配置後驗證**：確認在啟用 Normal LUN (LUN0) 與 Enhanced LUN (LUN1)，並設定 Write Booster Buffer 為 0x400 Allocation Units 後，VB 列表結構正確反映新的 LUN 配置與 WB 資源分配。
3. **WB 填充狀態驗證**：確認在 LUN0 執行隨機寫入直至 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 歸零 (0x0) 後，VB 列表中與 WB 相關的區塊（如 `CURRENT_PTE`, `TMP_CODE_BLK` 等）狀態更新正確，且與 VU 0x406D 返回數據一致。
4. **WB Flush 完成狀態驗證**：確認觸發 `WRITEBOOSTER_BUFFER_FLUSH_EN` 後，當 `WRITEBOOSTER_BUFFER_FLUSH_STATUS` 為 `COMPLETED` 且 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 穩定在 0xA 時，VB 列表反映 WB 緩衝區已清空並恢復至預設保留狀態，且數據一致性通過檢查。

## Test Case (TC) Checkpoints

1. [Initial_VB_List_Consistency_Check]：
   - 動作：讀取當前 HW Setting 中的 `POWER_SAVING_CTRL_ENABLE` 並備份，將其設定為 0x3A 以禁用電源節省控制。透過 `project_api.custom_vu.issue_406D_get_VB_list_info()` 獲取韌體 VB 列表 (`sorted_vb_list_from_VU`)。同時呼叫 `calculate_by_vb_list()`，該函數透過 `get_vb_info` 取得原始 VB 資訊，解析每個 VB 的 Group ID (低 6 bits) 與 Access Mode (bit 6-7)，並針對特定 Group (如 0x07, 0x11, 0x13, 0x1B) 進行計數與索引排序，生成預期列表 (`data_from_vb_info`)。
   - 預期結果：`sorted_vb_list_from_VU` 必須與 `data_from_vb_info` 完全相等 (byte-by-byte match)。若不相等，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此步驟驗證基礎 VB 映射邏輯與 Vendor Command 返回數據的一致性。

2. [Multi_LUN_WB_Config_VB_List_Check]：
   - 動作：執行 `config_precondition()`，修改 Configuration Descriptor：
     - LUN0 (Normal Memory Type)：啟用，分配 `total_au >> 1` 個 Allocation Units，Logical Block Size 0xC (4KB)。
     - LUN1 (Enhanced_1 Memory Type)：啟用，分配 `total_au >> 1` 個 Allocation Units，Logical Block Size 0xC (4KB)。
     - 其他 LUN：禁用。
     - 設定 Write Booster Buffer 類型為 1，Preserve User Space 為 1，Shared Buffer 分配為 0x400 AU。
     - 推送配置並發送命令。更新 Unit Descriptor。
     - 再次透過 VU 0x406D 獲取 VB 列表，並與 `calculate_by_vb_list()` 生成的預期列表進行比對。
   - 預期結果：兩份 VB 列表必須完全一致。驗證韌體在動態調整 LUN 配置與 WB 資源分配後，VB 索引表能即時且準確地反映硬體資源狀態。

3. [WB_Fill_State_VB_List_Check]：
   - 動作：啟用 Write Booster (`WRITEBOOSTER_EN`)。在 LUN0 (範圍 0 至 `_param.gLUCapacity[0]`) 執行隨機寫入，每次寫入大小隨機介於 64MB 至 128MB。持續監控 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 屬性，直到其值變為 0x0 (緩衝區滿) 或超過 15 分鐘超時。
   - 預期結果：當 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 為 0x0 時，再次獲取 VB 列表並與計算值比對，兩者必須一致。驗證在 WB 緩衝區完全被佔用時，韌體內部 VB 狀態機正確標記了相關區塊的使用狀態。

4. [WB_Flush_Completion_VB_List_Check]：
   - 動作：啟用 `WRITEBOOSTER_BUFFER_FLUSH_EN`。輪詢讀取 `WRITEBOOSTER_BUFFER_FLUSH_STATUS` 與 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE`。等待條件：`WB_flush_status` 等於 `COMPLETED` (0x03) **且** `Available WB size` 等於 0xA。Idle 30 秒讓裝置穩定。
   - 預期結果：在滿足上述條件後，獲取 VB 列表並與計算值比對，兩者必須一致。特別注意 `Available WB size` 穩定在 0xA 而非 0x0，這代表 WB 緩衝區在 Flush 後保留了特定的保留區塊 (Reserved Blocks) 或預設結構，韌體必須正確反映這一最終穩定狀態，而非錯誤地認為緩衝區完全清空或仍處於忙碌狀態。