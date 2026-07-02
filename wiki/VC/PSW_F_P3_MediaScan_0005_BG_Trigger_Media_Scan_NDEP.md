# Test Spec: UFS Media Scan & Refresh Mechanism Verification for Critical Internal LUNs

## Verification Criterion (VC)
驗證 UFS 韌體在 Media Scan 機制下，針對不同記憶體類型（TLC L2, SLC L2, TLC L1, LOG, PTE）及特定 LUN 配置下的錯誤恢復與狀態遷移行為：
1. **TLC L2 (LUN 0)**：驗證在注入空頁 UECC 後，Media Scan 能正確將該 VB 加入 Booking Queue，並在 Refresh 執行後完成 VB 切換，確保資料完整性。
2. **SLC L2 (LUN 1)**：驗證 Enhanced 1 (EM1) LUN 在相同 UECC 注入情境下，Media Scan 與 Refresh 機制能正確處理 SLC 區塊的錯誤修復與 VB 遷移。
3. **TLC L1 (LUN 0)**：驗證韌體內部 L1 區塊在注入 UECC 後，Media Scan 能識別並處理，最終觸發 VB 切換。
4. **LOG 區塊**：驗證韌體日誌區塊在注入 UECC 後，Media Scan 能正確掃描並修復，確保 VB 狀態更新。
5. **PTE 區塊**：驗證 Page Table Entry 區塊在注入 UECC 後，Media Scan 能正確掃描並修復，確保 VB 狀態更新。
所有 Case 共同驗證點：Media Scan 必須將受影響的 VB 正確排入 Booking Queue (`LogicalVBNumberInBookingQueue` 不為 0 且內容正確)，Refresh 執行完畢後 Booking Queue 必須清空，且對應 LUN/VB 的 `logical_vb` 值必須發生改變（代表已遷移至新區塊），最後透過 Read Compare 確認資料無損。

## Test Case (TC) Checkpoints

