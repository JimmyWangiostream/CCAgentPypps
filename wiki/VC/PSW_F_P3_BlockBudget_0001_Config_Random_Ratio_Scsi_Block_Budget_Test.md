# Test Spec: UFS Block Budget & LUN Partitioning Verification

## Verification Criterion (VC)
驗證 UFS 韌體在不同 CE (Chip Enable) 數量與 SLC/TLC 混合配置下的 Block Budget 分配邏輯與硬體資源隔離機制：
1. **初始狀態驗證**：確認在預設 "Open_Card" 配置下，韌體分配的各類型 Block（System Table, SLC/TLC User Data, OP, Hidden, GC Reserve 等）數量符合 `block_budget_criteria_dict` 中定義的最低閾值，且總 VB (Valid Block) 數量滿足 `least_vb_cnt_criteria_dict` 的硬性要求。
2. **動態 Partition 驗證**：驗證在 27 種不同的 SLC/TLC 比例配置（從 100% SLC 到 100% TLC，含混合比例）下，透過 UFS Standard Unit Descriptor 動態配置 LUN 的 Memory Type (`NORMAL` vs `ENHANCED_1`) 後，韌體能正確重新計算並分配 Block 預算。
3. **硬體邊界一致性驗證**：透過 Vendor Command `0x4004` 讀取硬體層級的 Block Boundary 暫存器值，驗證韌體邏輯計算出的 Block 分區（如 `slc_blk`, `dynamic_bounday0`）與硬體實際劃分的物理區塊邊界完全一致，特別是在極端配置（如 Case 7: 100% SLC）下，TLC 動態區塊應為 0 且無溢位錯誤。
4. **容量與隨機存取驗證**：確認總原始容量 (`TotalRawCap`) 與 CE 數量成線性比例關係，並透過隨機 SCSI 操作（Write, Unmap, Purge, Read Compare）確保在混合 LUN 環境下資料完整性與 Purge 狀態機的正常運作。

## Test Case (TC) Checkpoints

1. [Case01_Initial_Budget_Check]：
   - 動作：在系統初始化後，呼叫 `get_all_vb_cnt` 讀取 Offset 0x1000 (2560) 處的 36 位元組 VB 計數表，解析出 `system_table`, `slc_user_data`, `tlc_user_data` 等欄位。將這些值與 `block_budget_criteria_dict_CE[CE]` 中 "Open_Card" 配置的閾值進行比對（例如：`system_table >= 23`, `hidden_blk >= 8`）。同時計算所有 VB 欄位總和，並與 `least_vb_cnt_criteria_dict[CE]`（CE=1 時為 457，CE=2/4 時為 455）進行比較。
   - 預期結果：所有解析出的 VB 計數必須大於或等於對應的閾值；總 VB 數量必須 >= 457 (1CE) 或 455 (2/4CE)。若任一欄位低於閾值或總數不足，測試應報錯 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [Case02_Dynamic_LUN_Configuration_Check]：
   - 動作：針對 Case 1 至 27，計算對應的 `normal_ratio` (TLC) 與 `em1_ratio` (SLC)。透過 `config_lun` 函數，隨機選擇 LUN 並設定其 `b3_memory_type` 為 `MemoryType.NORMAL` (TLC) 或 `MemoryType.ENHANCED_1` (SLC)，並根據比例分配 `l4_num_alloc_units`。發送 UFS `WRITE_CONFIG` 命令更新 Descriptor，隨後發送 `READ_DESCRIPTOR` 確認配置生效，並對所有啟用的 LUN 執行 `TEST_UNIT_READY`。
   - 預期結果：UFS 裝置成功接受配置並進入 Unit Ready 狀態；LUN 的 Memory Type 屬性正確反映為 NORMAL 或 ENHANCED_1；韌體內部記錄的 LUN 列表與硬體狀態同步。

3. [Case03_Block_Boundary_Hardware_Consistency_Check]：
   - 動作：在每次 LUN 配置變更後，呼叫 `get_block_boundary`。透過 Vendor Command `0x4004` 讀取硬體 Block Boundary 結構體，解析各 CE/Plane 的 `hidden_bound`, `spare_bound`, `ics_bound`, `table_bound`, `slc_stop`, `dynamic_bound0`, `dynamic_bound_ce`。計算韌體邏輯區塊數量（例如：`slc_blk = slc_stop - table_bound`，`dynamic_bounday0 = dynamic_bound0 - slc_stop`）。將這些計算值與 `check_meet_block_budget_criteria` 中定義的 `block_budget_criteria_dict` 閾值進行比對。特別檢查 Case 7 (100% SLC) 時，`dynamic_bounday0` 是否嚴格等於 0。
   - 預期結果：
     - 一般情況：`ics_blk` (System Table) >= 23, `table_blk` >= 23, `slc_blk` >= (slc_user_data + slc_op + rev_blk), `dynamic_bounday0` (TLC) >= (tlc_user_data + tlc_op + rev_blk), `dynamic_bounday1` (BB Replacement) >= 4。
     - Case 7 (100% SLC)：`dynamic_bounday0` 必須精確等於 0，表示無 TLC 區塊分配，且無下溢位或邏輯錯誤。
     - 所有計算出的硬體邊界區塊數必須滿足上述最小值要求，否則報錯。

4. [Case04_Total_Capacity_Linearity_Check]：
   - 動作：讀取 `gGeometry.q4_total_raw_device_capacity`。根據 `flashsetting.FLH_Quantity * (BIT0 << flashsetting.Parallel)` 計算 CE 數量。
   - 預期結果：
     - 若 CE == 1，容量必須等於 `0xEE64000`。
     - 若 CE == 2，容量必須等於 `0x1DCBC000`。
     - 若 CE == 4，容量必須等於 `0x3B96C000`。
     - 任何偏差均觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，驗證硬體容量映射與韌體幾何參數的一致性。

5. [Case05_Random_SCSI_Operation_Integrity_Check]：
   - 動作：在配置好的 LUN 列表上，隨機執行以下操作序列：
     - **WRITE**: 隨機 LUN/LBA/Size (4K-128K)，使用 `HW_COMPARE` 驗證寫入資料。
     - **UNMAP**: 隨機 LUN/LBA/Size 執行邏輯刪除。
     - **PURGE**: 設定 `FlagIDN.PURGE_EN`，輪詢 `AttributeIDN.PURGE_STATUS` 直到 `PurgeStatus.PURGE_STS_COMPLETE_SUCCESS`，超時 30 秒則報錯。
     - **READ_COMPARE**: 對之前寫入的 `write_record` 進行硬體比對讀取。
   - 預期結果：所有 SCSI 命令返回成功狀態碼；`PURGE` 操作在 30 秒內完成並返回成功狀態；`READ_COMPARE` 驗證資料與寫入時一致，無資料損毀或 ECC 錯誤累積導致驗證失敗。