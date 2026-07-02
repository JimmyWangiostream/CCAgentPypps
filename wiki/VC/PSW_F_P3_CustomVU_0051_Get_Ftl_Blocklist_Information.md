# Test Spec: UFS FTL Block List Consistency & PB Status Verification (VU 406D vs 4099)

## Verification Criterion (VC)
驗證韌體內部 FTL 區塊管理資訊的一致性與物理區塊（Physical Block, PB）狀態標記的正確性：
1. **列表一致性檢查**：透過 Vendor Command 0x406D 取得的 VB (Virtual Block) 列表與 Vendor Command 0x4099 取得的 FTL Block 列表進行比對，確認 `blk_cnt`、`blk_head`、`blk_tail` 數值完全一致，且 0x4099 剩餘 Payload 必須為全 `0xFF`。
2. **PB 狀態位元檢查**：針對 0x4099 回應中的 Event Log 與 MMSEG Log 所列出的物理區塊，透過 Vendor Command `direct_read` 讀取該 PB 的第一頁（Page 0, offset 128+4*4K）與最後一頁（Page 1103, offset 128+4*4K）的狀態頁（Status Page）。
   - **PB Status 0 (Close)**：Page 0 與 Page 1103 的狀態值必須均為 `0x00`。
   - **PB Status 1 (Open)**：Page 0 狀態值必須為 `0x00`，且 Page 1103 的 Bit 4 必須為 `1`。
   - **PB Status 2 (Invalid)**：Page 0 的 Bit 4 與 Page 1103 的 Bit 4 必須均為 `1`。

## Test Case (TC) Checkpoints
1. [VB_List_Consistency_Check]：
   - 動作：
     1. 呼叫 `issue_406D_get_VB_list_info` 獲取 VB 列表，解析 `vb_info_list`（包含 `blk_cnt`, `blk_head`, `blk_tail`）。
     2. 呼叫 `issue_4099_to_get_ftl_blk_list(0)` 獲取 FTL Block 列表，解析 `blk_info.payload`。
     3. 遍歷 `vb_info_list`，將每個 VB 的計數與範圍與 0x4099 payload 中對應偏移量（每次增加 12 bytes）的 `blk_cnt`、`blk_head`、`blk_tail` 進行逐項比對。
     4. 檢查 0x4099 payload 中所有已使用欄位之後的剩餘資料是否全為 `0xFF`。
   - 預期結果：
     - 若 `vb_info.blk_cnt > 0`：`vb_info.blk_cnt` 必須等於 `blk_cnt`，`vb_info.blk_head` 必須等於 `blk_head`，`vb_info.blk_tail` 必須等於 `blk_tail`。
     - 若 `vb_info.blk_cnt == 0`：對應的 `blk_cnt` 必須為 `0` 或 `0xFFFFFFFF`，且 `blk_head` 與 `blk_tail` 必須均為 `0xFFFFFFFF`。
     - 剩餘 Payload 必須全部為 `0xFF`。若任何一項不符，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [PB_Status_EventLog_Verification]：
   - 動作：
     1. 從 0x4099 回應結構中取得 `event_log_pb_cnt`。
     2. 從 Payload 偏移量 `8` 開始，依序讀取 `event_log_pb_cnt` 個物理區塊位置資訊（每個 4 bytes）。
     3. 對每個區塊位置資訊，解析 `MmesgBlkLocation` 結構，提取 `block_number_of_physical_blk`、`die_number_of_physical_blk`、`plane_number_of_physical_blk` 及 `pb_status`。
     4. 根據 `pb_status` 值，構造 PCA 結構並執行 `vendor_cmd.direct_read`：
        - 讀取 Page 0 (l12_fpage=0) 的 Status Page 資料（Payload 索引 `128 + 4*4096`）。
        - 讀取 Page 1103 (l12_fpage=1103) 的 Status Page 資料（Payload 索引 `128 + 4*4096`）。
     5. 根據 `pb_status` 執行以下位元檢查：
        - 若 `pb_status == 0`：`read_status_page0` 必須為 `0` 且 `read_status_last_page` 必須為 `0`。
        - 若 `pb_status == 1`：`read_status_page0` 必須為 `0` 且 `read_status_last_page` 的 Bit 4 必須為 `1`。
        - 若 `pb_status == 2`：`read_status_page0` 的 Bit 4 必須為 `1` 且 `read_status_last_page` 的 Bit 4 必須為 `1`。
   - 預期結果：所有 Event Log 中的物理區塊狀態位元檢查必須通過，否則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

3. [PB_Status_MMSEGLog_Verification]：
   - 動作：
     1. 計算 MMSEG Log 的數量：`mmseg_cnt = amount_double_word_of_product_output - event_log_pb_cnt - 3`。
     2. 計算 MMSEG Log 的起始偏移量：`offset_of_mmseg = 8 + 4 * (event_log_pb_cnt + 1)`。
     3. 從 `offset_of_mmseg` 開始，依序讀取 `mmseg_cnt` 個物理區塊位置資訊。
     4. 對每個區塊執行與 [PB_Status_EventLog_Verification] 相同的 `MmesgBlkLocation` 解析與 `direct_read` 狀態頁檢查邏輯。
   - 預期結果：所有 MMSEG Log 中的物理區塊狀態位元檢查必須通過，否則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。