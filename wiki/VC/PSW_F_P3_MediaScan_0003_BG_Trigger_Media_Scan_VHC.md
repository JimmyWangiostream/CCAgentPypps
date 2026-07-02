# Test Spec: UFS Media Scan & Refresh UECC Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Media Scan 機制下，針對不同邏輯區塊（LUN）與不同 VB 類型（TLC L2, SLC L2, TLC L1, LOG, PTE, Used Pool MLC/SLC）注入 UECC 錯誤後的自動修復行為：
1. **Booking Queue 機制驗證**：確認在 `C088` 暫停 Refresh 但允許入隊的情境下，Media Scan 能正確偵測到錯誤 VB 並將其加入 Booking Queue，且掃描進度（Scan Group）會跳過已處理區塊。
2. **Refresh 執行與狀態恢復**：確認啟動 Refresh 後，BKOPS 完成時 Booking Queue 清空，且對應的 VB Logical Number 發生改變（代表壞塊被替換或修復）。
3. **資料完整性驗證**：確認修復後的資料讀寫比對（Read Compare）通過，確保韌體在處理 UECC 時未破壞數據一致性。
4. **多維度覆蓋**：涵蓋 Normal LUN (TLC/SLC)、系統關鍵區塊 (L1/LOG/PTE) 以及內部管理區塊 (Used Pool)，確保所有層級的 UECC 均能被 Media Scan 偵測並透過 Refresh 機制修復。

## Test Case (TC) Checkpoints

1. **[TC01_TLC_L2_UECC_Recovery]**：
   - 動作：配置 LUN 0 (Normal) 為 TLC 模式，寫入一個 WL 大小的資料量。取得當前 `TLC_L2` 的 Logical VB 號碼 (`old_tlc_l2_vb`) 及物理位置 (PCA)。透過 `inject_UECC` 在該 VB 的 Page 0 注入 UECC 錯誤。關閉 Media Scan，設定 `C085` 參數觸發 Idle Media Scan，開啟 Media Scan。輪詢檢查 `C085` 回應中的 `scan_group` 是否改變，並透過 `C085` 確認 Booking Queue 中已包含 `old_tlc_l2_vb`。接著發送 `C088` 啟動 Refresh，輪詢 BKOPS 至 Idle。檢查 `C085` Booking Queue 是否為空，並讀取 `open_vb_info` 確認 `TLC_L2.logical_vb` 已改變。最後執行 Read Compare。
   - 預期結果：Booking Queue 中必須出現 `old_tlc_l2_vb`；Refresh 完成後，`TLC_L2.logical_vb` 必須不等於 `old_tlc_l2_vb`（代表 VB 已遷移/修復）；Read Compare 必須通過，無資料錯誤。

2. **[TC02_SLC_L2_UECC_Recovery]**：
   - 動作：配置 LUN 1 (Enhanced 1) 為 SLC 模式，寫入一個 WL 大小的資料量。取得當前 `SLC_L2` 的 Logical VB 號碼 (`old_slc_l2_vb`) 及物理位置 (PCA)。透過 `inject_UECC` 在該 VB 的 Page 0 注入 UECC 錯誤。關閉 Media Scan，設定 `C085` 參數觸發 Idle Media Scan，開啟 Media Scan。輪詢檢查 `C085` 回應中的 `scan_group` 是否改變，並透過 `C085` 確認 Booking Queue 中已包含 `old_slc_l2_vb`。接著發送 `C088` 啟動 Refresh，輪詢 BKOPS 至 Idle。檢查 `C085` Booking Queue 是否為空，並讀取 `open_vb_info` 確認 `SLC_L2.logical_vb` 已改變。最後執行 Read Compare。
   - 預期結果：Booking Queue 中必須出現 `old_slc_l2_vb`；Refresh 完成後，`SLC_L2.logical_vb` 必須不等於 `old_slc_l2_vb`；Read Compare 必須通過。

3. **[TC03_TLC_L1_UECC_Recovery]**：
   - 動作：配置 LUN 0，寫入一個 VB 大小的資料。取得當前 `TLC_L1` 的 Logical VB 號碼 (`old_l1_vb`)。手動構造 PCA，設定 `b4_mode=2` (L1 Mode)，指定 CE 0, Plane 0, Block 為 `old_l1_vb`，Page 0。透過 `inject_UECC` 注入 UECC。關閉 Media Scan，設定 `C085` 參數觸發 Idle Media Scan，開啟 Media Scan。輪詢檢查 `C085` 回應中的 `scan_group` 是否改變，並透過 `C085` 確認 Booking Queue 中已包含 `old_l1_vb`。接著發送 `C088` 啟動 Refresh，輪詢 BKOPS 至 Idle。檢查 `C085` Booking Queue 是否為空，並讀取 `open_vb_info` 確認 `TLC_L1.logical_vb` 已改變。最後執行 Read Compare。
   - 預期結果：Booking Queue 中必須出現 `old_l1_vb`；Refresh 完成後，`TLC_L1.logical_vb` 必須不等於 `old_l1_vb`；Read Compare 必須通過。

