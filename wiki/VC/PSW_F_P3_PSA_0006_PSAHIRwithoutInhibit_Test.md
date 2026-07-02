# Test Spec: UFS PSA (Power State Awareness) Inhibition Phase & HIR Recovery Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 PSA (Power State Awareness) 流程中，硬體抑制時間 (Inhibition Time) 機制對後回流 (Post-Reflow) 遷移進度的鎖定行為，以及手動強制刷新 (Manual Force Refresh) 後的狀態恢復：
1. **抑制期鎖定驗證**：在 HW_RESET 觸發 PSA 遷移後，於設定的 240 秒抑制時間內，韌體必須嚴格阻止任何 PSA 遷移進度的推進（進度保持 0%），且 `gInhibitMgr.lock` 狀態必須維持為 1，確保在焊接完成前的敏感階段不會發生數據遷移。
2. **手動刷新觸發驗證**：抑制期結束後，透過設定 `REFRESH_EN` Flag 觸發 HIR (Host Initiated Refresh)，驗證韌體能正確執行 SLC PSA 區塊的刷新，並將 `REFRESH_STATUS` 更新為 0x03 (Completed Successfully)。
3. **最終狀態一致性驗證**：刷新完成後，驗證所有 MLC VB (Virtual Block) 的 Trim Type 已從預設狀態重置為 POR (Power-On Reset, 0x00)，代表 PSA 狀態已完全清除並恢復至初始上電狀態。

## Test Case (TC) Checkpoints

1. [Case01_Configuration_and_Inhibition_Setup]：
   - 動作：
     1. 將 LUN0 配置為使用 `ENHANCED_1` 記憶體類型並分配所有 Allocation Units (AU)，驗證 `dPSAMaxDataSize` 屬性必須為 0 (表示不支援 PSA 數據傳輸)。
     2. 執行 Unmap 清除所有 LUN 資料。
     3. 嘗試將 `bPSAState` 寫入 `PRE_SOLDERING`，預期裝置回應 `GENERAL_FAILURE` (0xFF)，因為此時記憶體類型不支援或狀態未就緒。
     4. 將 LUN0 重新配置為 `NORMAL` 記憶體類型並分配所有 AU。
     5. 透過 `HwSetting` 將 `INHIBITION_TIME` 設定為 240 秒。
     6. 設定 `REFRESH_METHOD` 為 `ManualForce` (0x01)，`REFRESH_UNIT` 為 `MinimumRefresh` (0x00)。
     7. 將 `bPSAState` 寫入 `PRE_SOLDERING`，隨後寫入 2 個 SLC VB Size 的資料至 LUN0 (LBA 0 開始)。
     8. 將 `bPSAState` 寫入 `LOADING_COMPLETE`。
     9. 執行 HW_RESET (Power Cycle)。
   - 預期結果：
     - `dPSAMaxDataSize` 讀回值必須等於 0。
     - 寫入 `PRE_SOLDERING` 時，`QueryResponse` 必須為 0xFF。
     - HW_RESET 後，系統進入抑制階段，`inhibit_start_time` 記錄重置時刻。

2. [Case02_Inhibition_Phase_Lock_Verification]：
   - 動作：
     1. 在 HW_RESET 後，立即向 LUN0 寫入 4KB 資料 (LBA 2*SLC_VB_Size 處)。
     2. 啟動輪詢機制，持續 40 秒，每 2 秒透過 Vendor Command 0x405C 讀取 `PSAPostReflowProgress` (獲取 `PercentageForSLCPSAblocks`)，並透過 Vendor Command 0x404F 讀取 `PSAMigrationState` (獲取 `IsPsaOngoing`)。
     3. 同時檢查韌體內部變數 `gInhibitMgr.lock` 的值。
   - 預期結果：
     - 在整個 40 秒期間，`PercentageForSLCPSAblocks` 必須始終等於 0。
     - `IsPsaOngoing` 必須始終等於 0。
     - `gInhibitMgr.lock` 必須始終等於 1。
     - 若任何時刻進度大於 0 或 Lock 不等於 1，則測試失敗，證明抑制機制未生效。

3. [Case03_HIR_Trigger_and_Completion_Verification]：
   - 動作：
     1. 當經過時間超過抑制時間的 90% (即 > 216 秒) 且 `gInhibitMgr.lock` 仍為 1 時，透過 `api.set_flag` 設定 `REFRESH_EN` Flag。
     2. 輪詢讀取 `REFRESH_STATUS` 屬性，直到其值變為 0x03 或超過 1 分鐘超時。
     3. 再次透過 Vendor Command 0x405C 和 0x404F 讀取最終的遷移狀態與進度。
   - 預期結果：
     - `REFRESH_STATUS` 最終必須等於 0x03，代表 Host Initiated Refresh 成功完成。
     - `PercentageForSLCPSAblocks` 必須等於 100。
     - `IsPsaOngoing` 必須等於 0 (表示遷移流程已結束)。

4. [Case04_Final_PSA_State_Reset_Verification]：
   - 動作：
     1. 在刷新完成後，呼叫 `check_vb_mlc_trim` 函數。
     2. 該函數遍歷所有 VB (Virtual Block)，針對 `CURRENT_L2_MLC` (0x07) 和 `USED_BLK_POOL_MLC` (0x11) 群組的 VB，讀取其 Trim Type 欄位。
   - 預期結果：
     - 所有相關 MLC VB 的 `vb_trim` 欄位數值必須等於 `trimtype.POR` (0x00)。
     - 這證明 PSA 流程結束後，所有虛擬區塊的邏輯狀態已正確重置為上電初始狀態，無殘留的 PSA 標記。