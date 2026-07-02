# Test Spec: UFS FTL BBT Boundary & Block Count Consistency Verification

## Verification Criterion (VC)
驗證 UFS 韌體內部 FTL (Flash Translation Layer) 的 Bad Block Table (BBT) 狀態機與外部 Vendor Command (0x4004) 回報的區塊邊界資訊是否完全一致：
1. **Hidden Block Boundary**：確認韌體內部 `bbt_info_ce[ce].bbt_info[plane].hidden_bound` 與 Vendor Command payload 中對應偏移量的數值（+1 修正後）一致，驗證隱藏區塊計數邏輯。
2. **Spare Block Boundary**：確認韌體內部 `bbt.pivot`（ICS 起始 VB 索引）與 Vendor Command payload 中對應偏移量的數值（+1 修正後）一致，驗證備用區塊邊界。
3. **ICS Pool Boundary**：確認韌體內部 `bbt.last_bbs_vb` 與 Vendor Command payload 中對應偏移量的數值一致，驗證 ICS 區塊池結束索引。
4. **Table Pool Boundary**：確認韌體內部 `bbt.last_tbl_pool_vb` 與 Vendor Command payload 中對應偏移量的數值一致，驗證 Table 區塊池結束索引。
5. **SLC Pool Boundary**：確認韌體內部 `bbt.last_slc_pool_vb` 與 Vendor Command payload 中對應偏移量的數值一致，驗證 SLC 區塊池結束索引。
6. **Dynamic User Pool Boundaries**：確認韌體內部 `bbt.user_floor` 與 `bbt.user_ceil` 與 Vendor Command payload 中對應偏移量的數值（扣除 Spare Bound 後）一致，驗證動態使用者區塊池的上下界。
7. **Bad Block Count**：累計所有 CE 與 Plane 的 `bad_blk_cnt`，確保韌體內部計數器正確累加。

## Test Case (TC) Checkpoints
1. [BBT_Boundary_Consistency_Check]:
   - 動作：
     1. 透過 `get_flash_setting()` 獲取 `Max_Fdevice` (CE 數量)。
     2. 呼叫 `project_api.issue_4004_get_boundaryblocks_for_hiddentable_static_dynamicpool()` 獲取 Vendor Command 0x4004 的回傳 Payload。
     3. 透過 `read_fw_value` 讀取韌體內部結構體 `gUfsApiStruct.ftl->bbt` 下的多個關鍵指標：`hidden_bound` (遍歷所有 CE/Plane)、`pivot`、`last_bbs_vb`、`last_tbl_pool_vb`、`last_slc_pool_vb`、`user_floor`、`user_ceil`。
     4. 針對每個 CE (0 至 Max_Fdevice-1) 和 Plane (0 至 5)，解析 Vendor Command Payload 中的二進制數據：
        - **Hidden Bound**: 讀取 offset `2*plane_num` 處的 2-byte Little Endian 值，加 1 後與韌體 `hidden_bound` 比對。若韌體值為 0，則視為 0xFFFF+1 進行比對。
        - **Spare Bound**: 讀取 offset `48*1 + 2*plane_num` 處的 2-byte Little Endian 值，加 1 後與韌體 `pivot` 比對。
        - **ICS Bound**: 讀取 offset `48*2 + 2*plane_num` 處的 2-byte Little Endian 值，與韌體 `last_bbs_vb` 比對。
        - **Table Bound**: 讀取 offset `48*3 + 2*plane_num` 處的 2-byte Little Endian 值，與韌體 `last_tbl_pool_vb` 比對。
        - **SLC Bound**: 讀取 offset `48*4 + 2*plane_num` 處的 2-byte Little Endian 值，與韌體 `last_slc_pool_vb` 比對。
        - **Dynamic Floor**: 讀取 offset `48*5 + 2*plane_num` 處的 2-byte Little Endian 值，減去 Spare Bound 後與韌體 `user_floor` 比對。
        - **Dynamic Ceil**: 讀取 offset `48*6 + 2*plane_num` 處的 2-byte Little Endian 值，減去 Spare Bound 後與韌體 `user_ceil` 比對。
     5. 累計所有 CE/Plane 的 `bad_blk_cnt` 並記錄。
   - 預期結果：
     - 所有 CE 與 Plane 的比對均必須通過，若任何一組數據不符（例如 `compare_value != tmp_cnt`），則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。
     - 特別注意：`hidden_bound` 在韌體為 0 時需轉換為 0xFFFF+1 再比對；Dynamic Bound 需先扣除 Spare Bound 再比對。
     - 最終 `bad_blk_cnt` 應為所有 CE/Plane 壞塊計數器的總和，用於後續壞塊管理策略的基線確認。