1. **[TLC_L2_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 透過 `vuC08B` 禁用 Media Scan。
     2. 配置 LUN 0 (Normal) 並寫入一個完整 TLC Wear Leveling (WL) 大小的資料量 (`TLC_WL_block`)。
     3. 獲取當前 TLC L2 的 VB 號碼 (`old_tlc_l2_vb`) 及該 VB 內的第一個空頁物理地址 (CE, Plane, Page)。
     4. 透過 `inject_UECC` 在該空頁注入 UECC 錯誤 (`pca.b4_mode = 2` 代表 TLC)。
     5. 記錄當前 Media Scan 參數 (`cur_scan_vb`, `scan_group`)。
     6. 透過 `vuC088` 停止 Refresh 執行但允許入隊 (`StopRefreshRefreshCanStillBeEnqueue`)。
     7. 透過 `vuC08B` 啟用 Media Scan。
     8. 輪詢等待 Media Scan 觸發，檢查 `vu40C5` 返回的 Booking Queue，確認 `LogicalVBNumberInBookingQueue` 不為 0，且 Queue 中的 VB 號碼等於 `old_tlc_l2_vb`。
     9. 確認 `vu40CF` 返回的 `scan_group` 已改變（代表掃描進度推進）。
     10. 透過 `vuC088` 啟動 Refresh 執行 (`StartRefresh`)。
     11. 輪詢等待 BKOPS 狀態為 Idle (`expect_value=0`)。
     12. 檢查 `vu40C5` 返回的 Booking Queue，確認 `LogicalVBNumberInBookingQueue` 為 0。
     13. 獲取新的 TLC L2 VB 號碼 (`new_tlc_l2_vb`) 並與舊值比較。
     14. 執行 `read_compare` 驗證寫入資料的完整性。
   - 預期結果：
     - Booking Queue 中必須包含 `old_tlc_l2_vb`。
     - Refresh 結束後 Booking Queue 必須為空。
     - `new_tlc_l2_vb` 必須不等於 `old_tlc_l2_vb`（代表 VB 已切換）。
     - Read Compare 必須通過，無資料錯誤。

2. **[SLC_L2_EM1_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 配置 LUN 1 (Enhanced 1) 並寫入一個完整 SLC WL 大小的資料量 (`SLC_WL_block`)。
     3. 獲取當前 SLC L2 的 VB 號碼 (`old_slc_l2_vb`) 及該 VB 內的第一個空頁物理地址。
     4. 透過 `inject_UECC` 在該空頁注入 UECC 錯誤 (`pca.b4_mode = 1` 代表 SLC)。
     5. 記錄當前 Media Scan 參數。
     6. 透過 `vuC088` 停止 Refresh 執行但允許入隊。
     7. 啟用 Media Scan。
     8. 輪詢等待 Media Scan 觸發，檢查 `vu40C5` 返回的 Booking Queue，確認 Queue 中的 VB 號碼等於 `old_slc_l2_vb`。
     9. 確認 `scan_group` 已改變。
     10. 啟動 Refresh 執行。
     11. 輪詢等待 BKOPS Idle。
     12. 檢查 Booking Queue 為空。
     13. 獲取新的 SLC L2 VB 號碼 (`new_slc_l2_vb`) 並與舊值比較。
     14. 執行 `read_compare` 驗證資料完整性。
   - 預期結果：
     - Booking Queue 中必須包含 `old_slc_l2_vb`。
     - Refresh 結束後 Booking Queue 必須為空。
     - `new_slc_l2_vb` 必須不等於 `old_slc_l2_vb`。
     - Read Compare 必須通過。

3. **[TLC_L1_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 配置 LUN 0 並寫入一個 16KB (一個 Block) 的資料量。
     3. 獲取當前 TLC L1 的 VB 號碼 (`old_l1_vb`) 及該 VB 內的第一個空頁物理地址。
     4. 透過 `inject_UECC` 在該空頁注入 UECC 錯誤 (`pca.b4_mode = 2` 代表 TLC)。
     5. 記錄當前 Media Scan 參數。
     6. 透過 `vuC088` 停止 Refresh 執行但允許入隊。
     7. 啟用 Media Scan。
     8. 輪詢等待 Media Scan 觸發，檢查 `vu40C5` 返回的 Booking Queue，確認 Queue 中的 VB 號碼等於 `old_l1_vb`。
     9. 確認 `scan_group` 已改變。
     10. 啟動 Refresh 執行。
     11. 輪詢等待 BKOPS Idle。
     12. 檢查 Booking Queue 為空。
     13. 獲取新的 TLC L1 VB 號碼 (`new_l1_vb`) 並與舊值比較。
     14. 執行 `read_compare` 驗證資料完整性。
   - 預期結果：
     - Booking Queue 中必須包含 `old_l1_vb`。
     - Refresh 結束後 Booking Queue 必須為空。
     - `new_l1_vb` 必須不等於 `old_l1_vb`。
     - Read Compare 必須通過。

4. **[LOG_Block_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 配置 LUN 0 並寫入 12MB 的資料量。
     3. 獲取當前 LOG 區塊的 VB 號碼 (`old_log_vb`) 及該 VB 內的第一個空頁物理地址。
     4. 透過 `inject_UECC` 在該空頁注入 UECC 錯誤 (`pca.b4_mode = 1` 代表 SLC/LOG 通常使用 SLC 模式或特定模式，代碼中為 1)。
     5. 記錄當前 Media Scan 參數。
     6. 透過 `vuC088` 停止 Refresh 執行但允許入隊。
     7. 啟用 Media Scan。
     8. 輪詢等待 Media Scan 觸發，檢查 `vu40C5` 返回的 Booking Queue，確認 Queue 中的 VB 號碼等於 `old_log_vb`。
     9. 確認 `scan_group` 已改變。
     10. 啟動 Refresh 執行。
     11. 輪詢等待 BKOPS Idle。
     12. 檢查 Booking Queue 為空。
     13. 獲取新的 LOG VB 號碼 (`new_log_vb`) 並與舊值比較。
   - 預期結果：
     - Booking Queue 中必須包含 `old_log_vb`。
     - Refresh 結束後 Booking Queue 必須為空。
     - `new_log_vb` 必須不等於 `old_log_vb`。

5. **[PTE_Block_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 配置 LUN 0 並寫入 4096 個節點 (Node) 的資料量以觸發 PTE Flush。
     3. 獲取當前 PTE 區塊的 VB 號碼 (`old_pte_vb`) 及該 VB 內的第一個空頁物理地址。
     4. 透過 `inject_UECC` 在該空頁注入 UECC 錯誤 (`pca.b4_mode = 1` 代表 SLC/PTE)。
     5. 記錄當前 Media Scan 參數。
     6. 透過 `vuC088` 停止 Refresh 執行但允許入隊。
     7. 啟用 Media Scan。
     8. 輪詢等待 Media Scan 觸發，檢查 `vu40C5` 返回的 Booking Queue，確認 Queue 中的 VB 號碼等於 `old_pte_vb`。
     9. 確認 `scan_group` 已改變。
     10. 啟動 Refresh 執行。
     11. 輪詢等待 BKOPS Idle。
     12. 檢查 Booking Queue 為空。
     13. 獲取新的 PTE VB 號碼 (`new_pte_vb`) 並與舊值比較。
   - 預期結果：
     - Booking Queue 中必須包含 `old_pte_vb`。
     - Refresh 結束後 Booking Queue 必須為空。
     - `new_pte_vb` 必須不等於 `old_pte_vb`。