# Test Spec: UFS Media Scan & Refresh Mechanism Verification for Critical Internal LUNs

## Verification Criterion (VC)
驗證 UFS 韌體在 Media Scan 機制下，針對不同記憶體類型（TLC L2, SLC L2, TLC L1, LOG, PTE）及特定 LUN 配置下的錯誤恢復與資源遷移行為：
1. **TLC L2 (LUN 0)**：確認在注入 Empty Page UECC 後，Media Scan 能正確識別該 VB 並將其加入 Booking Queue，且在 Refresh 執行完畢後，該 VB 被替換為新的 Empty VB，且 Booking Queue 清空。
2. **SLC L2 (LUN 1)**：確認在 Enhanced 1 (EM1) LUN 上注入 Empty Page UECC 後，Media Scan 能正確識別並觸發 Refresh，最終 SLC L2 VB 發生變更，證明 EM1 區域的韌體結構完整性恢復。
3. **TLC L1 (LUN 0)**：確認在 L1 區塊注入 Empty Page UECC 後，Media Scan 能識別並修復，導致 TLC L1 VB 號碼變更。
4. **LOG Block (LUN 0)**：確認在 LOG 區塊注入 Empty Page UECC 後，Media Scan 能識別並修復，導致 LOG VB 號碼變更。
5. **PTE Block (LUN 0)**：確認在 PTE 區塊注入 Empty Page UECC 後，Media Scan 能識別並修復，導致 PTE VB 號碼變更。
所有 Case 均需驗證：Booking Queue 在 Refresh 前包含目標 VB，Refresh 後為空；且最終透過 HW Compare 確認資料一致性無誤。

## Test Case (TC) Checkpoints

