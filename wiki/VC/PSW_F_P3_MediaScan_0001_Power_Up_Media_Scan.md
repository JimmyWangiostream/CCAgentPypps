# Test Spec: UFS Media Scan UECC Recovery Verification for L2/L1/LOG/PTE

## Verification Criterion (VC)
驗證 UFS 韌體在硬體重置（HW_RESET）後，Media Scan 機制對不同邏輯區塊（L2, L1, LOG, PTE）中注入的 Empty Page UECC 錯誤之恢復行為：
1. **TLC L2 (LUN 0)**：確認注入 4 個空頁 UECC 後，韌體能識別並修復，導致 Logical VB 號碼發生變更（代表區塊替換或重建），且後續讀寫資料完整性無損。
2. **SLC L2 (LUN 1)**：確認注入 4 個空頁 UECC 後，韌體能識別並修復，導致 Logical VB 號碼發生變更，且資料完整性無損。
3. **TLC L1 (LUN 0)**：確認注入 4 個空頁 UECC 後，韌體能識別並修復，導致 Logical VB 號碼發生變更，且資料完整性無損。
4. **LOG Block**：確認注入 4 個空頁 UECC 後，韌體能識別並修復，導致 Logical VB 號碼發生變更。
5. **PTE Block**：確認注入 4 個空頁 UECC 後，韌體能識別並修復，導致 Logical VB 號碼發生變更。
所有 Case 均透過 `vuC08B` 關閉 Media Scan 以確保錯誤在重置前未被自動掃描修復，重置後由韌體主動觸發 Media Scan 進行修復驗證。

## Test Case (TC) Checkpoints

1. **[TLC_L2_UECC_Recovery_Check]**：
   - 動作：透過 `vuC08B` Vendor Command 關閉 Media Scan；配置 LUN 0 (Normal) 並寫入一個 WL 大小（`TLC_WL_block`）的資料；取得 TLC L2 的 Logical VB (`old_tlc_l2_vb`) 及第一個空頁位置 (`empty_page`)；設定 PCA 模式為 2 (TLC)，針對 `empty_page` 開始的 4 個頁面（步長 3，即 page 0, 3, 6, 9）注入 Empty Page UECC 錯誤；執行 HW_RESET 並啟動 Media Scan；讀取新的 TLC L2 Logical VB (`new_tlc_l2_vb`) 並與舊值比對；最後對原寫入區域執行 Read Compare。
   - 預期結果：`new_tlc_l2_vb` 必須不等於 `old_tlc_l2_vb`（VB 號碼變更代表韌體已將受損區塊標記並替換/修復）；Read Compare 必須通過，證明資料完整性恢復。

2. **[SLC_L2_UECC_Recovery_Check]**：
   - 動作：透過 `vuC08B` Vendor Command 關閉 Media Scan；配置 LUN 1 (Enhanced 1) 並寫入一個 WL 大小（`SLC_WL_block`）的資料；取得 SLC L2 的 Logical VB (`old_slc_l2_vb`) 及第一個空頁位置 (`empty_page`)；設定 PCA 模式為 1 (SLC)，針對 `empty_page` 開始的 4 個連續頁面（page 0, 1, 2, 3）注入 Empty Page UECC 錯誤；執行 HW_RESET 並啟動 Media Scan；讀取新的 SLC L2 Logical VB (`new_slc_l2_vb`) 並與舊值比對；最後對原寫入區域執行 Read Compare。
   - 預期結果：`new_slc_l2_vb` 必須不等於 `old_slc_l2_vb`（VB 號碼變更代表韌體已將受損區塊標記並替換/修復）；Read Compare 必須通過，證明資料完整性恢復。

3. **[TLC_L1_UECC_Recovery_Check]**：
   - 動作：透過 `vuC08B` Vendor Command 關閉 Media Scan；配置 LUN 0 (Normal) 並寫入 16KB (1 Block) 的資料；取得 TLC L1 的 Logical VB (`old_l1_vb`) 及第一個空頁位置 (`empty_page`)；將 `empty_page` 偏移 +3 後，設定 PCA 模式為 2 (TLC)，針對新起始位置的 4 個頁面（步長 3，即 page 3, 6, 9, 12）注入 Empty Page UECC 錯誤；執行 HW_RESET 並啟動 Media Scan；讀取新的 TLC L1 Logical VB (`new_l1_vb`) 並與舊值比對；最後對原寫入區域執行 Read Compare。
   - 預期結果：`new_l1_vb` 必須不等於 `old_l1_vb`（VB 號碼變更代表韌體已將受損區塊標記並替換/修復）；Read Compare 必須通過，證明資料完整性恢復。

4. **[LOG_Block_UECC_Recovery_Check]**：
   - 動作：透過 `vuC08B` Vendor Command 關閉 Media Scan；配置 LUN 0 (Normal) 並寫入 12MB 的資料；取得 LOG Block 的 Logical VB (`old_log_vb`) 及第一個空頁位置 (`empty_page`)；設定 PCA 模式為 1 (SLC)，針對 `empty_page` 開始的 4 個連續頁面（page 0, 1, 2, 3）注入 Empty Page UECC 錯誤；執行 HW_RESET 並啟動 Media Scan；讀取新的 LOG Logical VB (`new_log_vb`) 並與舊值比對。
   - 預期結果：`new_log_vb` 必須不等於 `old_log_vb`（VB 號碼變更代表韌體已將受損區塊標記並替換/修復）。

5. **[PTE_Block_UECC_Recovery_Check]**：
   - 動作：透過 `vuC08B` Vendor Command 關閉 Media Scan；配置 LUN 0 (Normal) 並寫入 4096 個節點（觸發 PTE Flush）的資料；取得 PTE Block 的 Logical VB (`old_pte_vb`) 及第一個空頁位置 (`empty_page`)；設定 PCA 模式為 1 (SLC)，針對 `empty_page` 開始的 4 個連續頁面（page 0, 1, 2, 3）注入 Empty Page UECC 錯誤；執行 HW_RESET 並啟動 Media Scan；讀取新的 PTE Logical VB (`new_pte_vb`) 並與舊值比對。
   - 預期結果：`new_pte_vb` 必須不等於 `old_pte_vb`（VB 號碼變更代表韌體已將受損區塊標記並替換/修復）。