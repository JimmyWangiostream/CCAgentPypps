# Test Spec: UFS Refresh Unit Granularity & Method Control Logic Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 Refresh Unit 設定為 Slice (0) 且 Refresh Method 設定為 Force (1) 時，Refresh 進度的計數邏輯與狀態機行為：Case 01 確認在空閒狀態下 `dRefreshProgress` 為 0；Case 02 確認寫入 TLC 與 SLC 資料後，啟用 Refresh 並輪詢 `bRefreshStatus` 至完成 (03h) 後歸零 (00h)，且 `dRefreshProgress` 嚴格增加 `100000 / Total VB Count` 的固定增量，驗證 Slice 級別的 Refresh 粒度；Case 03 確認 Reconfig 後進度重置為 0；Case 04 確認當 `bRefreshMethod` 設為 0 (Undefined) 時，強制啟用 Refresh Flag 會觸發 General Failure (0xFF)，驗證 Method 參數對 Refresh 執行的約束機制。

## Test Case (TC) Checkpoints
1. [Case01_Initial_RefreshState_Check]：
   - 動作：執行 `pre_process` 計算 TLC/SLC VB 大小，呼叫 `config_lun` 配置 LUN0 (Normal), LUN1/2 (Boot), LUN3 (EM1), LUN4 (WriteBooster)。寫入屬性 `REFRESH_UNIT = 0` (Slice 模式) 與 `REFRESH_METHOD = 1` (Force 模式)。讀取 Device Health Descriptor，提取偏移量 41-44 的 `dRefreshProgress` 與 37-40 的 `dRefreshCount`。
   - 預期結果：`dRefreshProgress` 必須等於 0，代表裝置尚未開始或已完成 Refresh 循環，初始狀態乾淨。

2. [Case02_Data_Write_Refresh_Granularity_Check]：
   - 動作：
     1. 關閉 WriteBooster，寫入 LUN0 (Normal) 總長度為 `1.5 * TLC_VB_4K_SIZE` 的隨機資料。
     2. 寫入 LUN3 (EM1) 總長度為 `1.5 * SLC_VB_4K_SIZE` 的資料。
     3. 開啟 WriteBooster，寫入 LUN4 (WB) 總長度為 `1.5 * SLC_VB_4K_SIZE` 的資料，隨後關閉 WriteBooster。
     4. 再次讀取 `dRefreshProgress` 記錄為 `refreshProgress_step3`。
     5. 設定 Flag `REFRESH_EN = 1` 啟動 Refresh。
     6. 輪詢讀取屬性 `REFRESH_STATUS`，直到值為 3 (Refresh In Progress) 後繼續輪詢，直到值變為 0 (Refresh Completed/Idle)。
     7. 讀取最終 `dRefreshProgress` 記錄為 `refreshProgress_step6`。
   - 預期結果：
     - `REFRESH_STATUS` 必須經歷 1 (Idle/Ready) -> 3 (In Progress) -> 0 (Completed) 的狀態轉換。
     - `dRefreshProgress` 的增量 `refreshProgress_step6 - refreshProgress_step3` 必須精確等於 `(1 * 100000) // self.fw_geometry.l52_total_vb_count`。這驗證了在 Slice 模式下，Refresh 進度是基於總 VB 數量的線性累加，且每次完整循環或特定觸發對應固定的進度百分比增量。

3. [Case03_Reconfig_Reset_Check]：
   - 動作：呼叫 `config_lun` 重新配置 LUN 結構。讀取 Device Health Descriptor，提取 `dRefreshProgress`。
   - 預期結果：`dRefreshProgress` 必須等於 0。驗證 LUN 重配置操作會觸發韌體內部狀態重置，清除之前的 Refresh 進度標記。

4. [Case04_Method_Control_Failure_Check]：
   - 動作：寫入屬性 `REFRESH_METHOD = 0` (Undefined/Not Defined)。嘗試透過 `SetFlag` 命令設定 `REFRESH_EN = 1`。使用 `sendcmd_keeperror` 獲取回應碼。
   - 預期結果：回應碼 `b6_query_response` 必須等於 `0xFF` (General Failure)。驗證當 Refresh 方法未定義時，硬體/韌體拒絕執行 Refresh 操作，並返回標準錯誤碼，確保系統不會在無效配置下執行潛在的危險操作。