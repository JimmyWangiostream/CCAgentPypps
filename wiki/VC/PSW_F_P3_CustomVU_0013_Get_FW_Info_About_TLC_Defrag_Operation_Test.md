# Test Spec: UFS FTL 40C2 Vendor Command Enhanced Health Report Verification

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command `0x40C2` 回傳之 Enhanced Health Report Payload 中，各 Offset 欄位（Offset 0 至 175）與 FTL 內部狀態機、VB (Virtual Block) 計數器、Write Booster (WB) 緩衝區狀態、以及 GC (Garbage Collection) 觸發條件的一致性。測試涵蓋 Normal (TLC) 與 EM1 (SLC) 兩種 Partition 的獨立驗證，確認 BG/FG GC 閾值、IGC (Immediate GC) 觸發旗標、LOCKED_SRC 列表狀態、WB 緩衝區大小動態變化、以及 Invalid Pool 中 Fragmented VB 的計數邏輯符合韌體設計規範。

## Test Case (TC) Checkpoints

1. [TC01_GC_Trigger_Flags_Check]:
   - 動作：執行 `issue_40C2_to_get_info_about_TLC_defrag_operation` 讀取 Vendor Command 回應，檢查 Offset [0:3] 的 `GC_trigger_fields` 與 Offset [4:7] 的 `GC_trigger_type`。
   - 預期結果：Offset [0:3] 數值必須等於 `(payload_length - 4) / 4`，代表有效欄位數量正確；Offset [4:7] 必須為 `0`，代表當前無 BG 或 FG GC 正在執行。

2. [TC02_Normal_BG_GC_Threshold_Check]:
   - 動作：配置 LUN 為 Normal (TLC) 佔用全部 AU，讀取 GC 閾值 (`api.get_gc_threshold`)，計算 `bg_mlc_gc_threshold = mlc_threshold - 3`。再次讀取 40C2 Payload，檢查 Offset [8:11] `start_bg_gc_vb_cnt_normal` 與 Offset [12:15] `stop_bg_gc_vb_cnt_normal`。
   - 預期結果：Offset [8:11] 與 Offset [12:15] 的數值均必須等於 `bg_mlc_gc_threshold`，確認 Normal 區域的 BG GC 啟動與停止閾值設定正確。

3. [TC03_Normal_FG_GC_Threshold_Check]:
   - 動作：讀取 40C2 Payload，檢查 Offset [16:19] `start_fg_gc_vb_cnt_normal`。
   - 預期結果：該欄位數值必須等於 `mlc_threshold`，確認 Normal 區域的 FG IMMEDIATE GC 觸發閾值設定正確。

4. [TC04_WB_Cache_Size_LS0_Check]:
   - 動作：配置 Write Booster Buffer 大小為 2048 AU，計算對應的 SLC VB 數量 `expect_value = ceil(config_wb_node_size / SLC_VB_4K_SIZE)`。讀取 40C2 Payload，檢查 Offset [24:27] `wb_slc_cache_vb_size_ls0`。
   - 預期結果：Offset [24:27] 數值必須等於 `expect_value`，確認 Logical Saturation (LS) 為 0 時，WB SLC Cache 的大小計算正確。

5. [TC05_WB_Cache_Size_LS100_Check]:
   - 動作：透過 `read_fw_value` 讀取韌體變數 `gUfsApiStruct.ftl->vb_list.head_misc->statistics.non_slc_vc_threshold_min` 作為最小 WB 節點大小，計算 `expect_value = ceil(min_wb_node_size / SLC_VB_4K_SIZE)`。讀取 40C2 Payload，檢查 Offset [28:31] `wb_slc_cache_vb_size_ls100`。
   - 預期結果：Offset [28:31] 數值必須等於 `expect_value`，確認 LS 為 100 時，WB SLC Cache 的最小大小計算正確。

