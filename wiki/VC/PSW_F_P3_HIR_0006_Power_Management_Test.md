# Test Spec: UFS Refresh Mechanism & Power State Persistence Verification

## Verification Criterion (VC)
驗證 UFS 裝置在執行背景 Refresh 操作後，其狀態機與計數器在不同電源狀態（H8 Hibernate, SLEEP, POWER DOWN）及重置類型（POR with SSU, SPOR without SSU）下的持久化行為與恢復邏輯：
1. **Refresh 機制驗證**：確認在 `bRefreshUnit=0` 設定下，Refresh 進度 (`dRefreshProgress`) 以總 VB 數量的 1/100% 為單位遞增，且 `bRefreshStatus` 正確反映 Idle/Running/Complete 狀態。
2. **電源狀態持久性**：驗證在 H8、SLEEP、POWER DOWN 狀態切換後，Refresh 相關屬性（Progress, Count, Unit, Method, Status）保持不變，證明這些狀態不觸發 Refresh 重置或中斷。
3. **重置後狀態恢復**：
   - **POR (SSU)**：硬體重啟並執行 Secure Storage Unit 流程後，`bRefreshStatus` 歸零，但 `dRefreshProgress` 與 `dRefreshTotalCount` 必須保留重置前的值，證明韌體從非揮發性儲存恢復了 Refresh 進度。
   - **SPOR (No SSU)**：硬體重啟但無 SSU 流程後，行為應與 POR 一致，確認 Refresh 進度存儲於非揮發性區域而非易失性 RAM。
4. **Refresh Unit 變更影響**：當 `bRefreshUnit` 從 0 改為 1 並完成一次新的 Refresh 循環後，執行 SPOR 重置，驗證 `dRefreshProgress` 被清零（因為 Unit 變更導致舊進度失效或新循環開始），而 `dRefreshTotalCount` 遞增 1，證明每次完整的 Refresh 周期都會增加總計數。

## Test Case (TC) Checkpoints
1. [Step1_RefreshInit_Check]：
   - 動作：配置 LUN 0,1,2,3,4（LUN1/2為Boot, LUN3為EM1, LUN0/4為Normal），設定 `bRefreshUnit=0`, `bRefreshMethod=1`。讀取 Device Health Descriptor，確認初始 `bRefreshProgress` 為 0。
   - 預期結果：`bRefreshProgress` 必須等於 0，確認系統處於 Refresh 初始狀態。

2. [Step2_DataWrite_Check]：
   - 動作：
     - 關閉 Write Booster，寫入 LUN 0 共 1.5 個 TLC VB 大小的資料（隨機 chunk）。
     - 寫入 LUN 3 (EM1) 共 1.5 個 SLC VB 大小的資料。
     - 開啟 Write Booster，寫入 LUN 4 共 1.5 個 SLC VB 大小的資料，隨後關閉 Write Booster。
   - 預期結果：寫入操作成功完成，無錯誤返回，為後續 Refresh 建立足夠的資料分佈以觸發背景整理。

3. [Step3_RefreshExecution_Check]：
   - 動作：設定 `REFRESH_EN` Flag，輪詢讀取 `bRefreshStatus` 暫存器，直到數值為 `0x03` (Complete)。記錄完成時的 `dRefreshProgress` 與 `dRefreshTotalCount`。
   - 預期結果：`bRefreshStatus` 最終必須等於 `0x03`，代表 Refresh 操作已順利完成。

4. [Step5_RefreshStatusReset_Check]：
   - 動作：在 Refresh 完成後，再次讀取 `bRefreshStatus`。
   - 預期結果：`bRefreshStatus` 必須等於 `0x00`，代表 Refresh 閒置狀態。

5. [Step6_RefreshProgressIncrement_Check]：
   - 動作：讀取完成後的 `dRefreshProgress`。計算預期增量 `increase_val = (1 * 100 * 1000) // total_vb_count`。比較當前 Progress 與 Step 3 的 Progress。
   - 預期結果：`refreshProgress_step6 - refreshProgress_step3` 必須嚴格等於 `increase_val`。這驗證了在 `bRefreshUnit=0` 模式下，每次 Refresh 循環僅推進總容量的 1/1000 (0.1%)。

