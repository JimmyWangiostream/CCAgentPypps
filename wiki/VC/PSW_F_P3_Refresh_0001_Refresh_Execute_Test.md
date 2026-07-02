# Test Spec: UFS FTL Refresh Mechanism & Booking Queue Integrity Test

## Verification Criterion (VC)
驗證 UFS 韌體在 Host 透過 Vendor Command (C087/C088) 介入 Refresh 流程時的狀態機行為：
1. **Booking Queue 隔離性**：確認在 `StopRefresh` (C088) 狀態下，Host 發送的 Refresh 請求能正確進入 Booking Queue 且不被立即執行；同時驗證 SSU Sleep (0x02) 與 Power Down (0x03) 循環不會導致 Booking Queue 內容丟失或重置。
2. **Refresh 執行與 VB 遷移**：確認啟動 Refresh (C088 Start) 後，韌體能正確處理 Queue 中的 VB 請求，將指定的 L2 (SLC/TLC)、L1 及 PTE VB 從 `CURRENT_*` 狀態遷移至對應的 `FREE_BLK_QUEUE_*` 狀態，並更新 Open VB 指針。
3. **資料完整性與健康計數**：驗證 Refresh 完成後，原始寫入資料經 HW Compare 無誤，且 Enhanced Health Report 中對應的 Read Reclaim Count (SLC Table, TLC, EM1) 嚴格增加，證明物理區塊已確實被回收並標記為 Free。

## Test Case (TC) Checkpoints

1. [Case01_Initial_State_Verification]：
   - 動作：針對 SLC LUN 與 TLC LUN 分別寫入 128MB (128M Byte) 資料，隨後在 TLC LUN 的 128MB Offset 處寫入 16KB 資料並設定 FUA=1。讀取當前 Open VB Info，記錄 L2_TLC_VB, L2_SLC_VB, L1_VB, PTE_VB 的 Logical VB Number。透過 `get_VB_group` 確認這四個 VB 目前的 Group 狀態分別為 `CURRENT_PTE`, `CURRENT_L2_MLC`, `CURRENT_L2_SLC`, `CURRENT_L1`。
   - 預期結果：所有指定的 VB 必須處於對應的 Current Group 狀態，代表資料已穩定寫入且 FTL 映射表已更新，為後續 Refresh 測試建立基準狀態。

2. [Case02_BookingQueue_Integrity_During_Power_Cycles]：
   - 動作：
     1. 發送 Vendor Command C088，參數設為 `StopRefreshRefreshCanStillBeEnqueue`，暫停 Refresh 執行但允許入隊。
     2. 發送 Vendor Command C087，將 L2_SLC_VB, L2_TLC_VB 以 Medium Priority 入隊，將 L1_VB, PTE_VB 以 Low Priority 入隊。
     3. 發送 Vendor Command 40C5 讀取 Booking Queue，確認 `LogicalVBNumberInBookingQueue` 等於 4。檢查 Queue 前兩個項目 (MP) 必須包含 `VU_REFRESH` 與 `BOOKING_IN_MP` 標記，後兩個項目 (LP) 必須包含 `VU_REFRESH` 與 `BOOKING_IN_LP` 標記。
     4. 執行 SSU Sleep (Power Condition 0x02) 後 Wake (0x01)。
     5. 執行 SSU Power Down (Power Condition 0x03) 後 Wake (0x01)。
     6. 每次電源循環後，再次發送 40C5 讀取 Booking Queue。
   - 預期結果：
     - 初始入隊後，Queue 長度必須為 4，且每個 Entry 的 Bitmask 必須精確匹配對應的 Priority 與 Refresh 標記。
     - 在 Sleep 與 Power Down 循環後，Booking Queue 的 `LogicalVBNumberInBookingQueue` 值必須保持為 4，且所有 Entry 的數值與 Sleep/Power Down 前完全一致，證明韌體在電源狀態轉換期間正確保留了 Host 提交的 Refresh 請求，未發生資料丟失或重置。

3. [Case03_Refresh_Execution_VB_Migration]：
   - 動作：
     1. 發送 Vendor Command C088，參數設為 `StartRefresh`，啟動 Refresh 執行。
     2. Polling BKOPS 狀態直到 Idle (Timeout 900s)。
     3. 發送 40C5 讀取 Booking Queue，確認 `LogicalVBNumberInBookingQueue` 變為 0。
     4. 讀取所有 VB 的 Group 狀態 (`get_VB_group`) 及 Open VB Info。
   - 預期結果：
     - Booking Queue 必須為空，表示所有請求已處理完畢。
     - 原 L2_TLC_VB 的 Group 必須變更為 `FREE_BLK_QUEUE_MLC`。
     - 原 L2_SLC_VB 的 Group 必須變更為 `FREE_BLK_QUEUE_SLC`。
     - 原 PTE_VB 的 Group 必須變更為 `FREE_BLK_QUEUE_TABLE` 或 `FREE_BLK_QUEUE_SLC`。
     - 原 L1_VB 的 Group 必須變更為 `FREE_BLK_QUEUE_TABLE` (根據代碼邏輯推斷，雖未明確檢查 L1 的 Group 變更為 Free，但檢查了 Open VB 更新)。
     - **關鍵狀態檢查**：Open VB Info 中的 `L2_SLC_VB`, `PTE_VB`, `L1_VB`, `L2_TLC_VB` 的 Logical VB Number 必須全部發生改變（與測試前的值不同），證明 FTL 已將舊 VB 標記為 Free 並分配了新的 VB 給 Open 映射。

4. [Case04_Data_Integrity_Health_Counter_Verification]：
   - 動作：
     1. 對之前寫入的 SLC 與 TLC LUN 資料執行 `read_compare`，使用 `HW_COMPARE` 方法。
     2. 發送 Vendor Command 40FE 讀取 Enhanced Health Report，比對測試前的 Health Report。
   - 預期結果：
     - HW Compare 必須成功，證明 Refresh 過程中的資料搬移 (Read-Reclaim) 未造成資料損壞。
     - Health Report 中的 `read_reclaim_count_for_slc_table`, `read_reclaim_count_for_tlc`, `read_reclaim_count_for_em1` 三個計數器的數值必須嚴格大於測試前的數值，證明 Refresh 操作確實觸發了物理區塊的回收與計數更新。