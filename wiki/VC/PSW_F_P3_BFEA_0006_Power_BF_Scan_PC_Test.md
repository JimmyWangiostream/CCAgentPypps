# Test Spec: UFS FTL BFEA (Bad Flash Element Analysis) Power Cycle Recovery & State Persistence Test

## Verification Criterion (VC)
驗證 UFS 韌體在異常掉電（SSU Power Cycle）情境下，BFEA（Bad Flash Element Analysis）掃描狀態機與計數器的硬體行為：
1. **Case 01 (BFEA Disabled)**：確認在 BFEA 掃描功能關閉（Opcode 1, Param=0）且未進行任何 BFEA 表項設定的情況下，執行 HW_RESET + Power Down 後，韌體內部的 `bfea_power_up_done_cnt` 計數器**不應增加**，且 BFEA 表項數據保持不變。
2. **Case 02 (BFEA Enabled - Bin 0/1)**：確認在 BFEA 掃描功能開啟（Opcode 1, Param=1）並針對特定 L2 VB 的 CE 設定 Bin 0 或 Bin 1 後，執行 HW_RESET + Power Down 觸發韌體恢復流程，`bfea_power_up_done_cnt` 計數器**必須遞增**，且 BFEA 表項數據在恢復後與掉電前**完全一致**（驗證非揮發性儲存或恢復機制正確）。
3. **Case 03 (BFEA Enabled - Bin 2/5/8/15)**：確認在 BFEA 掃描功能開啟並設定較高複雜度 Bin（2, 5, 8, 15）或混合設定後，執行 HW_RESET + Power Down，`bfea_power_up_done_cnt` 計數器**必須遞增**，且 BFEA 表項數據在恢復後與掉電前**完全一致**，驗證韌體能正確處理不同 BFEA 級別的狀態持久化。

## Test Case (TC) Checkpoints

1. [Case01_BFEA_Disabled_No_Counter_Increment_Check]：
   - 動作：
     1. 透過 `random_config` 隨機啟用一個 Normal LUN (`random_en_lun`)，並將其配置為 Thin Provisioning，分配全部 Allocation Units。
     2. 執行 Unmap 並設定 `PURGE_EN` Flag，輪詢 `PURGE_STATUS` 直到返回 `0x03` (Complete)，確保儲存空間清空。
     3. 發送 Vendor Command `0x40B0` (Opcode 1, Param=0) **禁用** BFEA 掃描功能。
     4. 透過 `Write10` 寫入 2 個 TLC VB 大小的資料（約 `2 * tlc_vb_size` 個 4KB 區塊），Chunk Size 為 512KB。
     5. 透過 `lba_to_pba` 獲取寫入區域對應的 VB 與 CE，並透過 `get_target_vb_list(17)` 取得所有 Group Type 為 17 的 L2 VB 列表 (`used_l2_vb_list`)。
     6. 透過 Vendor Command `0x40B0` (Opcode 3) 讀取所有 `used_l2_vb_list` 中每個 CE 的 BFEA 表項，儲存為 `ori_bfae_table_list`。
     7. 讀取韌體內部變數 `gUfsApiStruct.ftl->split_info->smart_info_2.bfea_power_up_done_cnt` 記錄為 `before_cnt`。
     8. 執行 SSU Power Down 並觸發 HW_RESET。
     9. 輪詢 Vendor Command `0x40B0` (Opcode 5) 直到返回 `1` (Idle)，確認 BFEA 狀態機就緒。
     10. 讀取韌體內部變數 `bfea_power_up_done_cnt` 記錄為 `after_cnt`。
     11. 再次讀取 BFEA 表項 (`bfae_table_list_after`) 並與 `ori_bfae_table_list` 進行逐項比對。
   - 預期結果：
     - `after_cnt` 必須**等於** `before_cnt`（計數器未增加，因為 BFEA 功能被禁用，韌體不應執行完整的 BFEA 恢復流程）。
     - `bfae_table_list_after` 必須與 `ori_bfae_table_list` **完全相同**，任何差異均視為測試失敗。

