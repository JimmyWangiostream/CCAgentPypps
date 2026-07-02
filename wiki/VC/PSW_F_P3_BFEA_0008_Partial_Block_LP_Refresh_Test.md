# Test Spec: UFS BFEA (Block Error Frequency Analysis) Scan Logic & Timer Mechanism Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 BFEA (Block Error Frequency Analysis) 掃描機制的硬體行為與狀態機邏輯：
1. **Case 01 (Enhanced LUN / Normal Bin)**：確認在 Enhanced_1 LUN 上寫入特定數據後，BFEA 掃描能正確識別出最佳 Bin (Best Bin)，且當該 Bin 值 <= 1 時，觸發 Group 0 的定期掃描計數器（Trig/Done Count）在等待 1 分鐘後精確增加 1。
2. **Case 02 (Boot LUN A / Skip Bin)**：確認在 Boot LUN A 上寫入數據後，透過 Vendor Command (0x40B0/0xD04A) 手動修改 BFEA 表格，將「最佳 Bin」覆蓋為「Skip Bin」，迫使系統進入 Group 1 或 Group 2 的掃描邏輯；驗證在等待 1 分鐘後，對應 Group 的計數器精確增加 1，且 Booking Queue 中的 BFEA 任務優先級與 Bit Position 符合預期（Bit 18 設為 1，Priority 設為 1）。

## Test Case (TC) Checkpoints

1. [Case01_Enhanced_LUN_BFEA_Scan_Group0_Check]：
   - 動作：
     1. 透過 `config_case(1)` 配置 LUN 0 為 `MemoryType.ENHANCED_1`，並分配全部 AU 容量。
     2. 執行 `flow6`：對 LUN 0 執行 Unmap 清除資料，並透過 `SetFlag(PURGE_EN)` 觸發 Purge，輪詢 `AttributeIDN.PURGE_STATUS` 直到狀態為 `0x03` (Complete)，隨後關閉 Auto Standby。
     3. 執行 `flow7`：向 LUN 0 寫入 `write_data_size4k` (由 `PB_SCAN_PAGE` 和 `PB_SCAN_ENABLE_PAGE_GAP` 計算得出) 的 4KB 資料。透過 `lba_to_pba` 取得目標 VB 與 CE。
     4. 執行 `issue_40B1_then_expected_result`：發送 Vendor Command `0x40B1` (Get Best Bfea Scan) 查詢該 VB/CE 的最佳 Bin，記錄為 `source_best_bin`。
     5. 執行 `flow10_11`：發送 Vendor Command `0x40B0` (Option 3) 遍歷所有 CE，取得該 VB 的最小 Bin 值 `min_bin_val`。
     6. 執行 `flow12`：根據 `min_bin_val` 判斷 Group (若 `min_bin_val <= 1` 則 `grp=0`)，並發送 Vendor Command `0x40B0` (Option 9) 設定 Group 0 的掃描間隔為 1 分鐘 (`time_gap_min - setting_timer_minutes`)。
     7. 執行 `flow13`：休眠 1 分鐘。
     8. 執行 `flow14`：讀取韌體內部變數 `gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[0]` 與 `done_count[0]`。
   - 預期結果：
     - `min_bin_val` 必須小於等於 1，確保觸發 Group 0 邏輯。
     - 韌體變數 `bfea_regular_scan_group_trig_count[0]` 必須等於 `flow9` 中記錄的初始值 + 1。
     - 韌體變數 `bfea_regular_scan_group_done_count[0]` 必須等於 `flow9` 中記錄的初始值 + 1。
     - 代表 BFEA 掃描機制在 Group 0 條件滿足且時間到期後，正確觸發並完成了一次定期掃描計數。

2. [Case02_Boot_LUN_A_BFEA_Scan_Group1_Check_With_Manual_Bin_Override]：
   - 動作：
     1. 透過 `config_case(2)` 配置 LUN 0 為 `MemoryType.ENHANCED_1` 但僅分配 4 AU，並設定 `BootLUNID.BOOT_LUN_A`。
     2. 執行 `flow6`：對 LUN 0 執行 Unmap 與 Purge (`Purge Status == 0x03`)，關閉 Auto Standby。
     3. 執行 `flow7`：向 LUN 0 寫入數據，取得目標 VB/CE。發送 `0x40B1` 取得 `source_best_bin`。
     4. 設定 `skip_bin = PB_REFRESH_BIN + 1`。
     5. 執行 `set_bfea_scan_make_offset_all_128(skip_bin)`：發送 Vendor Command `0xD04A` 將所有 Bin (0-15) 的 Offset 設為 128，但跳過 `skip_bin`。
     6. 執行 `set_table_bin_as_another_bin(source_best_bin, skip_bin)`：發送 Vendor Command `0xD04A` 將 `skip_bin` 的 Offset 表格值複製為 `source_best_bin` 的原始表格值，從而「污染」或「覆蓋」該 Bin 的掃描結果，確保 `0x40B0` (Option 3) 查詢時，該 VB/CE 的最小 Bin 值不再是最優的 `source_best_bin`，而是變成 `skip_bin` (或更高錯誤率的 Bin)。
     7. 執行 `flow10_11`：發送 `0x40B0` (Option 3) 查詢，確認 `min_bin_val` 已改變（預期為 `skip_bin` 或更高，確保 `min_bin_val > 1`，從而進入 Group 1 或 2）。
     8. 執行 `flow12`：根據新的 `min_bin_val` 計算 Group (假設 `1 < min_bin_val <= 8` 則 `grp=1`)，發送 `0x40B0` (Option 9) 設定該 Group 的掃描間隔為 1 分鐘。
     9. 執行 `flow13`：休眠 1 分鐘。
     10. 執行 `flow14`：讀取韌體變數 `bfea_regular_scan_group_trig_count[1]` 與 `done_count[1]`。
     11. 執行 `flow15_16`：發送 Vendor Command `0x40C5` (Get Booking Queue)，解析 Payload 的 Byte 12-16。
   - 預期結果：
     - `min_bin_val` 必須大於 1，確保觸發 Group 1 (或 2) 邏輯。
     - 韌體變數 `bfea_regular_scan_group_trig_count[1]` 必須等於 `flow9` 中記錄的初始值 + 1。
     - 韌體變數 `bfea_regular_scan_group_done_count[1]` 必須等於 `flow9` 中記錄的初始值 + 1。
     - Booking Queue Payload 的 Byte 12-16 中，Bit 18 (`bfea_booking`) 必須等於 1 (代表 BFEA 任務已入隊)。
     - Booking Queue Payload 的 Byte 12-16 中，Priority 欄位 (Bit 8) 必須等於 1。
     - 代表 BFEA 機制在 Bin 值異常 (Group 1) 時，正確觸發掃描計數，並將高優先級的 BFEA 任務排入 Booking Queue。