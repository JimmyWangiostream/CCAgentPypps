# Test Spec: UFS Media Scan & Refresh UECC Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Media Scan 機制下，針對不同 LUN 類型（TLC L2, SLC L2, TLC L1, LOG, PTE, Used Pool MLC/SLC）注入 UECC 錯誤後的自動修復（Refresh）行為：
1. **Booking Queue 機制驗證**：確認在 `C088` 暫停 Refresh 但允許入隊期間，Media Scan 能正確偵測到 UECC 並將其 Logical VB 加入 Booking Queue；且當 `C088` 恢復執行後，Booking Queue 必須清空，代表該 VB 已被處理。
2. **VB 狀態遷移驗證**：確認經過 Refresh 流程後，受影響的 Logical VB（如 TLC_L2, SLC_L2, LOG, PTE 等）必須發生跳變（Change），代表舊的損壞區塊已被替換或修復，且新 VB 指向健康的物理區塊。
3. **資料完整性驗證**：在每個 Case 的 Refresh 完成後，執行 `Read Compare` 確保資料無誤，證明 UECC 錯誤已透過韌體層級的修復機制（如重寫或重新映射）消除，而非僅是標記為壞塊。

## Test Case (TC) Checkpoints

1. **[TLC_L2_UECC_Refresh_Check]**：
   - 動作：配置 LUN 0 (Normal) 並寫入一個 TLC WL 大小的資料量；取得 TLC_L2 的 Logical VB (`old_tlc_l2_vb`) 及空閒 CE/Plane/Page 資訊；透過 `inject_UECC` 在該 VB 的 Page 0 注入 UECC 錯誤；記錄當前 Media Scan 參數 (`cur_scan_vb`, `scan_group`)；發送 `C088` 停止 Refresh 執行但允許入隊；啟用 Media Scan (`C08B`)；輪詢等待 Booking Queue 中出現 `old_tlc_l2_vb` 且 `scan_group` 改變；發送 `C088` 啟動 Refresh；輪詢 BKOPS 至 Idle；檢查 Booking Queue 是否為空；讀取 `open_vb_info` 確認 `TLC_L2.logical_vb` 已改變；執行 Read Compare。
   - 預期結果：Booking Queue 中必須包含 `old_tlc_l2_vb`；Refresh 完成後 Booking Queue 必須為空；`TLC_L2.logical_vb` 必須不等於 `old_tlc_l2_vb`（代表 VB 已遷移）；Read Compare 必須通過，證明資料完整性恢復。

2. **[SLC_L2_UECC_Refresh_Check]**：
   - 動作：配置 LUN 1 (Enhanced 1) 並寫入一個 SLC WL 大小的資料量；取得 SLC_L2 的 Logical VB (`old_slc_l2_vb`) 及空閒 CE/Plane/Page 資訊；透過 `inject_UECC` 在該 VB 的 Page 0 注入 UECC 錯誤；記錄當前 Media Scan 參數；發送 `C088` 停止 Refresh 執行但允許入隊；啟用 Media Scan (`C08B`)；輪詢等待 Booking Queue 中出現 `old_slc_l2_vb` 且 `scan_group` 改變；發送 `C088` 啟動 Refresh；輪詢 BKOPS 至 Idle；檢查 Booking Queue 是否為空；讀取 `open_vb_info` 確認 `SLC_L2.logical_vb` 已改變；執行 Read Compare。
   - 預期結果：Booking Queue 中必須包含 `old_slc_l2_vb`；Refresh 完成後 Booking Queue 必須為空；`SLC_L2.logical_vb` 必須不等於 `old_slc_l2_vb`（代表 VB 已遷移）；Read Compare 必須通過，證明資料完整性恢復。

3. **[TLC_L1_UECC_Refresh_Check]**：
   - 動作：配置 LUN 0 並寫入一個 Block (16KB) 的資料量；取得 TLC_L1 的 Logical VB (`old_l1_vb`) 及空閒 CE/Plane/Page 資訊；手動構造 PCA 結構體（`b4_mode=2`, `b5_ce=0`, `b6_plane=0`, `b11_block_h/l` 設為 `old_l1_vb`, `l12_fpage=0`）並透過 `inject_UECC` 注入 L1 Block 的有效頁面 UECC 錯誤；記錄當前 Media Scan 參數；發送 `C088` 停止 Refresh 執行但允許入隊；啟用 Media Scan (`C08B`)；輪詢等待 Booking Queue 中出現 `old_l1_vb` 且 `scan_group` 改變；發送 `C088` 啟動 Refresh；輪詢 BKOPS 至 Idle；檢查 Booking Queue 是否為空；讀取 `open_vb_info` 確認 `TLC_L1.logical_vb` 已改變；執行 Read Compare。
   - 預期結果：Booking Queue 中必須包含 `old_l1_vb`；Refresh 完成後 Booking Queue 必須為空；`TLC_L1.logical_vb` 必須不等於 `old_l1_vb`（代表 VB 已遷移）；Read Compare 必須通過，證明 L1 層級資料完整性恢復。

