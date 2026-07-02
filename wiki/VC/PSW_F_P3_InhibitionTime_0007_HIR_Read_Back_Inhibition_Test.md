# Test Spec: UFS HIR (Host Initiated Refresh) Inhibition Time & GC Trigger Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 Host Initiated Refresh (HIR) 機制下的時序控制與垃圾回收 (GC) 觸發行為：
1. **HIR 觸發與 Read-Back 機制**：確認在設定 `REFRESH_UNIT=1` 與 `REFRESH_METHOD=1` 並寫入特定容量資料（1.5x TLC VB Size）後，HIR 能正確觸發 Read-Back 流程，且 `bRefreshStatus` 必須從 01h (In Progress) 變更為 03h (Completed)，同時 Device Health Descriptor 中的 `RefreshProgress` 與 `RefreshCount` 數值必須發生預期變化。
2. **Inhibition Time 鎖定機制**：確認在 HIR 觸發後，韌體內部變數 `gInhibitMgr.lock` 必須為 1，阻止後續 HIR 重複觸發。
3. **Inhibition 解除與二次觸發**：確認經過硬體設定的 `INHIBITION_TIME` 秒數後，`gInhibitMgr.lock` 必須自動變更為 0，此時再次觸發 HIR 應能成功再次觸發 Read-Back 流程，證明抑制計時器機制運作正常。

## Test Case (TC) Checkpoints

1. [Case01_HIR_Trigger_ReadBack_Check]：
   - 動作：
     1. 執行 `power_cycle`（隨機選擇 HW_RESET 帶或不帶 Power Down）並進入 Vendor Mode。
     2. 讀取硬體設定 `api.HwSettingField.INHIBITION_TIME` 並備份為 `backup_inhibition_time_sec`。
     3. 讀取 FW 變數 `gInhibitMgr.lock`，確認初始狀態為 1（鎖定狀態）。
     4. 呼叫 `trigger_hir()`：
        - 執行 `reconfig_to_erase_all_lun()` 清除 `refreshprogress`。
        - 設定 `api.AttributeIDN.REFRESH_UNIT = 1` 與 `api.AttributeIDN.REFRESH_METHOD = 1`。
        - 讀取 Device Health Descriptor，記錄 `refreshProgress_before` (偏移 0x29-0x2C) 與 `refreshCount_before` (偏移 0x25-0x28)。
        - 對 LUN 0 寫入總長度為 `1.5 * TLC_VB_4K_SIZE` 的資料（使用 `random_chunk=True` 混合大小區塊）。
        - 設定 `api.FlagIDN.REFRESH_EN` 標誌。
     5. 呼叫 `check_hir_trigger()`：
        - 輪詢讀取 `api.AttributeIDN.REFRESH_STATUS`，直到數值等於 03h 或逾時 15 分鐘。
        - 讀取 Device Health Descriptor，記錄 `refreshProgress_after` 與 `refreshCount_after`。
   - 預期結果：
     - `gInhibitMgr.lock` 初始值必須為 1。
     - `bRefreshStatus` 最終必須等於 03h (HIR 完成)。
     - `refreshProgress_after` 與 `refreshCount_after` 必須與 Before 數值不同，證明 Read-Back 流程已執行並更新健康狀態。

2. [Case02_Inhibition_Lock_Verification]：
   - 動作：
     1. 在 Case 01 完成後，立即讀取 FW 變數 `gInhibitMgr.lock`。
   - 預期結果：
     - `gInhibitMgr.lock` 必須等於 1。
     - 這代表 HIR 觸發後，系統進入抑制狀態，防止立即重複觸發 HIR。

3. [Case03_Inhibition_Time_Expiry_Second_HIR_Check]：
   - 動作：
     1. 執行 `time.sleep(self.inhibition_time_sec)`，等待硬體設定的抑制時間過去。
     2. 讀取 FW 變數 `gInhibitMgr.lock` 兩次（間隔 10ms），確認狀態穩定。
     3. 再次呼叫 `trigger_hir()` 執行第二次 HIR 觸發流程（包含寫入資料與設定 Flags）。
     4. 再次呼叫 `check_hir_trigger()` 檢查 HIR 狀態。
   - 預期結果：
     - 第一次讀取的 `gInhibitMgr.lock` 必須等於 0，代表抑制計時器已歸零，鎖定解除。
     - 第二次 HIR 觸發後，`bRefreshStatus` 必須再次成功變更為 03h。
     - 這證明 Inhibition Time 機制正確運作，允許在時間到期後重新觸發 HIR。