1. **[TLC_L2_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 透過 `vuC08B` 禁用 Media Scan。
     2. 配置 LUN 0 (Normal) 並寫入 `TLC_WL_block` 大小的資料。
     3. 讀取 `open_vb_info.TLC_L2` 獲取當前 VB (`old_tlc_l2_vb`) 及第一個 Empty CE/Plane/Page。
     4. 建構 `PCA` 結構體：`b4_mode=2` (TLC), 設定對應 CE/Plane/Page/Block，呼叫 `inject_UECC` 在 TLC L2 的 Empty Page 注入 UECC 錯誤。
     5. 透過 `vu40CF` 記錄當前 Scan Group (`old_scan_group`)。
     6. 透過 `vuC088` 設定 `StopRefreshRefreshCanStillBeEnqueue` 停止 Refresh 執行但允許入隊。
     7. 透過 `vuC08B` 啟用 Media Scan。
     8. 輪詢等待 Booking Queue 非空，並驗證 `BookingQueueVB` 中必須包含 `old_tlc_l2_vb`。
     9. 透過 `vu40CF` 確認 `new_scan_group != old_scan_group` (表示已掃描過該 VB)。
     10. 透過 `vuC088` 設定 `StartRefresh` 啟動 Refresh。
     11. 輪詢 BKOPS 至 Idle。
     12. 透過 `vu40C5` 驗證 `LogicalVBNumberInBookingQueue` 為 0。
     13. 讀取 `open_vb_info.TLC_L2.logical_vb` 並與 `old_tlc_l2_vb` 比較。
     14. 執行 `read_compare` 驗證資料完整性。
   - 預期結果：
     - Booking Queue 在 Refresh 前正確包含 `old_tlc_l2_vb`。
     - `new_scan_group` 不等於 `old_scan_group`。
     - Refresh 後 Booking Queue 為空。
     - `new_tlc_l2_vb` **不等於** `old_tlc_l2_vb` (VB 號碼必須改變，代表舊 VB 被替換)。
     - HW Compare 通過，無資料損壞。

2. **[SLC_L2_EM1_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 配置 LUN 1 (Enhanced 1) 並寫入 `SLC_WL_block` 大小的資料。
     3. 讀取 `open_vb_info.SLC_L2` 獲取當前 VB (`old_slc_l2_vb`) 及 Empty 物理位置。
     4. 建構 `PCA` 結構體：`b4_mode=1` (SLC), 設定對應 CE/Plane/Page/Block，呼叫 `inject_UECC` 在 SLC L2 的 Empty Page 注入 UECC 錯誤。
     5. 記錄當前 Scan Group (`old_scan_group`)。
     6. 透過 `vuC088` 設定 `StopRefreshRefreshCanStillBeEnqueue`。
     7. 啟用 Media Scan。
     8. 輪詢等待 Booking Queue 非空，並驗證 `BookingQueueVB` 中必須包含 `old_slc_l2_vb`。
     9. 透過 `vu40CF` 確認 `new_scan_group != old_scan_group`。
     10. 透過 `vuC088` 設定 `StartRefresh`。
     11. 輪詢 BKOPS 至 Idle。
     12. 透過 `vu40C5` 驗證 Booking Queue 為空。
     13. 讀取 `open_vb_info.SLC_L2.logical_vb` 並與 `old_slc_l2_vb` 比較。
     14. 執行 `read_compare` 驗證資料完整性。
   - 預期結果：
     - Booking Queue 在 Refresh 前正確包含 `old_slc_l2_vb`。
     - `new_scan_group` 不等於 `old_scan_group`。
     - Refresh 後 Booking Queue 為空。
     - `new_slc_l2_vb` **不等於** `old_slc_l2_vb` (VB 號碼必須改變)。
     - HW Compare 通過。

3. **[TLC_L1_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 配置 LUN 0 並寫入 `BLOCK4K_SIZE_16K_BYTE` (1個 VB 大小) 的資料。
     3. 讀取 `open_vb_info.TLC_L1` 獲取當前 VB (`old_l1_vb`) 及 Empty 物理位置。
     4. 建構 `PCA` 結構體：`b4_mode=2` (TLC), 設定對應 CE/Plane/Page/Block，呼叫 `inject_UECC` 在 TLC L1 的 Empty Page 注入 UECC 錯誤。
     5. 記錄當前 Scan Group (`old_scan_group`)。
     6. 透過 `vuC088` 設定 `StopRefreshRefreshCanStillBeEnqueue`。
     7. 啟用 Media Scan。
     8. 輪詢等待 Booking Queue 非空，並驗證 `BookingQueueVB` 中必須包含 `old_l1_vb`。
     9. 透過 `vu40CF` 確認 `new_scan_group != old_scan_group`。
     10. 透過 `vuC088` 設定 `StartRefresh`。
     11. 輪詢 BKOPS 至 Idle。
     12. 透過 `vu40C5` 驗證 Booking Queue 為空。
     13. 讀取 `open_vb_info.TLC_L1.logical_vb` 並與 `old_l1_vb` 比較。
     14. 執行 `read_compare` 驗證資料完整性。
   - 預期結果：
     - Booking Queue 在 Refresh 前正確包含 `old_l1_vb`。
     - `new_scan_group` 不等於 `old_scan_group`。
     - Refresh 後 Booking Queue 為空。
     - `new_l1_vb` **不等於** `old_l1_vb` (VB 號碼必須改變)。
     - HW Compare 通過。

4. **[LOG_Block_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 配置 LUN 0 並寫入 `BLOCK4K_SIZE_12M_BYTE` (12MB) 的資料。
     3. 讀取 `open_vb_info.LOG` 獲取當前 VB (`old_log_vb`) 及 Empty 物理位置。
     4. 建構 `PCA` 結構體：`b4_mode=1` (SLC), 設定對應 CE/Plane/Page/Block，呼叫 `inject_UECC` 在 LOG Block 的 Empty Page 注入 UECC 錯誤。
     5. 記錄當前 Scan Group (`old_scan_group`)。
     6. 透過 `vuC088` 設定 `StopRefreshRefreshCanStillBeEnqueue`。
     7. 啟用 Media Scan。
     8. 輪詢等待 Booking Queue 非空，並驗證 `BookingQueueVB` 中必須包含 `old_log_vb`。
     9. 透過 `vu40CF` 確認 `new_scan_group != old_scan_group`。
     10. 透過 `vuC088` 設定 `StartRefresh`。
     11. 輪詢 BKOPS 至 Idle。
     12. 透過 `vu40C5` 驗證 Booking Queue 為空。
     13. 讀取 `open_vb_info.LOG.logical_vb` 並與 `old_log_vb` 比較。
     14. 執行 `read_compare` 驗證資料完整性。
   - 預期結果：
     - Booking Queue 在 Refresh 前正確包含 `old_log_vb`。
     - `new_scan_group` 不等於 `old_scan_group`。
     - Refresh 後 Booking Queue 為空。
     - `new_log_vb` **不等於** `old_log_vb` (VB 號碼必須改變)。
     - HW Compare 通過。

5. **[PTE_Block_UECC_MediaScan_Refresh_Check]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 配置 LUN 0 並寫入 4096 個節點 (Nodes) 的資料以觸發 PTE Flush。
     3. 讀取 `open_vb_info.PTE` 獲取當前 VB (`old_pte_vb`) 及 Empty 物理位置。
     4. 建構 `PCA` 結構體：`b4_mode=1` (SLC), 設定對應 CE/Plane/Page/Block，呼叫 `inject_UECC` 在 PTE Block 的 Empty Page 注入 UECC 錯誤。
     5. 記錄當前 Scan Group (`old_scan_group`)。
     6. 透過 `vuC088` 設定 `StopRefreshRefreshCanStillBeEnqueue`。
     7. 啟用 Media Scan。
     8. 輪詢等待 Booking Queue 非空，並驗證 `BookingQueueVB` 中必須包含 `old_pte_vb`。
     9. 透過 `vu40CF` 確認 `new_scan_group != old_scan_group`。
     10. 透過 `vuC088` 設定 `StartRefresh`。
     11. 輪詢 BKOPS 至 Idle。
     12. 透過 `vu40C5` 驗證 Booking Queue 為空。
     13. 讀取 `open_vb_info.PTE.logical_vb` 並與 `old_pte_vb` 比較。
     14. 執行 `read_compare` 驗證資料完整性。
   - 預期結果：
     - Booking Queue 在 Refresh 前正確包含 `old_pte_vb`。
     - `new_scan_group` 不等於 `old_scan_group`。
     - Refresh 後 Booking Queue 為空。
     - `new_pte_vb` **不等於** `old_pte_vb` (VB 號碼必須改變)。
     - HW Compare 通過。