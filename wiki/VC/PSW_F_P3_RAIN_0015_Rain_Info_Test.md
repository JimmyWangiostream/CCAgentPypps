# Test Spec: UFS RAIN (Redundant Array of Independent NAND) Configuration & Accumulation Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 RAIN (Redundant Array of Independent NAND) 功能的配置狀態機與計數邏輯正確性：
1. **配置持久化與狀態同步**：透過 Vendor Command `0xD08B` 切換 RAIN 的啟用/禁用狀態，確認 `0x4054` 查詢指令回傳的 `rain_info` 結構體中，所有相關的 Bit Map 欄位（包含 Plane-based, Open Host VB Simple/Full Block, Global/Permanent flags）能精確反映當前配置（全 0 或全 1）。
2. **幾何參數計算正確性**：驗證韌體根據 Flash 幾何參數（CE, Plane, Page Line）計算出的 SLC/TLC VB 的 Host Data Pageline Count、LBA Size 以及 Max Raw 參數是否符合預設公式（例如 SLC Pageline 固定為 1104，TLC 為 3312，LBA Size 需扣除 Parity 開銷）。
3. **RAIN Accumulation Count 動態更新**：針對不同 VB 類型（SLC, TLC, WB, PTE, L1, LOG），在寫入特定數量 Page 觸發 Open VB 後，確認 `current_RAIN_accumulation_count_for_each_parity` 欄位中的計數值是否與實際寫入的 Page 數量、Parity Group 數量 (`rain_goup_cnt`) 及 Invalid Plane 排除邏輯完全一致。

## Test Case (TC) Checkpoints

1. [TC01_RAIN_Config_Default_Check]：
   - 動作：執行 `pre_process` 初始化環境，呼叫 `issue_4054_to_get_rain_info` 獲取初始 RAIN 資訊並備份。接著檢查 `rain_info` 結構體中的固定欄位數值：`dummy` 必須為 `0xFFFFFFFF`；`host_data_pageline_count_in_SLC_VB` 必須為 `1104`；`host_data_pageline_count_in_TLC_VB` 必須為 `3312`；`max_raw_pageline_count_in_in_SLC_VB` 必須為 `1104`；`max_raw_pageline_count_in_in_TLC_VB` 必須為 `3312`；`CE` 欄位必須等於 `max_ce`。同時驗證 SLC 與 TLC 的 LBA Size 計算公式：`Pageline * 4 * max_plane * max_ce - (rain_goup_cnt + 2) * 4` 是否與 `host_data_LBA_size_in_SLC_VB` 及 `host_data_LBA_size_in_TLC_VB` 完全吻合。
   - 預期結果：所有上述欄位的讀取值必須嚴格等於預期常數或計算結果，確認韌體初始幾何參數與 Parity 開銷計算邏輯正確。

2. [TC02_RAIN_Disable_Verification]：
   - 動作：呼叫 `issue_D08B_to_enable_or_disable_Rain`，將四個參數 `Table_and_S_CHK_rain`, `Host_Permanent_Rain`, `Host_Simple_Rain`, `host_full_block_protection_rain` 均設為 `0` 以禁用 RAIN。隨後再次呼叫 `issue_4054_to_get_rain_info` 獲取最新狀態，並執行 `check_RAIN_bit_map_value`，預期所有 Bit Map 欄位（`Plane_based_RAIN_encoding_state`, `Open_Host_VB_simple_RAIN_encoding_state`, `Open_Host_VB_Full_Block_Protection_RAIN_encoding_state`, `Global_permanent_RAIN_enable_flag`, `Permanent_RAIN_enable_bitmap`）的值均為 `0`。
   - 預期結果：所有 RAIN 相關的 Bit Map 欄位數值必須等於 `0`，代表 RAIN 編碼與保護功能已完全關閉，且 Host 端查詢指令能正確反映此硬體狀態。

3. [TC03_RAIN_Enable_Verification]：
   - 動作：呼叫 `issue_D08B_to_enable_or_disable_Rain`，將四個參數均設為 `project_api.RainVB.ALL`（即全 1）以啟用 RAIN。隨後再次呼叫 `issue_4054_to_get_rain_info` 獲取最新狀態，並執行 `check_RAIN_bit_map_value`，預期所有 Bit Map 欄位的值均為 `1`。
   - 預期結果：所有 RAIN 相關的 Bit Map 欄位數值必須等於 `1`，代表 RAIN 編碼與保護功能已完全啟用，且 Host 端查詢指令能正確反映此硬體狀態。

4. [TC04_RAIN_Accumulation_Count_SLC_TLC_WB]：
   - 動作：針對 `TEST_SLC`, `TEST_TLC`, `TEST_WB` 模式，分別獲取對應 LUN 與幾何參數。若為 WB 模式則設置 `WRITEBOOSTER_EN` Flag。根據 `rain_goup_cnt` 決定寫入策略：若 `rain_goup_cnt > 1`，寫入 `rain_goup_cnt - 1` 個 Pageline 以建立 Open VB；否則寫入 `max_ce * max_plane * 0.75` 個 Page。寫入完成後，獲取 `cursor` (Open VB Info)，呼叫 `issue_4054_to_get_rain_info` 並執行 `check_RAIN_accumulation_count`。該檢查需驗證 `current_RAIN_accumulation_count_for_each_parity` 中對應 VB 類型（Host_EM1 for SLC, Host_TLC for TLC, WB for WB）的計數列表。計數邏輯需考慮 `invalid_plane_list` 排除無效 Plane，並根據 `rain_goup_cnt` 對 Pageline 進行取模分組累加（每 Page 計 4 個單位）。
   - 預期結果：韌體回傳的 `accumulation_list` 必須與手動計算的 `accumulation_list` 完全一致。特別是在 `rain_goup_cnt == 1` 時，計數應僅累加有效 Plane 的 Page 數乘以 4；在 `rain_goup_cnt > 1` 時，計數應按 Parity Group 正確分組累加，且正確跳過 `invalid_plane_list` 標記的 Plane。

5. [TC05_RAIN_Accumulation_Count_PTE_L1_LOG]：
   - 動作：針對 `TEST_PTE`, `TEST_L1`, `TEST_LOG` 模式執行類似 TC04 的寫入與檢查流程。對於 `TEST_LOG`，需先執行 `ssu_sleep_and_active` (StartStopUnit 進入 Sleep 再喚醒) 以觸發特定的韌體狀態轉換。獲取 Open VB Cursor 後，驗證 `current_RAIN_accumulation_count_for_each_parity` 中對應欄位（PTE, S_CHK, LOG）的計數值。驗證邏輯同樣需嚴格遵循 `invalid_plane_list` 排除與 `rain_goup_cnt` 分組累加規則。
   - 預期結果：所有特殊 VB 類型的 RAIN 計數器必須精確反映實際寫入的有效 Page 數量（扣除 Invalid Plane 後），且分組計數邏輯無誤，確保 RAIN 保護機制在各種 VB 類型下均能正確追蹤寫入進度。