2. [Case02_BFEA_Enabled_Bin01_Persistence_Check]：
   - 動作：
     1. 重複 Case 01 的初始化步驟（Unmap, Purge, Enable BFEA via `0x40B0` Opcode 1 Param 1）。
     2. 透過 `Write10` 寫入 3 個 TLC VB 大小的資料。
     3. 獲取 `used_l2_vb_list`。
     4. 透過 Vendor Command `0x40B0` (Opcode 3) 讀取並儲存初始 BFEA 表項 `ori_bfae_table_list`。
     5. **Case 02-1 (Bin 0)**：針對所有 `used_l2_vb_list` 中的所有 CE，發送 `0x40B0` (Opcode 2, Param=0) 設定 BFEA Bin 為 0。
     6. **Case 02-2 (Bin 1)**：針對所有 `used_l2_vb_list` 中的所有 CE，發送 `0x40B0` (Opcode 2, Param=1) 設定 BFEA Bin 為 1。
     7. 讀取韌體內部變數 `bfea_power_up_done_cnt` 記錄為 `before_cnt`。
     8. 執行 SSU Power Down 並觸發 HW_RESET。
     9. 輪詢 Vendor Command `0x40B0` (Opcode 5) 直到返回 `1` (Idle)。
     10. 讀取韌體內部變數 `bfea_power_up_done_cnt` 記錄為 `after_cnt`。
     11. 再次讀取 BFEA 表項 `bfae_table_list_after` 並與 `ori_bfae_table_list` 進行逐項比對。
   - 預期結果：
     - `after_cnt` 必須**大於** `before_cnt`（計數器遞增，代表韌體在電源循環後執行了 BFEA 恢復/掃描流程）。
     - `bfae_table_list_after` 必須與 `ori_bfae_table_list` **完全相同**，驗證 Bin 0/1 的狀態在掉電後被正確保留或恢復。

3. [Case03_BFEA_Enabled_Bin2_5_8_15_Mixed_Persistence_Check]：
   - 動作：
     1. 重複 Case 02 的初始化步驟（Unmap, Purge, Enable BFEA, Write 3 TLC VBs）。
     2. 獲取 `used_l2_vb_list`。
     3. 透過 Vendor Command `0x40B0` (Opcode 3) 讀取並儲存初始 BFEA 表項 `ori_bfae_table_list`。
     4. **Case 03-1 (Bin 2)**：針對所有 `used_l2_vb_list` 中的所有 CE，發送 `0x40B0` (Opcode 2, Param=2) 設定 BFEA Bin 為 2。
     5. **Case 03-2 (Bin 8)**：針對隨機選取的兩個不同 VB（`indices[0]` 和 `indices[1]`）中的所有 CE，分別發送 `0x40B0` (Opcode 2, Param=8) 設定 BFEA Bin 為 8。
     6. **Case 03-3 (Bin 5 & 15)**：針對隨機選取的另外兩個不同 VB（`indices[1]` 和 `indices[2]`，注意索引可能重疊或獨立，視 `random.shuffle` 結果而定，代碼中分別對 `indices[1]` 設 Bin 5，`indices[2]` 設 Bin 15），發送 `0x40B0` (Opcode 2, Param=5) 和 `0x40B0` (Opcode 2, Param=15) 設定對應 VB 的 BFEA Bin。
     7. 讀取韌體內部變數 `bfea_power_up_done_cnt` 記錄為 `before_cnt`。
     8. 執行 SSU Power Down 並觸發 HW_RESET。
     9. 輪詢 Vendor Command `0x40B0` (Opcode 5) 直到返回 `1` (Idle)。
     10. 讀取韌體內部變數 `bfea_power_up_done_cnt` 記錄為 `after_cnt`。
     11. 再次讀取 BFEA 表項 `bfae_table_list_after` 並與 `ori_bfae_table_list` 進行逐項比對。
   - 預期結果：
     - `after_cnt` 必須**大於** `before_cnt`（計數器遞增，代表韌體處理了複雜的 BFEA 狀態恢復）。
     - `bfae_table_list_after` 必須與 `ori_bfae_table_list` **完全相同**，驗證 Bin 2, 5, 8, 15 等多種 BFEA 級別在異常掉電後，其對應的 VB/CE 狀態能被精確恢復，無數據損毀或狀態丟失。