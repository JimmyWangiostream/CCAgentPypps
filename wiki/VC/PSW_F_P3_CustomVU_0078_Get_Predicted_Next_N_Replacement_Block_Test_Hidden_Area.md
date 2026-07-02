# Test Spec: UFS Vendor Command 40C1/40DC/40D6/4013/405E/C012 Bad Block Replacement & Erase Fail Verification

## Verification Criterion (VC)
驗證韌體在遭遇強制 Erase Fail 情境下的 Bad Block Table (BBT) 更新機制與替換區塊預測邏輯：Case 01 確認透過 Vendor Command (VU) 40C1 與 40DC 正確讀取當前 L2 Open VB 與 Next Open VB；Case 02 確認透過 VU 40D6 正確解析出預測的替換區塊 (Replacement Block) 的 CE/Plane/Block 位址；Case 03 確認透過 VU C012 對指定 L2 Next VB 及其對應替換區塊注入 Erase Fail (fail_type=1) 後，系統能正確識別並標記這兩個區塊為 Bad Block；Case 04 確認透過連續 Write10 觸發 L2 VB 切換後，透過 VU 4013 讀取 BE (Bad Endurance) Fail Status，並最終透過 VU 405E 驗證 BBT 中的 Bad Block 計數器 (BB_count) 嚴格增加 2，證明韌體成功將受影響的原始區塊與替換區塊均納入 BBT 管理。

## Test Case (TC) Checkpoints
1. [Case01_VB_Info_Initialization_Check]：
   - 動作：執行 `project_api.issue_40C1_to_get_open_vb_information()` 獲取當前 L2 Open Logical VB (Host TLC Number)，記錄為 `L2_vb`；接著執行 `project_api.issue_40DC_to_get_next_open_vb_information(0)` 獲取下一個 L2 Open VB，記錄 `DM_NORMAL_HOST_VB` 為 `L2_vb_next`；同時執行 `project_api.issue_405E_to_get_bad_block_information()` 記錄初始 Bad Block 計數 `BB_count`。
   - 預期結果：成功解析出當前與下一個 L2 VB 的邏輯位址；初始 `BB_count` 為系統當前已知的 Bad Block 總數，作為後續比對的基準值。

2. [Case02_Replacement_Block_Prediction_Check]：
   - 動作：執行 `project_api.issue_40D6_to_get_predicted_next_n_replacement_block`，參數設定為 `ce=0, plane=0, next_n=1, pool_type=2, is_CIS=0, pf_on_open_data=0`。從返回的 `VU_DATA_40D6` (前4 bytes) 中，透過位元運算提取替換區塊資訊：Block = `(Data & 0xFFFFFFE0) >> 5`，Plane = `(Data & 0x1C) >> 2`，CE = `Data & 0x03`。
   - 預期結果：成功解析出對應於 `L2_vb_next` 的硬體替換區塊位址 (`next_replacement_block`)、Plane (`next_replacement_plane`) 與 CE (`next_replacement_ce`)，確保韌體預測算法能正確映射邏輯 VB 到物理替換資源。

3. [Case03_Erase_Fail_Injection_Check]：
   - 動作：建構 `PhysicalAddressInformation` 結構體，針對兩個目標區塊注入 Erase Fail：
     1. 目標 0：Die=0, Plane=0, Block=`L2_vb_next` (當前待使用的 L2 VB)。
     2. 目標 1：Die=`next_replacement_ce`, Plane=`next_replacement_plane`, Block=`next_replacement_block` (預測的替換區塊)。
     執行 `project_api.issue_C012_to_create_program_erase_fail`，設定 `fail_type=1` (Erase Fail) 與 `block_info_list_count=2`。
   - 預期結果：韌體內部狀態機應記錄這兩個區塊的 Erase 操作失敗，並準備在後續寫入或管理流程中將其標記為 Bad Block，不立即拋出異常中斷測試流程。

4. [Case04_L2_VB_Switch_and_BBT_Update_Check]：
   - 動作：從 LBA 0 開始執行連續 `Write10` (長度 `WRITE_10_MAX_BLOCK_LEN`)，每次寫入後透過 VU 40C1 檢查 `L2_vb_new` 是否與初始 `L2_vb` 不同。若相同則 `start_lba += data_len` 繼續寫入，直到 L2 VB 發生切換 (Break)。切換後，執行 `project_api.issue_4013_to_get_BE_fail_status(1)` 讀取 Bad Endurance Fail 狀態。最後，再次執行 `project_api.issue_405E_to_get_bad_block_information()` 獲取新的 `BB_count_new`。
   - 預期結果：
     1. L2 VB 成功切換，證明寫入流程觸發了區塊替換或 VB 遷移。
     2. `BB_count_new` 必須嚴格等於 `BB_count + 2`。這驗證了韌體在處理 Erase Fail 後，正確地將「原始 L2 VB 區塊」與「其對應的替換區塊」兩者均標記為 Bad Block 並更新至 BBT，且計數器準確反映了這兩次故障事件。