4. **[TC04_LOG_Block_UECC_Recovery]**：
   - 動作：配置 LUN 0，寫入 12MB 資料以填充 LOG 區塊。取得當前 `LOG` 的 Logical VB 號碼 (`old_log_vb`)。手動構造 PCA，設定 `b4_mode=1` (Log Mode)，指定 CE 0, Plane 0, Block 為 `old_log_vb`，Page 0。透過 `inject_UECC` 注入 UECC。關閉 Media Scan，設定 `C085` 參數觸發 Idle Media Scan，開啟 Media Scan。輪詢檢查 `C085` 回應中的 `scan_group` 是否改變，並透過 `C085` 確認 Booking Queue 中已包含 `old_log_vb`。接著發送 `C088` 啟動 Refresh，輪詢 BKOPS 至 Idle。檢查 `C085` Booking Queue 是否為空，並讀取 `open_vb_info` 確認 `LOG.logical_vb` 已改變。
   - 預期結果：Booking Queue 中必須出現 `old_log_vb`；Refresh 完成後，`LOG.logical_vb` 必須不等於 `old_log_vb`。

5. **[TC05_PTE_Block_UECC_Recovery]**：
   - 動作：配置 LUN 0，寫入 4096 個節點大小的資料以觸發 PTE Flush。取得當前 `PTE` 的 Logical VB 號碼 (`old_pte_vb`)。手動構造 PCA，設定 `b4_mode=1` (Log Mode，PTE 通常歸類於 Log/Control 區)，指定 CE 0, Plane 0, Block 為 `old_pte_vb`，Page 0。透過 `inject_UECC` 注入 UECC。關閉 Media Scan，設定 `C085` 參數觸發 Idle Media Scan，開啟 Media Scan。輪詢檢查 `C085` 回應中的 `scan_group` 是否改變，並透過 `C085` 確認 Booking Queue 中已包含 `old_pte_vb`。接著發送 `C088` 啟動 Refresh，輪詢 BKOPS 至 Idle。檢查 `C085` Booking Queue 是否為空，並讀取 `open_vb_info` 確認 `PTE.logical_vb` 已改變。
   - 預期結果：Booking Queue 中必須出現 `old_pte_vb`；Refresh 完成後，`PTE.logical_vb` 必須不等於 `old_pte_vb`。

6. **[TC06_Used_Pool_MLC_UECC_Recovery]**：
   - 動作：配置 LUN 0，寫入一個 TLC VB 大小的資料。透過 `get_PCA_and_print` 獲取當前寫入位置的 PCA，並確認該 VB 屬於 `VB_GROUP.USED_BLK_POOL_MLC`。記錄 `old_used_pool_mlc_vb`。透過 `inject_UECC` 注入 UECC。關閉 Media Scan，設定 `C085` 參數觸發 Idle Media Scan，開啟 Media Scan。輪詢檢查 `C085` 回應中的 `scan_group` 是否改變，並透過 `C085` 確認 Booking Queue 中已包含 `old_used_pool_mlc_vb`。接著發送 `C088` 啟動 Refresh，輪詢 BKOPS 至 Idle。檢查 `C085` Booking Queue 是否為空，並透過 `get_PCA_and_print` 獲取新的 PCA，確認新的 Block VB 號碼 (`new_used_pool_mlc_vb`) 不等於 `old_used_pool_mlc_vb`。最後執行 Read Compare。
   - 預期結果：Booking Queue 中必須出現 `old_used_pool_mlc_vb`；Refresh 完成後，當前寫入位置的 Block VB 號碼必須改變；Read Compare 必須通過。

7. **[TC07_Used_Pool_SLC_UECC_Recovery]**：
   - 動作：配置 LUN 1，寫入一個 SLC VB 大小的資料。透過 `get_PCA_and_print` 獲取當前寫入位置的 PCA，並確認該 VB 屬於 `VB_GROUP.USED_BLK_POOL_SLC`。記錄 `old_used_pool_slc_vb`。透過 `inject_UECC` 注入 UECC。關閉 Media Scan，設定 `C085` 參數觸發 Idle Media Scan，開啟 Media Scan。輪詢檢查 `C085` 回應中的 `scan_group` 是否改變，並透過 `C085` 確認 Booking Queue 中已包含 `old_used_pool_slc_vb`。接著發送 `C088` 啟動 Refresh，輪詢 BKOPS 至 Idle。檢查 `C085` Booking Queue 是否為空，並透過 `get_PCA_and_print` 獲取新的 PCA，確認新的 Block VB 號碼 (`new_used_pool_slc_vb`) 不等於 `old_used_pool_slc_vb`。最後執行 Read Compare。
   - 預期結果：Booking Queue 中必須出現 `old_used_pool_slc_vb`；Refresh 完成後，當前寫入位置的 Block VB 號碼必須改變；Read Compare 必須通過。