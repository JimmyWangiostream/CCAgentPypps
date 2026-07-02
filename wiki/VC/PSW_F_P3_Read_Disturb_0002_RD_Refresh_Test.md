# Test Spec: UFS Read Disturb Refresh Booking & Execution Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Read Disturb 機制下的完整生命週期行為：
1. **RC 注入與觸發**：確認透過 Vendor Command 將特定 LUN (Normal/TLC, EM1, WB/SLC) 的 VB Read Count (RC) 強制設為 `0xFFFFFFFF-1` 後，執行讀取操作能正確觸發韌體內部狀態更新。
2. **Booking Queue 優先級邏輯**：確認當 RC 達到臨界值時，韌體能將對應 VB 正確加入 Refresh Booking Queue，且必須符合 `RD_SCAN_BOOKING_1` 使用者標記與 `HighPriority` 優先級，排除非目標 VB 的誤入。
3. **Refresh 執行與計數一致性**：確認透過 Vendor Command 啟動 Refresh 並等待 Bkops Idle 後，Enhanced Health Report 中對應 LUN 類型（EM1, Normal TLC, Normal SLC, Table）的 `read_disturb_refresh_start_count` 欄位數值，必須精確增加等於該類型下被注入 RC 的 VB 總數量，證明 Refresh 任務已針對所有目標 VB 正確執行。

## Test Case (TC) Checkpoints

1. [Step1_Data_Creation_and_Config]：
   - 動作：
     1. 初始化 LUN 配置：LUN 0 設為 Normal (TLC), LUN 1 設為 EM1, LUN 2 設為 WB (SLC)。
     2. 在 LUN 0 (Normal) 寫入 `int(tlc_vb_size * 2.5)` 大小的資料。
     3. 在 LUN 1 (EM1) 寫入 `int(slc_vb_size * 2.5)` 大小的資料。
     4. 啟用 Write Booster (`WRITEBOOSTER_EN=1`, `WRITEBOOSTER_BUFFER_FLUSH_EN=0`)，在 LUN 2 (WB) 寫入 `int(slc_vb_size * 2.5)` 大小的資料，隨後關閉 Write Booster。
     5. 讀取初始 Enhanced Health Report (`VU 40FE`) 並儲存為 `health_report_before`。
   - 預期結果：所有 LUN 寫入成功；LUN 0, 1, 2 均擁有足夠的 VB 空間供後續測試使用；初始健康報告狀態記錄完成。

2. [Step2_Stop_Refresh]：
   - 動作：發送 Vendor Command `C088`，參數設定為 `StopRefresh` (`VUC088Paremeter.StopRefreshRefreshCanStillBeEnqueue`)。
   - 預期結果：韌體停止自動背景 Refresh 流程，確保後續手動注入 RC 時不會被自動背景任務干擾或提前執行 Refresh。

3. [Step3_RC_Injection_and_Validation]：
   - 動作：
     1. 獲取所有 VB 的當前 Read Count (`VU 4097`)。
     2. 根據 VB 類型映射表 (`type_to_field`)，識別出屬於 `CURRENT_L2_EM1`, `USED_BLK_POOL_EM1`, `CURRENT_L2_TLC`, `USED_BLK_POOL_TLC`, `CURRENT_L2_TLC_WB`, `USED_BLK_POOL_TLC_WB`, `PTE_POOL`, `CURRENT_PTE` 的 VB 列表。
     3. 構建 Payload，將上述列表中的 VB Read Count 設為 `0xFFFFFFFF-1`，其他 VB 保持原值。
     4. 透過 Vendor Command 寫入 Payload 更新所有 VB 的 Read Count。
     5. 讀回 Read Count 並驗證目標 VB 的值確實為 `0xFFFFFFFF-1`。
     6. 計算預期增加的 Refresh 計數：`expected_refresh_increase` 字典中，每個類型對應的計數等於該類型下被修改的 VB 數量。
   - 預期結果：目標 VB 的 Read Count 精確寫入 `0xFFFFFFFF-1`；非目標 VB 保持不變；`expected_refresh_increase` 準確反映各 LUN 類型下被觸發的 VB 總數。

4. [Step4_Read_Triggers_RC_Update]：
   - 動作：對之前寫入的資料執行 `api.read_compare` (讀取並比較)，隨後讀取所有 VB 的 Read Count。
   - 預期結果：韌體內部邏輯識別到 RC 接近最大值，為後續 Booking 做準備；讀取操作完成且無資料錯誤。

5. [Step5_Booking_Queue_Verification]：
   - 動作：
     1. 發送 Vendor Command `40C5` 獲取 Refresh Booking Queue (`booking_q`)。
     2. 驗證 `LogicalVBNumberInBookingQueue` 不為 0。
     3. 遍歷 Queue 中的每一個 VB 條目：
        - 驗證該 VB 必須存在於步驟 3 設定的 `refresh_vbs` 列表中。
        - 解析 `TheBookingUser` 欄位，驗證其優先級位元 (`& 0x700`) 對應 `HighPriority`。
        - 驗證 `TheBookingUser` 的低階位元對應 `RD_SCAN_BOOKING_1`。
        - 將驗證通過的 VB 從 `refresh_vbs` 列表中移除。
     4. 驗證 `refresh_vbs` 列表最終為空。
   - 預期結果：
     - Queue 中所有 VB 均為步驟 3 中 RC 被設為 `0xFFFFFFFF-1` 的目標 VB。
     - 所有 Queue 條目的優先級均為 `HighPriority`。
     - 所有 Queue 條目的 Booking User 均為 `RD_SCAN_BOOKING_1`。
     - 沒有遺漏任何目標 VB，也沒有混入非目標 VB。

6. [Step6_Start_Refresh_and_Wait]：
   - 動作：
     1. 發送 Vendor Command `C088`，參數設定為 `StartRefresh` (`VUC088Paremeter.StartRefresh`)。
     2. 呼叫 `polling_bkops_idle()` 等待 Bkops 操作完成並進入 Idle 狀態。
   - 預期結果：韌體開始執行 Refresh 任務，並最終返回 Idle 狀態，表示所有 Booking Queue 中的 VB 已處理完畢。

7. [Step7_Health_Report_Increase_Check]：
   - 動作：
     1. 發送 Vendor Command `40FE` 讀取 Enhanced Health Report (`health_report`)。
     2. 比對 `health_report` 與 `health_report_before`。
     3. 針對以下四個欄位分別驗證數值增加量：
        - `read_disturb_refresh_start_count_em1`
        - `read_disturb_refresh_start_count_normal_tlc`
        - `read_disturb_refresh_start_count_normal_slc`
        - `read_disturb_refresh_start_count_table`
     4. 驗證每個欄位的實際增加量 (`current.value - before.value`) 必須嚴格等於步驟 3 中計算的 `expected_refresh_increase[type]`。
   - 預期結果：
     - `read_disturb_refresh_start_count_em1` 增加量 == EM1 類型 VB 數量。
     - `read_disturb_refresh_start_count_normal_tlc` 增加量 == Normal TLC 類型 VB 數量。
     - `read_disturb_refresh_start_count_normal_slc` 增加量 == Normal SLC (WB) 類型 VB 數量。
     - `read_disturb_refresh_start_count_table` 增加量 == Table (PTE) 類型 VB 數量。
     - 證明韌體已針對所有 RC 觸發的 VB 正確執行了 Refresh 操作，且計數器更新正確。