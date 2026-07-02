# Test Spec: UFS BFEA (Background Flash Error Analysis) Scan Trigger & Bin Management Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 BFEA (Background Flash Error Analysis) 機制在多種寫入負載與配置情境下的行為一致性：
1. **Case 01 (Enhanced LUN/Full Capacity)**：驗證在 Enhanced 1 LUN 寫入 3 個 TLC VB 容量資料後，BFEA 背景掃描計數器（Trig/Done Count）正確增加 1，且目標 VB 的 Bin 值觸發掃描。
2. **Case 02 (Threshold Boundary - Below)**：驗證寫入量低於 `FB_SCAN_WL_MIN` 閾值時，BFEA 不應觸發，Bin 值保持不變。
3. **Case 03 (Threshold Boundary - At Min)**：驗證寫入量等於 `FB_SCAN_WL_MIN` 閾值時，BFEA 正確觸發，計數器增加 1。
4. **Case 04 (Threshold Boundary - At Max)**：驗證寫入量等於 `FB_SCAN_WL_MAX` 閾值時，BFEA 正確觸發。
5. **Case 05 (Page Gap Trigger)**：驗證寫入量觸發 `PB_SCAN_PAGE` 與 `PB_SCAN_ENABLE_PAGE_GAP` 組合條件時，BFEA 正確觸發。
6. **Case 06 (Page Gap Only)**：驗證僅寫入 `PB_SCAN_ENABLE_PAGE_GAP` 量時，BFEA 不應觸發（作為控制組）。
7. **Case 07 (DM Background Task Disabled)**：驗證當透過 Vendor Command `D018` 禁用 Bank 級背景任務時，寫入 3 個 TLC VB 後 BFEA 仍應正常觸發（確認 BFEA 獨立於 DM 背景任務）。
8. **Case 08 (Power Cycle Recovery)**：驗證在 HW_RESET + Power Down 後，韌體恢復並寫入 3 個 TLC VB，BFEA 機制能正確識別並觸發掃描。
9. **Case 09 (BFEA Disabled)**：驗證透過 Vendor Command `40B0` 禁用 BFEA 後，寫入 3 個 TLC VB，BFEA 不應觸發，Bin 值保持不變。
10. **Case 10 (Offset Configuration & Booking Queue)**：驗證在寫入大量資料並設定所有 Bin Offset 為 128 後，BFEA 觸發，且透過 `40C5` Vendor Command 讀取的 Booking Queue 中，BFEA 任務的 Bit Position 必須為 18，Priority 必須為 1。

## Test Case (TC) Checkpoints

1. **[Case01_Enhanced_LUN_BFEA_Trigger_Check]**：
   - 動作：配置 LUN 0 為 Enhanced 1 類型並分配全部 AU 容量；寫入 `3 * tlc_vb_size` 的 4KB 資料至 LUN 0；讀取韌體內部變數 `gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[0]` 與 `done_count[0]` 作為基準值；等待 BFEA 掃描完成（Polling `40B0` Option 5 返回 Idle）；再次讀取上述計數器。
   - 預期結果：`trig_count[0]` 與 `done_count[0]` 必須分別等於基準值 + 1。代表在 Enhanced LUN 滿載寫入情境下，BFEA 背景掃描機制正確觸發並完成。

2. **[Case02_Below_Min_Threshold_No_Trigger]**：
   - 動作：配置 LUN 0 為 Normal 類型，分配 4 個 AU 容量；計算寫入大小為 `(FB_SCAN_WL_MIN - 1) * 3 * 4` 個 4KB 區塊並寫入；讀取目標 VB 的 Bin 值作為 `set_bin_old_val`；等待 BFEA Idle；再次讀取目標 VB 的 Bin 值。
   - 預期結果：再次讀取的 Bin 值必須嚴格等於 `set_bin_old_val`。代表寫入量低於 `FB_SCAN_WL_MIN` 閾值時，BFEA 機制未觸發，Bin 值未發生變化。

3. **[Case03_At_Min_Threshold_Trigger_Check]**：
   - 動作：配置 LUN 0 為 Normal 類型；計算寫入大小為 `(FB_SCAN_WL_MIN) * 3 * 4` 個 4KB 區塊並寫入；讀取韌體計數器 `trig_count[0]` 與 `done_count[0]` 作為基準值；等待 BFEA Idle；再次讀取計數器。
   - 預期結果：`trig_count[0]` 與 `done_count[0]` 必須分別等於基準值 + 1。代表寫入量達到 `FB_SCAN_WL_MIN` 閾值時，BFEA 機制正確觸發。

