# Test Spec: UFS Media Scan Booking Queue Priority & Skip Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Media Scan 機制下的 Booking Queue 排程邏輯與優先級處理：
1. **Booking Queue 正確性**：確認透過 Vendor Command `C087` 將特定 VB (Virtual Block) 以 `HighPriority` 加入 Booking Queue 後，透過 `40C5` 查詢的 Queue 狀態（LogicalVBNumberInBookingQueue, BookingQueueVB 欄位）必須精確反映該 VB 號碼，且 Bitmask 必須同時包含 `VU_REFRESH` 與 `BOOKING_IN_HP` 標誌。
2. **Media Scan 跳過機制**：確認當 Media Scan 被啟用且透過 `C085` 設定極長的掃描間隔（`last_scan_spend_time = 0x1000000`）以觸發 Idle 觸發機制時，若目標 VB 已存在於 Booking Queue 中，韌體必須在掃描過程中自動跳過該 VB。驗證指標為 `40CF` 回報的 `scanned_blocks` 列表中絕對不包含該目標 VB，且 `cur_scan_vb` 最終歸零，代表掃描流程正常結束且未對已預訂區塊進行重複掃描。

## Test Case (TC) Checkpoints

1. **[BookingQueue_Priority_Verification]**：
   - 動作：
     1. 透過 `C08B` 禁用 Media Scan。
     2. 針對指定的 `test_blk_type`（如 `CURRENT_L2_MLC`, `CURRENT_PTE` 等），執行 `config_lun_and_create_target_blk` 建立對應的 LUN 與 VB 區塊（例如對 LUN 0 寫入 TLC_WL_block 大小資料以建立 MLC 區塊，或寫入 4096 節點以觸發 PTE 刷新）。
     3. 透過 `get_target_vb_list` 獲取該區塊對應的 Logical VB 號碼 (`target_vb`)。
     4. 透過 `C088` 停止當前 Refresh 執行但允許入隊。
     5. 透過 `C087` 將 `target_vb` 以 `HighPriority` 用戶身份加入 Booking Queue。
     6. 透過 `40C5` 讀取 Booking Queue 狀態。
   - 預期結果：
     - `booking_q_before.LogicalVBNumberInBookingQueue.value` 必須等於 `1`。
     - `booking_q_before.BookingQueueVB[0].value` 的 Bitmask 必須同時滿足 `(value & VU_REFRESH) == VU_REFRESH` 且 `(value & BOOKING_IN_HP) == BOOKING_IN_HP`。
     - `booking_q_before.BookingQueueVB[0].LogicalVBNumber.value` 必須精確等於 `target_vb`。
     - 若上述任一條件不符，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. **[MediaScan_Skip_BookingVB_Verification]**：
   - 動作：
     1. 透過 `C08B` 重新啟用 Media Scan。
     2. 透過 `C085` 設定 Media Scan 參數，將 `last_scan_spend_time` 設為 `0x1000000`，並發送指令觸發 Idle 狀態下的 Media Scan 流程。
     3. 進入輪詢迴圈，每 5 秒透過 `40CF` 讀取 Media Scan 狀態（包含 `cur_scan_vb`, `cur_scan_page`, `scan_group`, `scanned_blocks`）。
     4. 持續監控直到 `cur_scan_vb == 0xFFFFFFFF` 且 `cur_scan_page == 0xFFFFFFFF`，表示掃描完成或重置。
     5. 在掃描完成後，遍歷 `payload.scanned_blocks` 列表。
   - 預期結果：
     - 迴圈必須正常結束（無死鎖或超時）。
     - 在 `payload.scanned_blocks` 列表中，**絕對不能**包含 `target_vb`。
     - 若發現 `scanned_vb == target_vb`，代表韌體未正確識別 Booking Queue 中的高優先級區塊，導致重複掃描，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 此驗證確保了當 VB 已被預訂（Booked）時，Media Scan 引擎會正確跳過該區塊，避免資源衝突或效能浪費。