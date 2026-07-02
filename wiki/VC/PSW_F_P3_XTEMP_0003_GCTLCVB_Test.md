# Test Spec: XTEMP Thermal Refresh & Risky Type Transition Verification

## Verification Criterion (VC)
驗證韌體 XTEMP 熱管理機制在 NAND 溫度變化時的 VB (Virtual Block) 狀態遷移與刷新行為：
1. **Hot Risky 觸發與刷新**：確認當 NAND 溫度設定高於 `XTEMP_Refresh_T2` 閾值時，系統標記 VB 為 "Hot Risky"；當溫度回落至安全區（低於 `XTEMP_Refresh_T1` 且扣除緩衝區）時，該 Hot VB 必須進入 Booking Queue (User ID `0x0214`) 並最終刷新為 Free Block。
2. **Cold Risky 觸發與刷新**：確認當 NAND 溫度設定低於 `XTEMP_Refresh_T1` 閾值時，系統標記 VB 為 "Cold Risky"；當溫度回升至安全區（高於 `XTEMP_Refresh_T1` 且加上緩衝區）時，該 Cold VB 必須進入 Booking Queue 並最終刷新為 Free Block。
3. **Risky Type 動態切換**：確認在無 WB 分區情境下，先寫入資料產生 Hot Risky VB，隨後將溫度降至 Cold Risky 區間，原 Hot VB 的 Risky Type 應正確切換為 Cold Risky 並進入刷新流程；反之亦然，驗證韌體能根據當前溫度動態更新 VB 的風險標籤而非僅依賴創建時的狀態。

## Test Case (TC) Checkpoints

1. [Case01_Hot_Risky_Refresh_Check]：
   - 動作：
     1. 配置 LUN0 為 Normal 記憶體類型並啟用 Write Booster (WB) 分區。
     2. 透過 Vendor Command 將所有 VB 的 EC (Error Correction) 值設為 `XTEMP_ENABLE_PEC * 100` 以啟用 XTEMP 演算法。
     3. 執行 HW_RESET 並重新初始化。
     4. 透過 VU 0xD08A 將 NAND 溫度設定為 `XTEMP_Refresh_T2 + 1`，觸發 "Hot Risky" 狀態。
     5. 等待 `XTEMP_TIME_DETECTION_VALUE` 時間後，透過連續寫入填滿 WB Buffer 並觸發 Flush，強制產生新的 TLC VB。
     6. 輪詢 VU 0x40C1 獲取 `open_logical_VB_number_for_Normal_Defrag_GC_Open_VB_TLC`，確認其 Risky Type 為 `RiskyType.HOT_GROUP`。
     7. 將 NAND 溫度設定為 `XTEMP_Refresh_T2 - XTEMP_TEMP_BUFFER - 1` (安全區)。
     8. 等待檢測時間後，檢查 Booking Queue (VU 0x40C5)，確認該 VB 的 Booking User 為 `0x0214` (`XTEMP_BOOKING | BOOKING_IN_MP`)。
     9. 輪詢該 VB 的 Group 狀態，直到其變更為 `VB_group_for_list.FREE_BLK_QUEUE_MLC`。
   - 預期結果：
     - 在溫度設定為安全區後，原 Hot Risky VB 必須出現在 Booking Queue 中，且 `TheBookingUser` 欄位值嚴格等於 `0x0214`。
     - 該 VB 的 Group 狀態必須從 `CURRENT_DATA_GC_BLK_MLC` 或類似活躍狀態，最終變更為 `FREE_BLK_QUEUE_MLC`，代表 XTEMP 刷新機制成功將該 VB 標記為無風險並回收。