4. **[Case04_At_Max_Threshold_Trigger_Check]**：
   - 動作：配置 LUN 0 為 Normal 類型；計算寫入大小為 `(FB_SCAN_WL_MAX) * 3 * 4` 個 4KB 區塊並寫入；讀取韌體計數器 `trig_count[0]` 與 `done_count[0]` 作為基準值；等待 BFEA Idle；再次讀取計數器。
   - 預期結果：`trig_count[0]` 與 `done_count[0]` 必須分別等於基準值 + 1。代表寫入量達到 `FB_SCAN_WL_MAX` 閾值時，BFEA 機制正確觸發。

5. **[Case05_Page_Gap_Trigger_Check]**：
   - 動作：配置 LUN 0 為 Normal 類型；計算寫入大小為 `(PB_SCAN_PAGE + PB_SCAN_ENABLE_PAGE_GAP) * 6 * ce_num * 4` 個 4KB 區塊並寫入；讀取韌體計數器 `trig_count[0]` 與 `done_count[0]` 作為基準值；等待 BFEA Idle；再次讀取計數器。
   - 預期結果：`trig_count[0]` 與 `done_count[0]` 必須分別等於基準值 + 1。代表寫入量滿足 Page Scan 與 Page Gap 組合條件時，BFEA 機制正確觸發。

6. **[Case06_Page_Gap_Only_No_Trigger]**：
   - 動作：配置 LUN 0 為 Normal 類型；計算寫入大小為 `(PB_SCAN_ENABLE_PAGE_GAP) * 4` 個 4KB 區塊並寫入；讀取目標 VB 的 Bin 值作為 `set_bin_old_val`；等待 BFEA Idle；再次讀取目標 VB 的 Bin 值。
   - 預期結果：再次讀取的 Bin 值必須嚴格等於 `set_bin_old_val`。代表僅滿足 Page Gap 條件但未達到 Page Scan 閾值時，BFEA 機制未觸發。

7. **[Case07_DM_Disabled_BFEA_Independent_Check]**：
   - 動作：發送 Vendor Command `D018` 禁用 Bank 級背景任務（DM Background Task）；配置 LUN 0 為 Normal 類型；寫入 `3 * tlc_vb_size` 的 4KB 資料；讀取韌體計數器 `trig_count[0]` 與 `done_count[0]` 作為基準值；等待 BFEA Idle；再次讀取計數器。
   - 預期結果：`trig_count[0]` 與 `done_count[0]` 必須分別等於基準值 + 1。代表 BFEA 掃描機制獨立於 DM 背景任務，即使 DM 被禁用，BFEA 仍應正常運作。

8. **[Case08_Power_Cycle_BFEA_Recovery_Check]**：
   - 動作：執行 HW_RESET 並 Power Down；發送 Vendor Command `D088` 禁用 Auto Standby；發送 Vendor Command `40B0` 初始化 BFEA；配置 LUN 0 為 Normal 類型；寫入 `3 * tlc_vb_size` 的 4KB 資料；讀取韌體計數器 `trig_count[0]` 與 `done_count[0]` 作為基準值；等待 BFEA Idle；再次讀取計數器。
   - 預期結果：`trig_count[0]` 與 `done_count[0]` 必須分別等於基準值 + 1。代表韌體在異常掉電恢復後，BFEA 狀態機能正確重置並響應新的寫入觸發。

9. **[Case09_BFEA_Disabled_No_Trigger]**：
   - 動作：發送 Vendor Command `40B0` (Option 1) 禁用 BFEA；配置 LUN 0 為 Normal 類型；寫入 `3 * tlc_vb_size` 的 4KB 資料；讀取目標 VB 的 Bin 值作為 `set_bin_old_val`；等待 BFEA Idle；再次讀取目標 VB 的 Bin 值。
   - 預期結果：再次讀取的 Bin 值必須嚴格等於 `set_bin_old_val`。代表透過 Vendor Command 禁用 BFEA 後，即使寫入量觸發閾值，BFEA 機制也不會執行掃描或更新 Bin 值。

10. **[Case10_Offset_Config_Booking_Queue_Check]**：
    - 動作：配置 LUN 0 為 Normal 類型；寫入經過 `aligned_super_one_pass` 計算的大量 4KB 資料；發送 Vendor Command `D04A` 將所有 16 個 Bin 的 Offset 設定為 128；等待 BFEA Idle；發送 Vendor Command `40C5` 讀取 Booking Queue Payload；解析 Payload 的 Byte[12:16]。
    - 預期結果：
        1. 解析出的 `bfea_booking` (Bits 0-6) 必須等於 18。
        2. 解析出的 `priority` (Bit 8) 必須等於 1。
        這代表 BFEA 任務在 Booking Queue 中具有特定的 Bit Position (18) 和高優先級 (1)，且 Offset 配置已正確應用於觸發邏輯。