4. **[LOG_VB_UECC_Refresh_Check]**：
   - 動作：配置 LUN 0 並寫入 12MB 的資料量；取得 LOG VB 的 Logical VB (`old_log_vb`) 及空閒 CE/Plane/Page 資訊；手動構造 PCA 結構體（`b4_mode=1`, `b5_ce=0`, `b6_plane=0`, `b11_block_h/l` 設為 `old_log_vb`, `l12_fpage=0`）並透過 `inject_UECC` 注入 LOG Block 的有效頁面 UECC 錯誤；記錄當前 Media Scan 參數；發送 `C088` 停止 Refresh 執行但允許入隊；啟用 Media Scan (`C08B`)；輪詢等待 Booking Queue 中出現 `old_log_vb` 且 `scan_group` 改變；發送 `C088` 啟動 Refresh；輪詢 BKOPS 至 Idle；檢查 Booking Queue 是否為空；讀取 `open_vb_info` 確認 `LOG.logical_vb` 已改變。
   - 預期結果：Booking Queue 中必須包含 `old_log_vb`；Refresh 完成後 Booking Queue 必須為空；`LOG.logical_vb` 必須不等於 `old_log_vb`（代表 LOG 區塊已刷新/替換）。

5. **[PTE_VB_UECC_Refresh_Check]**：
   - 動作：配置 LUN 0 並寫入 4096 個節點（觸發 PTE Flush）的資料量；取得 PTE VB 的 Logical VB (`old_pte_vb`) 及空閒 CE/Plane/Page 資訊；手動構造 PCA 結構體（`b4_mode=1`, `b5_ce=0`, `b6_plane=0`, `b11_block_h/l` 設為 `old_pte_vb`, `l12_fpage=0`）並透過 `inject_UECC` 注入 PTE Block 的空閒頁面 UECC 錯誤；記錄當前 Media Scan 參數；發送 `C088` 停止 Refresh 執行但允許入隊；啟用 Media Scan (`C08B`)；輪詢等待 Booking Queue 中出現 `old_pte_vb` 且 `scan_group` 改變；發送 `C088` 啟動 Refresh；輪詢 BKOPS 至 Idle；檢查 Booking Queue 是否為空；讀取 `open_vb_info` 確認 `PTE.logical_vb` 已改變。
   - 預期結果：Booking Queue 中必須包含 `old_pte_vb`；Refresh 完成後 Booking Queue 必須為空；`PTE.logical_vb` 必須不等於 `old_pte_vb`（代表 PTE 區塊已刷新/替換）。

6. **[Used_Pool_MLC_UECC_Refresh_Check]**：
   - 動作：配置 LUN 0 並寫入一個 TLC VB 大小的資料量；透過 `get_PCA_and_print` 獲取當前寫入位置的 PCA，計算出 `old_used_pool_mlc_vb`；驗證該 VB 的 Group 為 `USED_BLK_POOL_MLC`；透過 `inject_UECC` 注入該 Used Pool MLC VB 的頁面 UECC 錯誤；記錄當前 Media Scan 參數；發送 `C088` 停止 Refresh 執行但允許入隊；啟用 Media Scan (`C08B`)；輪詢等待 Booking Queue 中出現 `old_used_pool_mlc_vb` 且 `scan_group` 改變；發送 `C088` 啟動 Refresh；輪詢 BKOPS 至 Idle；檢查 Booking Queue 是否為空；透過 `get_PCA_and_print` 獲取新 PCA，計算出 `new_used_pool_mlc_vb` 並確認其不等於 `old_used_pool_mlc_vb`；執行 Read Compare。
   - 預期結果：Booking Queue 中必須包含 `old_used_pool_mlc_vb`；Refresh 完成後 Booking Queue 必須為空；新的 PCA 計算出的 VB 必須不等於舊 VB（代表 Used Pool 區塊已替換）；Read Compare 必須通過。

7. **[Used_Pool_SLC_UECC_Refresh_Check]**：
   - 動作：配置 LUN 1 並寫入一個 SLC VB 大小的資料量；透過 `get_PCA_and_print` 獲取當前寫入位置的 PCA，計算出 `old_used_pool_slc_vb`；驗證該 VB 的 Group 為 `USED_BLK_POOL_SLC`；透過 `inject_UECC` 注入該 Used Pool SLC VB 的頁面 UECC 錯誤；記錄當前 Media Scan 參數；發送 `C088` 停止 Refresh 執行但允許入隊；啟用 Media Scan (`C08B`)；輪詢等待 Booking Queue 中出現 `old_used_pool_slc_vb` 且 `scan_group` 改變；發送 `C088` 啟動 Refresh；輪詢 BKOPS 至 Idle；檢查 Booking Queue 是否為空；透過 `get_PCA_and_print` 獲取新 PCA，計算出 `new_used_pool_slc_vb` 並確認其不等於 `old_used_pool_slc_vb`；執行 Read Compare。
   - 預期結果：Booking Queue 中必須包含 `old_used_pool_slc_vb`；Refresh 完成後 Booking Queue 必須為空；新的 PCA 計算出的 VB 必須不等於舊 VB（代表 Used Pool SLC 區塊已替換）；Read Compare 必須通過。