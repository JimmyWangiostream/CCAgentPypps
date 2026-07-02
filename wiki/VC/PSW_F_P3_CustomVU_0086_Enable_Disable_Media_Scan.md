# Test Spec: UFS Media Scan Control & Persistence Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Media Scan (媒體掃描) 機制的狀態控制、觸發條件及重置後的持久化行為：
1. **DM_Bg_Task_In_Bank 關聯性**：確認當 `DM_Bg_Task_In_Bank` (背景任務) 被禁用時，即使滿足掃描觸發條件，Media Scan 也不會啟動；當該標誌恢復啟用且滿足條件時，掃描必須立即啟動。
2. **Vendor Command 控制權**：確認透過 Vendor Command `0xC08B` 強制禁用/啟用 Media Scan 後，系統狀態與 `0x40CF` 查詢結果的一致性。
3. **Reset 類型對狀態的影響**：驗證不同 Reset 類型對 Media Scan 狀態位的影響差異——`HW_RESET` 與 `RESET_N` (電源循環) 會清除禁用狀態並恢復為 Enable (0x00)，而 `ENDPOINT_RESET` 與 `UNIPRO_RESET` (軟重置) 則保留禁用狀態 (0x01)。
4. **掃描中斷與恢復 (Resume)**：驗證在掃描過程中強制禁用掃描後，韌體是否正確記錄當前 `cur_scan_vb` 與 `cur_scan_page`；當重新啟用掃描時，是否從該精確位置繼續掃描，而非重置或跳過。

## Test Case (TC) Checkpoints

1. **[Case01_DM_Disable_Prevents_Scan]**：
   - 動作：透過 `issue_D018_Disable_Enable_DM_Bg_Task_In_Bank(flag=True)` 禁用背景任務；配置 LUN 並寫入 SLC/TLC 各一個 VB 大小資料；透過 `issue_C085` 設定 `last_scan_spend_time = 0x1000000` 以滿足觸發條件；輪詢 `issue_40CF` 獲取 `cur_scan_vb`, `cur_scan_page`, `scan_group`，持續監控 60 秒。
   - 預期結果：在 60 秒內，`cur_scan_vb`, `cur_scan_page`, `scan_group` 的數值必須與初始讀取值完全相同，不得發生任何變化。這證明當 `DM_Bg_Task_In_Bank` 為 False 時，韌體不會啟動 Media Scan 背景工作。

2. **[Case02_Reset_Triggers_Scan_With_DM_Disabled]**：
   - 動作：在 Case01 狀態下（DM 禁用，掃描未啟動），執行 `api.init_tester_to_unit_ready` 進行 HW_RESET、RESET_N、ENDPOINT_RESET 或 UNIPRO_RESET 四種重置；重置後立即讀取 `issue_40CF` 獲取當前掃描狀態 (`old_scan_vb`, `old_scan_page`)；接著透過 `issue_C085` 將 `last_scan_spend_time` 設為 `0x2000000` (確保滿足觸發閾值)；延遲 1 秒後再次讀取 `issue_40CF` 獲取新狀態 (`new_scan_vb`, `new_scan_page`)。
   - 預期結果：`new_scan_vb` 或 `new_scan_page` 必須與重置前的 `old_scan_vb`/`old_scan_page` 不同。這證明即使背景任務曾被禁用，Reset 後的韌體初始化流程會重新評估掃描條件，並在滿足條件時啟動掃描。

3. **[Case03_DM_Enable_Triggers_Scan]**：
   - 動作：禁用背景任務 (`flag=True`)，寫入資料，設定 `last_scan_spend_time = 0x1000000`，確認 60 秒內掃描未啟動；讀取當前狀態為 `old_scan_vb`；接著執行 `issue_D018_Disable_Enable_DM_Bg_Task_In_Bank(flag=False)` 啟用背景任務；設定 `last_scan_spend_time = 0x8000000`；延遲 1 秒後讀取新狀態 `new_scan_vb`。
   - 預期結果：`new_scan_vb` 必須不等於 `old_scan_vb`。這證明當 `DM_Bg_Task_In_Bank` 從 False 變為 True 時，韌體能夠正確響應並啟動 Media Scan。

4. **[Case04_VendorCmd_Disable_Scan]**：
   - 動作：透過 `issue_C08B_to_enable_diable_media_scan(enable_media_scan=False)` 強制禁用 Media Scan；寫入資料；設定 `last_scan_spend_time = 0x1000000`；輪詢 `issue_40CF` 監控 60 秒。
   - 預期結果：在 60 秒內，`cur_scan_vb`, `cur_scan_page`, `scan_group` 必須保持不變。這證明 Vendor Command `0xC08B` 的禁用指令具有最高優先級或有效攔截掃描觸發。

5. **[Case05_VendorCmd_Enable_Scan]**：
   - 動作：寫入資料；設定 `last_scan_spend_time = 0x1000000`；透過 `issue_C08B_to_enable_diable_media_scan(enable_media_scan=True)` 強制啟用 Media Scan；延遲 1 秒後讀取 `issue_40CF` 獲取 `new_scan_vb`，並與啟用前的 `old_scan_vb` 比較。
   - 預期結果：`new_scan_vb` 必須不等於 `old_scan_vb`。這證明 Vendor Command `0xC08B` 的啟用指令能立即觸發或允許 Media Scan 啟動。

6. **[Case06_Reset_Persistence_Differentiation]**：
   - 動作：透過 `issue_C08B` 禁用 Media Scan；讀取 `issue_40CF` 確認 `scan_status.value == 0x01` (Disabled)；分別執行 HW_RESET, RESET_N, ENDPOINT_RESET, UNIPRO_RESET；重置後立即讀取 `issue_40CF` 的 `scan_status.value`。
   - 預期結果：
     - 對於 `HW_RESET` 和 `RESET_N`：`scan_status.value` 必須等於 `0x00` (Enabled)。這證明電源循環重置會清除掃描禁用狀態，恢復預設行為。
     - 對於 `ENDPOINT_RESET` 和 `UNIPRO_RESET`：`scan_status.value` 必須等於 `0x01` (Disabled)。這證明軟重置不會改變掃描控制器的邏輯狀態，保留用戶的禁用設定。

7. **[Case07_Scan_Resume_From_Pause_Point]**：
   - 動作：啟用 Media Scan；寫入資料；設定 `last_scan_spend_time = 0x1000000`；輪詢 `issue_40CF` 直到掃描完成 (VB/Page 變為 0xFFFFFFFF) 並記錄掃描過的 VB 序列 (`old_vb_seq_scan_map`)；設定 `last_scan_spend_time = 0x2000000`；延遲 1 秒後透過 `issue_C08B` 禁用 Media Scan；讀取當前 `cur_scan_vb` 和 `cur_scan_page` 作為中斷點 (`old_scan_vb`, `old_scan_page`)；延遲 1 秒確認狀態未變；接著透過 `issue_C08B` 重新啟用 Media Scan；輪詢 `issue_40CF` 直到掃描位置回到 `old_scan_vb` 且 `cur_scan_page > old_scan_page`，或進入下一個 VB。
   - 預期結果：重新啟用後，掃描必須從 `old_scan_vb` 的下一個 Page 開始，或者如果 `old_scan_vb` 已掃描完畢，則進入 `old_vb_seq_scan_map` 中的下一個 VB。這證明韌體在 `0xC08B` 禁用時正確保存了掃描進度指針，並在啟用時實現斷點續掃。