6. [TC06_WB_Reduction_Boundary_Check]:
   - 動作：計算 Dynamic SLC Upper Bound (25%) 下的 LBA 數量 `ls_by_sector`，進而得出 `expect_value = ls_by_sector * total_node_by_sector // 100`。讀取 40C2 Payload，檢查 Offset [32:35] `max_size_to_reduce_wb_size`。
   - 預期結果：Offset [32:35] 數值必須等於 `expect_value`，確認 WB 緩衝區開始縮減的 LBA 閾值計算正確。

7. [TC07_WB_Available_Size_Full_Check]:
   - 動作：格式化卡，配置 WB 大小，啟用 WB 並禁用 Flush。寫入兩倍 WB 大小的資料以填滿緩衝區。讀取 40C2 Payload，檢查 Offset [36:39] `wb_available_size`。
   - 預期結果：Offset [36:39] 數值必須為 `0`，確認 WB 緩衝區已完全佔用，無可用空間。

8. [TC08_WB_Available_Size_Poll_Check]:
   - 動作：啟用 WB Flush 旗標，輪詢讀取 Attribute `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 直到數值為 `0xA`。隨後讀取 40C2 Payload，檢查 Offset [36:39] `wb_available_size`。
   - 預期結果：Offset [36:39] 數值必須恢復為初始配置的 `config_wb_size_lba`，確認 Flush 機制正確釋放 WB 緩衝區空間。

9. [TC09_Normal_Invalid_VB_Count_Check]:
   - 動作：透過 `get_vb_group_size('FREE_BLK_QUEUE_MLC')` 獲取 Normal 區域的 Free VB 計數。讀取 40C2 Payload，檢查 Offset [40:43] `invalid_vb_cnt_normal`。
   - 預期結果：Offset [40:43] 數值必須等於 `FREE_BLK_QUEUE_MLC` 的計數，確認 Invalid Pool 中的 VB 計數與 Free Queue 一致。

10. [TC10_Used_SLC_VB_Count_Check]:
    - 動作：配置 WB，啟用 WB，寫入 1 個 SLC VB 大小的資料。讀取 40C2 Payload，檢查 Offset [44:47] `used_slc_vb_cnt`。
    - 預期結果：Offset [44:47] 數值必須為 `1`，確認 Used SLC VB 計數正確反映已寫入且非 Open 的 SLC VB 數量。

11. [TC11_Used_TLC_VB_Count_Check]:
    - 動作：禁用 WB，寫入 1 個 TLC VB 大小的資料。讀取 40C2 Payload，檢查 Offset [48:51] `used_tlc_vb_cnt`。
    - 預期結果：Offset [48:51] 數值必須為 `1`，確認 Used TLC VB 計數正確反映已寫入且非 Open 的 TLC VB 數量。

12. [TC12_SLC_Stale_Zone_Count_Check]:
    - 動作：啟用 WB，再寫入 1 個 SLC VB 大小的資料（總共 2 個 SLC VB 被寫入）。讀取 40C2 Payload，檢查 Offset [52:55] `used_vb_cnt_in_slc_stale_zone_list`。
    - 預期結果：Offset [52:55] 數值必須為 `2`，確認 SLC Stale Zone 列表中包含最近寫入的 2 個 SLC VB。

13. [TC13_Normal_Open_VB_VC0_Count_Check]:
    - 動作：呼叫 `get_open_vb_vc_0_cnt('normal')` 計算 Normal 區域中 `first_free_page == 0` 的 Open VB 數量。讀取 40C2 Payload，檢查 Offset [56:59] `vb_cnt_in_LOCKED_SRC_and_cnt_of_open_vb_normal`。
    - 預期結果：Offset [56:59] 數值必須等於計算出的 Open VB VC0 數量，確認該欄位正確統計了 LOCKED_SRC 與 Open VB 的總和。

14. [TC14_WB_Stale_Zone_Size_LS0_LS100_Check]:
    - 動作：讀取 40C2 Payload，檢查 Offset [60:63] `wb_slc_cache_stale_zone_size_ls0` 與 Offset [64:67] `wb_slc_cache_stale_zone_size_ls100`。
    - 預期結果：Offset [60:63] 必須等於 Offset [28:31] (`wb_slc_cache_vb_size_ls100`)；Offset [64:67] 必須等於 Offset [24:27] (`wb_slc_cache_vb_size_ls0`)，確認 Stale Zone 大小與對應 LS 下的 Cache 大小互換邏輯正確。

15. [TC15_Normal_IGC_Trigger_Flag_Check]:
    - 動作：讀取 40C2 Payload，檢查 Offset [68:71] `flag_show_IGC_trigger_in_normal`。
    - 預期結果：該欄位數值必須為 `0`，確認當前 Normal 區域未滿足 IGC 觸發條件。

16. [TC16_Normal_IGC_Remaining_VPs_Check]:
    - 動作：禁用 WB，獲取當前 Used TLC VB 計數 `used_tlc_vb_cnt`。計算 `expect_value = (mlc_threshold - used_tlc_vb_cnt) * TLC_VB_4K_SIZE`。讀取 40C2 Payload，檢查 Offset [72:75] `VPs_be_written_to_trigger_IGC_in_normal`。
    - 預期結果：Offset [72:75] 數值必須等於 `expect_value`，確認觸發 IGC 前剩餘可寫入的 VP 數量計算正確。

17. [TC17_Normal_LOCKED_SRC_Empty_Check]:
    - 動作：讀取 40C2 Payload，檢查 Offset [76:79] `vb_cnt_in_LOCKED_SRC_list_for_normal` 與 Offset [80:83] `start_filling_GC_target_with_dummy_in_normal`。
    - 預期結果：Offset [76:79] 必須為 `0`；Offset [80:83] 必須為 `0`，確認無 GC 執行時，Locked Source 列表為空且未開始填充 Dummy 值。

18. [TC18_EM1_BG_GC_Threshold_Check]:
    - 動作：配置 LUN 為 EM1 (SLC) 佔用全部 AU。讀取 40C2 Payload，檢查 Offset [88:91] `start_bg_gc_vb_cnt_em1` 與 Offset [92:95] `stop_bg_gc_vb_cnt_em1`。
    - 預期結果：兩者數值均必須等於 `slc_threshold`，確認 EM1 區域的 BG GC 閾值設定正確。

19. [TC19_EM1_FG_GC_Threshold_Check]:
    - 動作：讀取 40C2 Payload，檢查 Offset [96:99] `start_fg_gc_vb_cnt_em1`。
    - 預期結果：該欄位數值必須等於 `slc_threshold`，確認 EM1 區域的 FG GC 閾值設定正確。

20. [TC20_EM1_Invalid_VB_Count_Check]:
    - 動作：透過 `get_vb_group_size('FREE_BLK_QUEUE_SLC')` 獲取 EM1 區域的 Free VB 計數。讀取 40C2 Payload，檢查 Offset [104:107] `invalid_vb_cnt_em1`。
    - 預期結果：Offset [104:107] 數值必須等於 `FREE_BLK_QUEUE_SLC` 的計數。

21. [TC21_EM1_Open_VB_VC0_Count_Check]:
    - 動作：讀取 40C2 Payload，檢查 Offset [108:111] `vb_cnt_in_LOCKED_SRC_and_cnt_of_open_vb_em1`。
    - 預期結果：該欄位數值必須為 `0`，確認當前無相關的 Open VB 或 Locked Source。

22. [TC22_EM1_IGC_Remaining_VPs_Check]:
    - 動作：獲取當前 Used SLC VB 計數 `used_slc_vb_cnt`。計算 `expect_value = (slc_threshold - used_slc_vb_cnt) * SLC_VB_4K_SIZE`。讀取 40C2 Payload，檢查 Offset [116:119] `VPs_be_written_to_trigger_IGC_in_em1`。
    - 預期結果：Offset [116:119] 數值必須等於 `expect_value`。

23. [TC23_EM1_LOCKED_SRC_Empty