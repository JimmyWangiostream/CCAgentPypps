# Test Spec: UFS VB (Virtual Block) Integrity & Refresh Mechanism under UECC Stress

## Verification Criterion (VC)
驗證 UFS 韌體在極端錯誤注入情境下的 Virtual Block (VB) 狀態管理與背景刷新機制：
1. **VB 完整性與錯誤隔離**：確認在特定 LUN 上寫入大量資料後，針對最後一個 VB 的特定 Page 層級注入 UECC (Uncorrectable ECC) 錯誤，韌體能正確識別該 VB 為異常狀態，且不會影響其他正常 VB 的數據完整性。
2. **VB 關閉與狀態固化**：確認在注入 UECC 後，透過寫入剩餘空間 (`last_size`) 及額外填充資料 (`2 * CE*Plane*Block`) 強制關閉該 VB，驗證 VB 關閉流程能正確處理包含 UECC 的 Page，並確保後續讀取比較 (Read-Compare) 僅針對未注入錯誤的 Write Record 進行驗證，排除注入區域的干擾。
3. **Refresh 機制觸發與穩定性**：確認在 VB 關閉後，啟動背景 Refresh 機制 (`C088 StartRefresh`)，驗證韌體能正確掃描並處理包含 UECC 的 VB，確保系統在 Idle 狀態下不會因未修復的 UECC 導致崩潰或數據丟失，同時確認 Refresh 過程中的電源管理與隊列清空邏輯正確執行。

## Test Case (TC) Checkpoints
1. [Precondition_Setup_and_Refresh_Suppression]：
   - 動作：初始化測試環境，獲取 TLC/SLC 幾何參數 (`max_ce`, `max_plane`, `max_pageline`) 及 VB 大小設定。透過 `project_api.issue_C088_to_start_or_stop_refresh` 發送 `StopRefresh` 指令 (`VUC088Paremeter.StopRefreshRefreshCanStillBeEnqueue`)，確保在後續高負載寫入與錯誤注入期間，背景 Refresh 機制不會干擾測試結果。根據測試模式 (`TEST_TLC` 或 `TEST_WB`) 設定 `WRITEBOOSTER_EN` 旗標。
   - 預期結果：背景 Refresh 機制被成功暫停，寫入加速器狀態符合測試模式設定，為後續精確的錯誤注入與 VB 狀態觀察建立乾淨的硬體環境。

2. [Sequential_Write_and_UECC_Injection_on_Last_VB]：
   - 動作：計算目標 VB 的剩餘空間 (`total_size = vb_size - last_size`) 與 Chunk Size。針對測試 LUN 從 LBA 0 開始執行 `sequential_write`，寫入 `total_size` 資料，並啟用 FUA (Force Unit Access) 確保資料落盤。記錄最後一個 LBA (`UECC_lba = lba - 1`) 並透過 `get_PCA_and_print` 獲取其物理位置資訊 (PCA)。接著，透過 `get_specific_open_vb_cursor` 獲取當前 VB 游標。針對該 VB 內的特定 Page 列表 (`page_list`)，計算其物理 Layout (包含 SubBlock, FlushGroup 等)，並對每個 Page 執行 `inject_UECC`，在硬體層級注入不可糾正的 ECC 錯誤。
   - 預期結果：資料成功寫入至目標 VB，最後一個 Page 的 PCA 被正確解析。UECC 錯誤被精確注入到指定的物理 Page，且該 VB 處於「開啟」狀態，尚未關閉。注入的錯誤應反映在該 Page 的 ECC 狀態中，但尚未觸發韌體的自動修復或標記為不可用。

3. [VB_Closure_and_Data_Integrity_Verification]：
   - 動作：計算關閉 VB 所需的剩餘空間 (`last_size`) 及額外填充資料大小 (`2 * max_ce * max_plane * BLOCK4K_SIZE_16K_BYTE`)。透過 `ExecuteCMD.Write10` 發送寫入指令，寫入 `total_size` 的固定模式資料 (`HW_FIX`) 至剩餘 LBA，並設定 FUA=1 強制落盤。寫入完成後，執行 `read_compare_rain_result`，僅針對 `write_record` 中記錄的、未注入 UECC 的資料區塊進行讀取與比較驗證。
   - 預期結果：VB 被成功關閉，包含 UECC 錯誤的 Page 被固化在 VB 中。讀取比較驗證通過，證明未受影響的資料區塊完整性無損。此步驟確認韌體在 VB 關閉流程中，能正確處理包含錯誤的 Page 而不導致整個寫入操作失敗，且錯誤被隔離在特定的 VB 內。

4. [Refresh_Mechanism_Activation_and_Idle_Polling]：
   - 動作：透過 `project_api.issue_C088_to_start_or_stop_refresh` 發送 `StartRefresh` 指令 (`VUC088Paremeter.StartRefresh`)，重新啟用背景 Refresh 機制。隨後執行 `polling_bkops_idle`，輪詢等待 BKOPS 操作完成並進入 Idle 狀態。
   - 預期結果：背景 Refresh 機制啟動，韌體開始掃描包含 UECC 的 VB。系統最終穩定進入 Idle 狀態，無未處理的錯誤中斷或崩潰。這驗證了韌體在 Refresh 過程中能正確識別並處理 UECC 錯誤（例如標記為壞塊、嘗試修復或記錄錯誤狀態），確保系統在錯誤注入後的長期穩定性。