2. [Case02_Cold_Risky_Refresh_Check]：
   - 動作：
     1. 保持 LUN0 配置不變。
     2. 透過 VU 0xD08A 將 NAND 溫度設定為 `XTEMP_Refresh_T1 - 1`，觸發 "Cold Risky" 狀態。
     3. 等待檢測時間後，透過連續寫入填滿 WB Buffer 並 Flush，產生新的 TLC VB。
     4. 輪詢 VU 0x40C1 獲取 Open GC VB，確認其 Risky Type 為 `RiskyType.COLD_GROUP`。
     5. 將 NAND 溫度設定為 `XTEMP_Refresh_T1 + XTEMP_TEMP_BUFFER + 1` (安全區)。
     6. 等待檢測時間後，檢查 Booking Queue (VU 0x40C5)，確認該 VB 的 Booking User 為 `0x0214`。
     7. 輪詢該 VB 的 Group 狀態，直到其變更為 `VB_group_for_list.FREE_BLK_QUEUE_MLC`。
   - 預期結果：
     - 在溫度設定為安全區後，原 Cold Risky VB 必須出現在 Booking Queue 中，且 `TheBookingUser` 欄位值嚴格等於 `0x0214`。
     - 該 VB 的 Group 狀態必須最終變更為 `FREE_BLK_QUEUE_MLC`，代表 Cold Risky 狀態下的 XTEMP 刷新機制運作正常。

3. [Case03_Risky_Type_Transition_Hot_to_Cold_Check]：
   - 動作：
     1. 重新配置 LUN0 為 Normal 記憶體類型，**禁用** Write Booster 分區 (`WB_partition = False`)。
     2. 執行 HW_RESET。
     3. 設定溫度為 `XTEMP_Refresh_T2 + 1` (Hot Risky)，寫入 5 個 TLC VB 大小的資料。
     4. 獲取所有 Risky Type 為 "Hot" 的 VB 列表 (`Hot_VB_list`)。
     5. 將溫度設定為 `XTEMP_Refresh_T1 - 1` (Cold Risky)。
     6. 輪詢 Booking Queue，確認 `Hot_VB_list` 中的 VB 依序進入 Queue，且 `TheBookingUser` 為 `0x0214`。
     7. 確認進入 Queue 的 VB 數量與 `Hot_VB_list` 長度一致，且順序符合預期（最小 VB 優先）。
     8. 等待所有刷新完成 (`polling_xtemp_refresh_done`)。
     9. 獲取刷新後的 VB 列表，確認其 Risky Type 已變更為 "Cold" (`Cold_VB_list`)，且數量與 `Hot_VB_list` 相同。
   - 預期結果：
     - 當溫度從 Hot 區間切換至 Cold 區間時，原本標記為 Hot Risky 的 VB 必須被重新評估，其 Risky Type 標籤應從 `RiskyType.HOT_GROUP` 切換為 `RiskyType.COLD_GROUP`。
     - 這些 VB 必須正確進入 Booking Queue 進行刷新，且 `TheBookingUser` 必須為 `0x0214`。
     - 刷新完成後，這些 VB 的 Risky Type 應維持為 Cold (因為當前溫度仍在 Cold 區間)，驗證韌體能動態更新 VB 的風險屬性。

4. [Case04_Risky_Type_Transition_Cold_to_Hot_Check]：
   - 動作：
     1. 保持 LUN0 無 WB 分區配置。
     2. 寫入 5 個 TLC VB 大小的資料。
     3. 獲取所有 Risky Type 為 "Cold" 的 VB 列表 (`Cold_VB_list`)。
     4. 將溫度設定為 `XTEMP_Refresh_T2 + 1` (Hot Risky)。
     5. 輪詢 Booking Queue，確認 `Cold_VB_list` 中的 VB 依序進入 Queue，且 `TheBookingUser` 為 `0x0214`。
     6. 確認進入 Queue 的 VB 數量與 `Cold_VB_list` 長度一致。
     7. 等待所有刷新完成。
     8. 獲取刷新後的 VB 列表，確認其 Risky Type 已變更為 "Hot" (`Hot_VB_list`)，且數量與 `Cold_VB_list` 相同。
   - 預期結果：
     - 當溫度從 Cold 區間切換至 Hot 區間時，原本標記為 Cold Risky 的 VB 必須被重新評估，其 Risky Type 標籤應從 `RiskyType.COLD_GROUP` 切換為 `RiskyType.HOT_GROUP`。
     - 這些 VB 必須正確進入 Booking Queue 進行刷新，且 `TheBookingUser` 必須為 `0x0214`。
     - 刷新完成後，這些 VB 的 Risky Type 應維持為 Hot (因為當前溫度仍在 Hot 區間)，驗證韌體在溫度反向變化時的風險標籤切換邏輯正確無誤。