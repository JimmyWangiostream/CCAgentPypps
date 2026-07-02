# Test Spec: UFS Xtemp Thermal Management & VB Risky Type Refresh Test

## Verification Criterion (VC)
驗證 UFS 韌體中 Xtemp 溫度管理機制對 VB (Virtual Block) 風險標記 (Risky Type) 的影響及自動修復行為：
1. **Safe 狀態驗證**：在 NAND 溫度處於 Safe 區間時，新寫入的 VB 必須標記為 `SAFE_GROUP` (0x00)，且 Xtemp Booking Queue 中不得出現 `XTEMP_BOOKING` (0x200) 使用者。
2. **Hot Risky 標記與觸發驗證**：當 NAND 溫度升高至 `XTEMP_REFRESH_T2 + 1` 時，新寫入的 VB 必須標記為 `HOT_GROUP` (0x02)；隨後溫度回落至 Safe 區間但未觸發刷新條件前，該 Hot VB 保持 `HOT_GROUP` 標記且 Booking Queue 為空；當溫度進一步降低至觸發刷新閾值（`XTEMP_REFRESH_T2 - XTEMP_TEMP_BUFFER - 1`）後，韌體應啟動 MP Refresh 機制，將所有 Hot VB 標記清除為 `SAFE_GROUP`，並透過 Booking Queue 機制確保刷新完成。
3. **Cold Risky 標記與觸發驗證**：當 NAND 溫度降低至 `XTEMP_REFRESH_T1 - 1` 時，新寫入的 VB 必須標記為 `COLD_GROUP` (0x01)；隨後溫度回升至 Safe 區間但未觸發刷新條件前，該 Cold VB 保持 `COLD_GROUP` 標記；當溫度進一步升高至觸發刷新閾值（`XTEMP_REFRESH_T1 + XTEMP_TEMP_BUFFER + 1`）後，韌體應啟動 MP Refresh 機制，將所有 Cold VB 標記清除為 `SAFE_GROUP`。
4. **Booking Queue 機制驗證**：在 Refresh 過程中，系統必須透過 Vendor Command 0x40C5 查詢到的 Booking Queue 中，存在 `TheBookingUser` 為 `0x200` (XTEMP_BOOKING | BOOKING_IN_MP) 的 VB 記錄，且該記錄數量應與待刷新 VB 數量一致，並在刷新完成後歸零。

## Test Case (TC) Checkpoints

1. [Case01_Safe_Write_Verification]：
   - 動作：初始化 LUN0 為 Normal 類型並擦除，透過 Vendor Command 0x0F (GET_FW_GEOMETRY) 寫入 EC 值以啟用 Xtemp 算法並執行 HW_RESET。設定 NAND 溫度為 Safe 區間（預設或初始狀態），寫入 1 個 TLC VB Size 的資料。讀取 VB 資訊，檢查新寫入 VB 的 `risky_type` 欄位（bits 18-19），並查詢 Booking Queue。
   - 預期結果：新寫入 VB 的 `risky_type` 必須等於 `0x00` (SAFE_GROUP)；Booking Queue 中 `TheBookingUser` 為 `0x200` 的 VB 數量必須為 0。

2. [Case02_Hot_Risky_Marking]：
   - 動作：將 NAND 溫度設定為 `XTEMP_REFRESH_T2 + 1`（觸發 Hot 風險區間），等待 `2 * XTEMP_TIME_DETECTION_VALUE` 時間讓韌體檢測到溫度變化。接著寫入 1 個 TLC VB Size 的資料。讀取 VB 資訊，檢查新寫入 VB 的 `risky_type` 欄位。
   - 預期結果：新寫入 VB 的 `risky_type` 必須等於 `0x02` (HOT_GROUP)；Booking Queue 中 `TheBookingUser` 為 `0x200` 的 VB 數量必須為 0（表示尚未觸發刷新，僅標記風險）。

3. [Case03_Hot_Risky_Persistence_Before_Refresh]：
   - 動作：將 NAND 溫度設定為 `XTEMP_REFRESH_T2`（Safe 區間，但未達到觸發刷新的低溫閾值），等待檢測時間。讀取 VB 資訊，檢查之前標記為 Hot 的 VB 狀態，並查詢 Booking Queue。
   - 預期結果：之前標記為 Hot 的 VB 其 `risky_type` 仍必須保持為 `0x02` (HOT_GROUP)；Booking Queue 中 `TheBookingUser` 為 `0x200` 的 VB 數量必須為 0（表示未進入 Refresh 流程）。

4. [Case04_Hot_Refresh_Triggered]：
   - 動作：將 NAND 溫度設定為 `XTEMP_REFRESH_T2 - XTEMP_TEMP_BUFFER - 1`（低於觸發刷新的低溫閾值），等待檢測時間。讀取 VB 資訊，檢查所有 VB 的 `risky_type` 欄位，並輪詢查詢 Booking Queue 直到 `TheBookingUser` 為 `0x200` 的 VB 數量歸零。
   - 預期結果：所有 VB 的 `risky_type` 必須全部變更為 `0x00` (SAFE_GROUP)；Booking Queue 中 `TheBookingUser` 為 `0x200` 的 VB 數量最終必須為 0，且刷新過程在 1 分鐘內完成。

5. [Case05_Cold_Risky_Marking]：
   - 動作：將 NAND 溫度設定為 `XTEMP_REFRESH_T1 - 1`（觸發 Cold 風險區間），等待檢測時間。寫入 1 個 TLC VB Size 的資料。讀取 VB 資訊，檢查新寫入 VB 的 `risky_type` 欄位。
   - 預期結果：新寫入 VB 的 `risky_type` 必須等於 `0x01` (COLD_GROUP)；Booking Queue 中 `TheBookingUser` 為 `0x200` 的 VB 數量必須為 0。

6. [Case06_Cold_Risky_Persistence_Before_Refresh]：
   - 動作：將 NAND 溫度設定為 `XTEMP_REFRESH_T1`（Safe 區間，但未達到觸發刷新的高溫閾值），等待檢測時間。讀取 VB 資訊，檢查之前標記為 Cold 的 VB 狀態，並查詢 Booking Queue。
   - 預期結果：之前標記為 Cold 的 VB 其 `risky_type` 仍必須保持為 `0x01` (COLD_GROUP)；Booking Queue 中 `TheBookingUser` 為 `0x200` 的 VB 數量必須為 0。

7. [Case07_Cold_Refresh_Triggered]：
   - 動作：將 NAND 溫度設定為 `XTEMP_REFRESH_T1 + XTEMP_TEMP_BUFFER + 1`（高於觸發刷新的高溫閾值），等待檢測時間。讀取 VB 資訊，檢查所有 VB 的 `risky_type` 欄位，並輪詢查詢 Booking Queue 直到 `TheBookingUser` 為 `0x200` 的 VB 數量歸零。
   - 預期結果：所有 VB 的 `risky_type` 必須全部變更為 `0x00` (SAFE_GROUP)；Booking Queue 中 `TheBookingUser` 為 `0x200` 的 VB 數量最終必須為 0，且刷新過程在 1 分鐘內完成。