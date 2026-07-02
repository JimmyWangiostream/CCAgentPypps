# Test Spec: MP Operation Post-Verification & Vendor Command Fail Injection Validation

## Verification Criterion (VC)
驗證 MP 操作後韌體狀態的一致性與 Vendor Command 錯誤注入機制的有效性：
1. **初始狀態一致性檢查**：確認韌體內部維護的 Bad Block Table (BBT) 與透過 Vendor Command (VU 405E/40C7) 讀取的硬體狀態完全同步，且 `later_VB`、`program_fail_VB`、`erase_fail_VB` 計數器在無異常情況下應為零或符合預期基線。
2. **Erase Fail 注入與替換驗證**：透過 VU C012 強制注入特定 L2 VB 的 Erase Fail，執行連續 Write10 觸發 L2 VB 切換後，驗證 Bad Block Count 增加 1，`later_VB_count` 增加 1，`later_VB_max_count` 減少 1，且該 Block 狀態正確標記為替換 (Status=1, Replaced Physical Block != 0xFFFFFFFF)。
3. **Program Fail 注入與替換驗證**：透過 VU C012 強制注入特定 L2 VB 的 Program Fail，執行單次 Write10 觸發失敗後，驗證 Bad Block Count 增加 1，`later_VB_count` 增加 1，`later_VB_max_count` 減少 1，且 `later_program_fail_VB_max_count` 增加 1，確保韌體能正確區分並記錄 Program Fail 事件。

## Test Case (TC) Checkpoints

1. [Case01_MP_Post_State_Consistency_Check]：
   - 動作：
     1. 透過 `issue_405E_to_get_bad_block_information` 讀取 VU_DATA_405E，解析前 4 位元組 Little-Endian 整數作為初始 `BB_count`，並解析 payload 從 0x04 開始每 8 位元組的區塊資訊（Block, CE, Plane）建立內部 BBT 映射表 `BB_data`。
     2. 透過 `issue_40C7_to_get_bad_block_info(0, 0)` 讀取全域 Bad Block 資訊，獲取 `later_VB_count`、`later_VB_max_count`、`later_program_fail_VB_max_count`、`later_erase_fail_VB_max_count` 及 `early_pool_physical_VB_count`。
     3. 驗證 `later_VB_count`、`later_program_fail_VB_max_count`、`later_erase_fail_VB_max_count` 均為 0，且 `BB_count` 等於 `early_pool_physical_VB_count`。
     4. 遍歷所有 `Max_PB` x `Max_Fdevice` x `Plane_Per_Die` 組合，針對每個目標區塊呼叫 `issue_40C7_to_get_bad_block_info(block, plane)` 獲取 `status` 與 `replaced_physical_block`。
     5. 比對內部 `BB_data`：若區塊存在於 BBT 中，預期 `status == 1` 且 `replaced_physical_block != 0xFFFFFFFF`；若不存在，預期 `status == 0` 且 `replaced_physical_block == 0xFFFFFFFF`。
   - 預期結果：所有計數器為零或符合基線；內部 BBT 與 Vendor Command 返回的硬體狀態完全一致，無任何狀態不匹配錯誤。

2. [Case02_Erase_Fail_Injection_And_Replacement_Check]：
   - 動作：
     1. 透過 `issue_40C1_to_get_open_vb_information` 獲取當前 `L2_vb`，並透過 `issue_40DC_to_get_next_open_vb_information(0)` 獲取下一個可用的 `L2_vb_next`。
     2. 記錄初始 `BB_count`。
     3. 構造 `PhysicalAddressInformation`，指定 `BlockInfoList_0_block` 為 `L2_vb_next`，呼叫 `issue_C012_to_create_program_erase_fail` 並設定 `fail_type=1` (Erase Fail) 進行錯誤注入。
     4. 執行迴圈連續發送 `Write10` (LUN 0, FUA=1)，每次寫入 `WRITE_10_MAX_BLOCK_LEN` 長度，直到 `issue_40C1` 返回的 `L2_Open_logical_VB_Host_TLC_number` 發生變化（即 L2 VB 從 `L2_vb` 切換至新 VB），此時觸發韌體對 `L2_vb_next` 的 Erase Fail 處理。
     5. 呼叫 `issue_4013_to_get_BE_fail_status(1)` 確認錯誤狀態。
     6. 再次呼叫 `issue_405E` 獲取新 `BB_count_new`，並呼叫 `issue_40C7` 獲取新的計數器狀態。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - `later_VB_count_new` 必須等於 `self.later_VB_count + 1`。
     - `later_VB_max_count_new` 必須等於 `self.later_VB_max_count - 1`。
     - `later_erase_fail_VB_max_count_new` 必須等於 `self.later_erase_fail_VB_max_count + 1`。
     - 代表韌體正確識別 Erase Fail 並將其標記為 Bad Block，同時更新相關計數器。

3. [Case03_Program_Fail_Injection_And_Replacement_Check]：
   - 動作：
     1. 透過 `issue_40C1_to_get_open_vb_information` 獲取當前 `L2_vb`。
     2. 記錄初始 `BB_count`。
     3. 構造 `PhysicalAddressInformation`，指定 `BlockInfoList_0_block` 為 `L2_vb`，呼叫 `issue_C012_to_create_program_erase_fail` 並設定 `fail_type=0` (Program Fail) 進行錯誤注入。
     4. 執行單次 `Write10` (LUN 0, FUA=1, 長度 `WRITE_10_MAX_BLOCK_LEN`) 觸發韌體對 `L2_vb` 的 Program Fail 處理。
     5. 呼叫 `issue_4013_to_get_BE_fail_status(1)` 確認錯誤狀態。
     6. 再次呼叫 `issue_405E` 獲取新 `BB_count_new`，並呼叫 `issue_40C7` 獲取新的計數器狀態。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - `later_VB_count_new` 必須等於 `self.later_VB_count + 1`。
     - `later_VB_max_count_new` 必須等於 `self.later_VB_max_count - 1`。
     - `later_program_fail_VB_max_count_new` 必須等於 `self.later_program_fail_VB_max_count + 1`。
     - 代表韌體正確識別 Program Fail 並將其標記為 Bad Block，且 Program Fail 專用計數器正確遞增，與 Erase Fail 機制區分明確。