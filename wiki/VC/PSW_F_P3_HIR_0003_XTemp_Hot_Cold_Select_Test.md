# Test Spec: UFS Background Refresh Unit (0) & Method (2) Temperature Triggered Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 `bRefreshUnit = 0` (單 VB 刷新) 與 `bRefreshMethod = 2` (溫度觸發) 設定下，NAND 溫度跨越特定閾值 (T1/T2) 時，韌體是否正確啟動背景 Refresh 流程：
1. **Case 01 (COLD_RESKY)**：當 NAND 溫度低於 T1 閾值時，確認 `bRefreshStatus` 狀態機從 `01h` (執行中) 正確過渡至 `03h` (完成)，最終歸零；且 `dRefreshProgress` 隨每次單 VB 刷新精確遞增 (步長為 1000000 / Total VB Count)，`dRefreshTotalCount` 在進度歸零時遞增 1。
2. **Case 02 (HOT_RESKY)**：當 NAND 溫度高於 T2 閾值時，確認相同的狀態機過渡與進度計數邏輯，驗證高溫情境下 Refresh 機制同樣被正確觸發且計數準確。

## Test Case (TC) Checkpoints
1. [Case01_Cold_Temp_Refresh_Unit0_Check]：
   - 動作：
     1. 配置 LUN 並寫入 `bRefreshUnit = 0` 與 `bRefreshMethod = 2`。
     2. 讀取 Device Health Descriptor (DHD) 獲取初始 `dRefreshProgress` (Offset 41-44) 與 `dRefreshTotalCount` (Offset 37-40)。
     3. 對所有 4 個 LUN 寫入 4KB 資料以確保有資料可刷新。
     4. 呼叫 `get_T1_T2()` 獲取溫度閾值 T1 與 T2，以及檢測延遲時間 `XTEMP_TIME_DETECTION_VALUE`。
     5. 執行 `set_nand_temp` 將 NAND 溫度設定為 `T1 - 1` (低於冷卻閾值)。
     6. 等待 `XTEMP_TIME_DETECTION_VALUE` 讓韌體檢測到溫度變化。
     7. 輪詢讀取 DHD 中的 `dRefreshProgress`，並透過 `api.set_flag(REFRESH_EN)` 確保 Refresh 使能。
     8. 輪詢讀取 `bRefreshStatus` (Attribute IDN)，預期狀態必須嚴格遵循 `01h` (執行中) -> `03h` (完成) 的順序，若出現其他值則報錯。
     9. 確認 `bRefreshStatus` 最終歸零 (`00h`)。
     10. 讀取最終 DHD，驗證 `dRefreshProgress` 的增量是否等於 `(1000000 / l52_total_vb_count)`，並驗證 `dRefreshTotalCount` 是否比初始值增加 1。
   - 預期結果：
     - `bRefreshStatus` 必須先出現 `01h`，隨後變為 `03h`，最後穩定在 `00h`。
     - `dRefreshProgress` 的數值變化必須精確符合單 VB 刷新的步長計算公式，不得跳躍或錯誤。
     - 當 `dRefreshProgress` 歸零或達到 1000000 時，`dRefreshTotalCount` 必須嚴格等於 `Initial_Count + 1`。
     - 這證明在低溫觸發下，Refresh Unit 0 的單區塊刷新機制運作正常且計數器邏輯正確。

2. [Case02_Hot_Temp_Refresh_Unit0_Check]：
   - 動作：
     1. 重置 LUN 配置與寫入，確保狀態乾淨。
     2. 再次設定 `bRefreshUnit = 0` 與 `bRefreshMethod = 2`。
     3. 讀取初始 DHD 狀態。
     4. 對所有 4 個 LUN 寫入 4KB 資料。
     5. 獲取 T1/T2 閾值。
     6. 執行 `set_nand_temp` 將 NAND 溫度設定為 `T2 + 1` (高於高溫閾值)。
     7. 等待 `XTEMP_TIME_DETECTION_VALUE`。
     8. 輪詢讀取 DHD 並設置 `REFRESH_EN` Flag。
     9. 輪詢讀取 `bRefreshStatus`，驗證狀態機從 `01h` 到 `03h` 再到 `00h` 的轉換。
     10. 驗證最終 `dRefreshProgress` 的增量步長與 `dRefreshTotalCount` 的遞增行為。
   - 預期結果：
     - `bRefreshStatus` 必須嚴格遵循 `01h` -> `03h` -> `00h` 的狀態轉換序列。
     - `dRefreshProgress` 的增量必須精確等於 `(1000000 / l52_total_vb_count)`。
     - 當進度完成時，`dRefreshTotalCount` 必須嚴格等於 `Initial_Count + 1`。
     - 這證明在高溫觸發下，Refresh 機制同樣被正確啟動，且不受溫度極端值影響計數邏輯的準確性。