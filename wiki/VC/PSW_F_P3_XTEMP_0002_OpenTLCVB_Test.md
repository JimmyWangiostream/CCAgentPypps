# Test Spec: Xtemp Manager Temperature Threshold & VB Risky Type Refresh Logic

## Verification Criterion (VC)
驗證韌體 Xtemp Manager 在不同 NAND 溫度閾值（T1/T2）與平均擦寫次數（EC）條件下，對 VB（Virtual Block）Risky Type 標記與 MP（Manufacturing Process）Refresh 機制的精確控制：
1. **Hot Risky 觸發與保留**：當設定 EC 低於閾值且溫度高於 T2+1 時，新寫入 VB 標記為 Hot Risky；若溫度回落至 T2，Hot Risky 標記應保留且觸發 Booking Queue（User ID 0x200 | 0x200），不立即清除。
2. **Hot Risky 清除機制**：當溫度進一步降低至 T2 - Buffer - 1 時，觸發 Hot2Safe Refresh，所有 Hot Risky VB 標記清除並恢復為 Safe。
3. **Cold Risky 觸發與保留**：當設定 EC 達到閾值且溫度低於 T1-1 時，新寫入 VB 標記為 Cold Risky；若溫度回升至 T1，Cold Risky 標記應保留且觸發 Booking Queue，不立即清除。
4. **Cold Risky 清除機制**：當溫度進一步升高至 T1 + Buffer + 1 時，觸發 Cold2Safe Refresh，所有 Cold Risky VB 標記清除並恢復為 Safe。
5. **Booking Queue 驗證**：在 Refresh 觸發前，Booking Queue 中必須存在 User ID 為 `XTEMP_BOOKING (0x20)` 且 `BOOKING_IN_MP (0x200)` 的 VB 列表；Refresh 完成後，該列表應為空。

## Test Case (TC) Checkpoints

1. [Case01_Hot_Risky_Trigger_Check]：
   - 動作：配置 LUN0 為 2GB Normal LUN。讀取 mConfig 中的 `XTEMP_ENABLE_PEC` 與 `XTEMP_REFRESH_T2`。透過 Vendor Command (GET_FW_GEOMETRY) 將所有 VB 的 EC 設定為 `XTEMP_ENABLE_PEC * 100 - 1`（低於觸發閾值）。執行 HW_RESET 並設定 NAND 溫度為 `XTEMP_REFRESH_T2 + 1`。等待 `2 * XTEMP_TIME_DETECTION_VALUE` 後，順序寫入 1.5 倍 TLC VB Size 資料。
   - 預期結果：`refresh_behavior_check` 驗證新建立的 Used VB 與 Open VB 之 `RiskyType` 均為 `SAFE_GROUP` (0)。此步驟旨在確認在低 EC 下，即使高溫也不會標記為 Hot Risky，作為基準控制組。

2. [Case02_Hot_Risky_Marking_Check]：
   - 動作：格式化 LUN0 清除狀態。透過 `write_data_to_increase_avg_ec` 將平均 EC 提升至 `XTEMP_ENABLE_PEC * 100`。執行 HW_RESET。設定 NAND 溫度為 `XTEMP_REFRESH_T2 + 1`。等待檢測時間後，順序寫入 1 倍 TLC VB Size 資料。
   - 預期結果：`refresh_behavior_check` 驗證新建立的 Used VB 與 Open VB 之 `RiskyType` 均為 `HOT_GROUP` (1)。確認在高 EC 與高溫條件下，韌體正確將 VB 標記為 Hot Risky。

3. [Case03_Hot_Risky_Booking_Queue_Check]：
   - 動作：在 Case02 狀態下（溫度維持 `XTEMP_REFRESH_T2 + 1`，VB 已標記為 Hot Risky），執行 `get_booking_Q` 檢查 Booking Queue。接著將溫度設定為 `XTEMP_REFRESH_T2`（降至觸發 Refresh 閾值以下，但未觸發 Refresh）。
   - 預期結果：`get_booking_Q` 返回的 `xtemp_user_count` 必須大於 0。檢查 Queue 中的 `TheBookingUser` 欄位數值必須等於 `XTEMP_BOOKING (0x20) | BOOKING_IN_MP (0x200)`。確認韌體已將 Hot Risky VB 加入 MP Refresh 佇列，但尚未執行實際的標記清除動作。

4. [Case04_Hot2Safe_Refresh_Check]：
   - 動作：在 Case03 狀態下，將 NAND 溫度設定為 `XTEMP_REFRESH_T2 - XTEMP_TEMP_BUFFER - 1`。等待檢測時間後，執行 `refresh_behavior_check` 並指定 `refresh_behavior = RefreshBehavior.Hot2Safe`。
   - 預期結果：韌體觸發 Hot2Safe Refresh 流程。`polling_xtemp_refresh_done` 確認 Refresh 完成。驗證所有 VB 的 `RiskyType` 變更為 `NA` (0) 或 `SAFE_GROUP` (0)。`get_booking_Q` 返回的 `xtemp_user_count` 必須為 0。確認 Hot Risky 標記已被成功清除。

5. [Case05_Cold_Risky_Trigger_Check]：
   - 動作：設定 NAND 溫度為 `XTEMP_REFRESH_T1 - 1`（低於 Cold 觸發閾值）。順序寫入 1 倍 TLC VB Size 資料。
   - 預期結果：`refresh_behavior_check` 驗證新建立的 Used VB 與 Open VB 之 `RiskyType` 均為 `COLD_GROUP` (2)。確認在低 EC（由 Case02 維持）與低溫條件下，韌體正確將 VB 標記為 Cold Risky。

6. [Case06_Cold_Risky_Booking_Queue_Check]：
   - 動作：在 Case05 狀態下（溫度維持 `XTEMP_REFRESH_T1 - 1`，VB 已標記為 Cold Risky），將溫度設定為 `XTEMP_REFRESH_T1`（升至觸發 Refresh 閾值以下，但未觸發 Refresh）。
   - 預期結果：`get_booking_Q` 返回的 `xtemp_user_count` 必須大於 0。檢查 Queue 中的 `TheBookingUser` 欄位數值必須等於 `XTEMP_BOOKING (0x20) | BOOKING_IN_MP (0x200)`。確認韌體已將 Cold Risky VB 加入 MP Refresh 佇列。

7. [Case07_Cold2Safe_Refresh_Check]：
   - 動作：在 Case06 狀態下，將 NAND 溫度設定為 `XTEMP_REFRESH_T1 + XTEMP_TEMP_BUFFER + 1`。等待檢測時間後，執行 `refresh_behavior_check` 並指定 `refresh_behavior = RefreshBehavior.Cold2Safe`。
   - 預期結果：韌體觸發 Cold2Safe Refresh 流程。`polling_xtemp_refresh_done` 確認 Refresh 完成。驗證所有 VB 的 `RiskyType` 變更為 `NA` (0) 或 `SAFE_GROUP` (0)。`get_booking_Q` 返回的 `xtemp_user_count` 必須為 0。確認 Cold Risky 標記已被成功清除。