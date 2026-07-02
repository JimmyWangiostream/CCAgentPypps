# Test Spec: UFS FTL Read Count (RC) & Threshold (RC_TH) Persistence and Dynamic Scan Verification

## Verification Criterion (VC)
驗證 FTL 韌體中 Virtual Block (VB) 的讀取計數器 (Read Count, RC) 與讀取計數閾值 (Read Count Threshold, RC_TH) 在多種電源狀態轉換下的持久性與動態掃描機制：
1. **持久性驗證**：確認在 HW_RESET (POR) 後，透過 Vendor Command (C071) 或 API 設定的 RC 與 RC_TH 值能正確寫入並持久化至非易失性儲存區，且在韌體重新初始化後讀回數值與設定值誤差在允許範圍內（Buffer=2）。
2. **動態掃描驗證 (Case 01)**：確認在無 SSU Sleep 情境下，透過 Vendor Command C071 設定的 `sgs_scan_dynamic_read_count` 與 `sgs_scan_static_read_count` 能觸發 FTL 的動態讀取計數掃描機制，導致 VB 的 RC 值隨實際讀取操作累積增加。
3. **電源管理驗證 (Case 02)**：確認在 SSU Sleep (Power Condition 0x02) 與 Wake-up (Power Condition 0x01) 循環後，RC 與 RC_TH 值保持不變（因未觸發動態掃描），且硬體狀態恢復正常。

## Test Case (TC) Checkpoints
1. [Case01_POR_Persistence_and_Dynamic_Scan_Check]：
   - 動作：
     1. 針對 Normal LUN (LUN 0) 寫入約 4.5 個 TLC VB 大小的資料，針對 EM1 LUN (LUN 1) 寫入約 4.5 個 SLC VB 大小的資料，建立測試區塊並記錄 LBA 與 VB 的對應關係。
     2. 遍歷所有 VB，透過 `project_api.set_specific_VB_read_count_threshold` 設定隨機的 RC_TH 值（範圍 0xFFFF0000-0xFFFFFFF0），並透過 `project_api.set_all_VB_read_count` 設定隨機的 RC 初始值（範圍 1-0xFFF00000）。
     3. 執行 HW_RESET (POR, powerdown=True) 重置系統。
     4. 讀取韌體中的 RC 與 RC_TH 表，驗證數值與設定值一致（誤差 <= 2）。
     5. 對測試 LBA 進行 10-100 次隨機重複讀取，預期 RC 值增加。
     6. 發送 Vendor Command C071，設定 `sgs_scan_dynamic_read_count` 與 `sgs_scan_static_read_count` 為隨機整數乘以 100,000 (NUM_100K)，觸發動態掃描參數更新。
     7. 輪詢等待 BKOPS 進入 Idle 狀態。
     8. 執行 HW_RESET (SPOR, powerdown=False) 模擬軟性掉電重啟。
     9. 再次讀取 RC 與 RC_TH，驗證數值是否反映讀取操作後的累積值。
   - 預期結果：
     - POR 後：RC 與 RC_TH 必須等於初始設定值（誤差 <= 2），證明持久化機制正常。
     - SPOR 後：RC 值必須等於「初始設定值 + 重複讀取次數」，證明 C071 設定的動態掃描參數生效，且 RC 計數器正確累加；RC_TH 值必須保持不變（除非被其他機制修改，但此處主要驗證 RC 累積）。若 RC 未增加或 RC_TH 丟失，則測試失敗。

2. [Case02_POR_Persistence_and_SSU_Sleep_Check]：
   - 動作：
     1. 重複步驟 1 中的資料寫入與 RC/RC_TH 隨機設定。
     2. 執行 HW_RESET (POR, powerdown=True) 重置系統。
     3. 讀取韌體中的 RC 與 RC_TH 表，驗證數值與設定值一致（誤差 <= 2）。
     4. 對測試 LBA 進行 10-100 次隨機重複讀取，預期 RC 值增加。
     5. 發送 UFS 標準命令 StartStopUnit (SSU)，設定 `power_condition=0x02` (Sleep) 進入睡眠，隨後發送 `power_condition=0x01` (Wake-up) 喚醒，並等待隊列清空。
     6. 輪詢等待 BKOPS 進入 Idle 狀態。
     7. 執行 HW_RESET (SPOR, powerdown=False) 模擬軟性掉電重啟。
     8. 再次讀取 RC 與 RC_TH，驗證數值是否反映讀取操作後的累積值。
   - 預期結果：
     - POR 後：RC 與 RC_TH 必須等於初始設定值（誤差 <= 2）。
     - SPOR 後：RC 值必須等於「初始設定值 + 重複讀取次數」，證明即使在 SSU Sleep/Wake 循環後，RC 計數器依然正確累加且數據未丟失；RC_TH 值必須保持不變。此 Case 用於排除 SSU 電源管理對 RC 持久化的干擾，並確認未觸發 C071 動態掃描參數更新時的行為一致性。