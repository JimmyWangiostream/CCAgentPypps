# Test Spec: UFS FTL Refresh Mechanism (Slice Mode) Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 `REFRESH_UNIT = 0` 且 `REFRESH_METHOD = 1` (Slice Mode) 設定下，執行 `REFRESH_EN` 指令時的硬體行為與狀態機轉換：
1. **狀態機同步性**：確認 `bRefreshStatus` 嚴格遵循 `00h` (Idle) -> `01h` (Busy) -> `03h` (Complete) 的硬體狀態轉換，且無異常狀態碼。
2. **進度計數精確性**：確認 `dRefreshProgress` (Device Health Descriptor Offset 41-44) 在每次 Slice 刷新完成後，嚴格增加 `(1 / Total VB Count) * 100000` 的數值，驗證 FTL 內部計數器與硬體報告的一致性。
3. **VB 遷移順序與邏輯**：確認被觸發刷新的 VB (VB Group 發生改變或 Remap 變更) 嚴格遵循韌體定義的優先級順序：`Current VB` -> `OpenVB (TLC/SLC)` -> `Table and System VB` -> `Closed TLC VB` -> `Closed SLC Static (EM1)` -> `Closed SLC Dynamic (WB)`。
4. **總計數器一致性**：確認當 `dRefreshProgress` 歸零或達到 100% 時，`dRefreshTotalCount` (Offset 37-40) 必須嚴格遞增 1，代表一個完整的 Refresh Cycle 結束。

## Test Case (TC) Checkpoints

1. [Case01_Refresh_Init_and_Status_Check]：
   - 動作：
     1. 配置 LUN：LUN0/4 為 Normal，LUN1/2 為 Boot，LUN3 為 EM1 (Enhanced 1)，LUN4 啟用 WriteBooster。
     2. 寫入資料：LUN0 寫入 1.5 個 TLC VB 大小 (隨機 Chunk)，LUN3 寫入 1.5 個 SLC VB 大小，LUN4 (WB En) 寫入 1.5 個 SLC VB 大小。
     3. 設定屬性：透過 `api.write_attribute` 將 `REFRESH_UNIT` 設為 0，`REFRESH_METHOD` 設為 1。
     4. 讀取初始狀態：從 Device Health Descriptor 讀取初始的 `dRefreshProgress` (Offset 41-44) 與 `dRefreshTotalCount` (Offset 37-41)。
     5. 觸發刷新：設定 `FlagIDN.REFRESH_EN`，並輪詢讀取 `AttributeIDN.REFRESH_STATUS`。
   - 預期結果：
     - `REFRESH_STATUS` 必須先變為 `01h` (Busy)，隨後穩定變為 `03h` (Complete)。若出現其他值 (如 02h 或 >3)，則判定為硬體狀態機異常。
     - 初始 `dRefreshProgress` 與 `dRefreshTotalCount` 被成功記錄，作為後續增量比對的基準 (Step4 Values)。

2. [Case02_Slice_Progress_Increment_Check]：
   - 動作：
     1. 在 `REFRESH_STATUS` 為 `03h` 後，再次讀取 Device Health Descriptor 獲取 `refreshProgress_step7` 與 `resfreshCount_step7`。
     2. 計算理論增量：`increase_val = (100 * 1000) // self.fw_geometry.l52_total_vb_count`。
     3. 驗證增量：檢查 `refreshProgress_step7 - refreshProgress_step4` 是否等於 `increase_val`。
   - 預期結果：
     - `refreshProgress_step7` 必須嚴格大於 `refreshProgress_step4`。
     - 差值必須精確等於 `increase_val`。若差值不等於此理論值，代表 FTL 內部 Slice 計數邏輯與硬體報告脫節，驗證失敗。

3. [Case03_VB_Migration_Order_and_Type_Check]：
   - 動作：
     1. 在刷新前 (Step 3) 與刷新後 (Step 8) 分別呼叫 `get_VB_group()` 獲取所有 VB 的詳細資訊，包含 `group` (VB Group Enum), `access_mode`, `remap_vb`, `valid_cnt`。
     2. 執行 `check_vb_after_refresh` 比對前後狀態，找出發生變化的 VB 列表 (`diff_vb`)。
     3. 檢查 `diff_vb` 中第一個變化的 VB (`diff_vb[0]`) 的 `vb_type`。
     4. 記錄該 VB 的類型 (`current_refresh_vb_type`) 並與上一次刷新的 VB 類型 (`last_refresh_vb_type`) 進行比較。
   - 預期結果：
     - `diff_vb` 長度應為 1 (代表每次 Slice 刷新僅處理一個 VB)。
     - `current_refresh_vb_type` 的數值必須大於或等於 `last_refresh_vb_type` (依據 `VBTYPE` Enum 定義：Current=0, OpenVB=1, Table=2, ClosedTLC=3, ClosedSLCStatic=4, ClosedSLCDynamic=5)。
     - 這驗證了 FTL 嚴格按照 `Current -> Open -> Table -> Closed` 的優先級順序進行資料遷移與刷新，未跳過高優先級 VB。

4. [Case04_Cycle_Completion_and_TotalCount_Check]：
   - 動作：
     1. 持續循環執行 Step 4-7，直到 `refreshProgress_step7` 等於 `100000` (100%) 或 `0` (重置)。
     2. 在循環終止條件滿足時，讀取當前的 `resfreshCount_step7` 與 Step 1 記錄的 `resfreshCount_step4`。
     3. 檢查 `refreshProgress_step7` 是否超過 `100000`。
   - 預期結果：
     - `refreshProgress_step7` 絕不能大於 `100000`。
     - `resfreshCount_step7` 必須嚴格等於 `resfreshCount_step4 + 1`。
     - 這確認了當進度條跑滿一圈後，硬體的全局刷新總計數器正確遞增，標誌著一個完整的 Refresh Cycle 結束，且無計數溢出或遺漏。