6. [Step8_PowerState_Persistence_Check]：
   - 動作：針對以下 6 種情境分別執行：
     - **LV1_ATS_H8**：Idle `ats_time` 秒後，進入/退出 H8 (Hibernate)。
     - **LV1_ATS_WO_H8**：Idle `ats_time` 秒後，無電源狀態變化。
     - **LV2_SLEEP_H8**：發送 `StartStopUnit` (Power Condition `0x02`, SLEEP) 後，進入/退出 H8。
     - **LV2_SLEEP_WO_H8**：發送 `StartStopUnit` (Power Condition `0x02`, SLEEP) 後，無 H8。
     - **LV2_POWERDOWN_H8**：發送 `StartStopUnit` (Power Condition `0x03`, POWER DOWN) 後，進入/退出 H8。
     - **LV2_POWERDOWN_WO_H8**：發送 `StartStopUnit` (Power Condition `0x03`, POWER DOWN) 後，無 H8。
     每次情境結束後，讀取 `dRefreshProgress`, `dRefreshTotalCount`, `bRefreshUnit`, `bRefreshStatus`, `bRefreshMethod` 並與 Step 6 的值進行比對。
   - 預期結果：所有讀取的屬性值必須與 Step 6 的值完全一致。這證明 H8、SLEEP 和 POWER DOWN 狀態不會導致 Refresh 進度丟失或重置。

7. [Step11_POR_RefreshPersistence_Check]：
   - 動作：執行 `HW_RESET` 且 `powerdown=True` (模擬 POR with SSU)。重置後讀取 `dRefreshProgress`, `dRefreshTotalCount`, `bRefreshUnit`, `bRefreshStatus`, `bRefreshMethod`。
   - 預期結果：
     - `bRefreshStatus` 必須等於 `0x00`。
     - `dRefreshProgress` 必須等於 Step 8 的值（進度保留）。
     - `dRefreshTotalCount` 必須等於 Step 8 的值（計數保留）。
     - `bRefreshUnit` 和 `bRefreshMethod` 必須保持不變。
     這驗證了 SSU 流程下，Refresh 狀態是持久化的。

8. [Step13_SPOR_RefreshPersistence_Check]：
   - 動作：執行 `HW_RESET` 且 `powerdown=False` (模擬 SPOR without SSU)。重置後讀取相同屬性。
   - 預期結果：行為必須與 Step 11 完全一致，所有 Refresh 相關屬性值必須保留，證明即使沒有 SSU，Refresh 進度也存儲在非揮發性記憶體中。

9. [Step19_SPOR_AfterRefreshUnitChange_Check]：
   - 動作：
     - 重新配置 LUN。
     - 設定 `bRefreshUnit=1`。
     - 觸發一次完整的 Refresh 循環（等待 `bRefreshStatus` 變為 `0x03` 後歸零）。
     - 執行 `HW_RESET` 且 `powerdown=False` (SPOR)。
     - 讀取屬性。
   - 預期結果：
     - `bRefreshUnit` 必須等於 `1`。
     - `bRefreshMethod` 必須等於 `1`。
     - `bRefreshStatus` 必須等於 `0x00`。
     - `dRefreshProgress` 必須等於 `0`（因為 Unit 變更導致舊進度無效，或新循環從頭開始）。
     - `dRefreshTotalCount` 必須等於 Step 13 的值加 1（證明完成了一次新的 Refresh 周期）。

10. [Step21_POR_AfterRefreshUnitChange_Check]：
    - 動作：在 Step 19 的狀態下，執行 `HW_RESET` 且 `powerdown=True` (POR with SSU)。讀取屬性。
    - 預期結果：
      - `dRefreshProgress` 必須等於 Step 19 的值（即 0）。
      - `dRefreshTotalCount` 必須等於 Step 19 的值。
      - 其他屬性 (`bRefreshUnit`, `bRefreshMethod`, `bRefreshStatus`) 必須與 Step 19 一致。
      這驗證了在 Unit 變更並完成新循環後，POR 同樣能正確恢復狀態。