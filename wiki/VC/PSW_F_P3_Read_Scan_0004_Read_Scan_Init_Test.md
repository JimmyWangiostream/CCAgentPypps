# Test Spec: UFS Read Scan Trigger & Recovery Verification (WL Range 0-31)

## Verification Criterion (VC)
驗證 UFS 韌體在 TLC 模式下，針對不同 Wear Level (WL) 範圍注入 UECC 錯誤後，Read Scan 機制的觸發行為與狀態機轉換：
1. **WL 0-7 區間**：確認在 Read Scan 啟用且 POR 後，韌體能正確偵測並標記該 WL 為錯誤狀態（Status=1），且該 WL 被加入 `error_detected_WLs` 列表。
2. **WL 8-15 區間**：確認在累積前一次錯誤標記的情況下，再次注入 UECC 並觸發 Read Scan，韌體能同時識別舊有 WL (0-7) 與新注入 WL (8-15) 的錯誤，驗證 `error_detected_WLs` 列表的累積性。
3. **WL 16-23 區間與最終狀態**：確認在注入第三組錯誤後，執行 HW_RESET (POR) 且無額外 Read Scan 觸發指令的情況下，韌體內部掃描狀態機應重置為完成或非進行中狀態（Status=0），驗證韌體在冷啟動後的狀態初始化邏輯正確性。

## Test Case (TC) Checkpoints

1. **[WL0-7_ReadScan_Trigger_Check]**：
   - 動作：
     1. 透過 `mConfig` 暫存器清除 `BIT1` 以禁用 Read Scan，並執行 HW_RESET 確保設定生效。
     2. 對 LUN 0 順序寫入資料至 WL15，建立基礎數據分佈。
     3. 計算隨機 WL 索引 (`randWL`)，範圍限制在 `0` 至 `READ_SCAN_SAFE_AREA` 之間（確保落在 WL 0-7 區間），透過 `get_pca_and_check_not_remap` 獲取該 LBA 對應的 PCA 物理地址，並確認未發生 Remap。
     4. 呼叫 `inject_UECC(pca=pca)` 在該物理頁注入 UECC 錯誤。
     5. 透過 `get_physical_layout` 解析該頁的 `phy_WL`。
     6. 修改 `mConfig` 設定 `BIT1` 為 1 以啟用 Read Scan，並執行 HW_RESET (POR)。
     7. 發送命令 `40BF` 查詢當前 VB 掃描狀態，並讀取 `gc_read_scan_released_scan_pageline` 獲取偵測到的錯誤 WL 列表。
   - 預期結果：
     - `check_if_current_VB_scan_in_progress_completed` 回傳值必須等於 `1`（代表掃描完成且偵測到錯誤）。
     - `error_detected_WLs` 列表長度必須大於 0。
     - 列表內容必須包含步驟 5 中解析出的 `phy_WL`，證明 Read Scan 機制成功識別了 WL 0-7 區間的 UECC 錯誤。

2. **[WL8-15_Accumulative_Detection_Check]**：
   - 動作：
     1. 再次禁用 Read Scan 並執行 HW_RESET。
     2. 繼續對 LUN 0 順序寫入資料至 WL23。
     3. 計算隨機 WL 索引，範圍限制在 `READ_SCAN_SAFE_AREA` 至 `READ_SCAN_SAFE_AREA * 2` 之間（確保落在 WL 8-15 區間），獲取 PCA 並注入 UECC 錯誤，解析出新的 `phy_WL`。
     4. 啟用 Read Scan (`mConfig BIT1=1`) 並執行 HW_RESET (POR)。
     5. 發送命令 `40BF` 查詢狀態，並獲取當前的 `error_detected_WLs` 列表。
   - 預期結果：
     - `check_if_current_VB_scan_in_progress_completed` 回傳值必須等於 `1`。
     - `error_detected_WLs` 列表必須同時包含「步驟 1 中的 `phy_WL`」與「本步驟解析出的新 `phy_WL`」。
     - 此結果驗證韌體在多次 Read Scan 觸發後，能正確累積並保留之前偵測到的錯誤 WL 標記，而非僅顯示最新錯誤。

3. **[WL16-23_POR_State_Reset_Check]**：
   - 動作：
     1. 禁用 Read Scan 並執行 HW_RESET。
     2. 繼續對 LUN 0 順序寫入資料至 WL31。
     3. 計算隨機 WL 索引，範圍限制在 `READ_SCAN_SAFE_AREA * 2` 至 `READ_SCAN_SAFE_AREA * 3` 之間（確保落在 WL 16-23 區間），獲取 PCA 並注入 UECC 錯誤。
     4. 執行一次 `HW_RESET` (POR)，**不**透過 `mConfig` 啟用 Read Scan，亦**不**發送 `40BF` 觸發掃描。
     5. 韌體冷啟動後，直接發送命令 `40BF` 查詢當前 VB 掃描狀態。
   - 預期結果：
     - `check_if_current_VB_scan_in_progress_completed` 回傳值必須等於 `0`。
     - 此結果驗證在沒有主動觸發 Read Scan 的情況下，韌體在 POR 後不會自動進入「偵測到錯誤」的進行中狀態（Status=1），而是保持初始化的空閒/完成狀態（Status=0），確保狀態機不會因之前的錯誤注入而錯誤鎖定在錯誤狀態。