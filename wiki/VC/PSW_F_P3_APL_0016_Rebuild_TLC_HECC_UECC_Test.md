# Test Spec: UFS FTL LWP Consistency & UECC Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在異常掉電（SPOR）情境下，FTL 的 Last Written Page (LWP) 狀態機與資料完整性保護機制：
1. **Case 01-05 (Plane 0-4)**：針對 Normal LUN 寫入 TLC 資料後，在特定 Die/Plane/Page 注入 **UECC (Unrecoverable ECC)** 錯誤。執行 **HW_RESET (無 SSU)** 後，驗證 LWP 狀態是否保持不變（LWP_A == LWP_B），且該 LBA 區域的資料因 UECC 導致讀取失敗或保留舊狀態（依據 `save_write_info` 標記為 Erase Pattern 進行比對），確認韌體在無電源循環保護下不會錯誤地推進 LWP 或修復 UECC。
2. **Case 06-7 (Plane 5-7)**：針對 Normal LUN 寫入 TLC 資料後，**不注入** UECC 錯誤。執行 **HW_RESET (無 SSU)** 後，驗證 LWP 狀態是否發生預期變化（LWP_A != LWP_B，通常因韌體內部狀態重置或垃圾回收機制導致），且該 LBA 區域的資料為新寫入資料（依據 `save_write_info` 標記為新資料進行比對），確認正常寫入流程在重置後的資料一致性。

## Test Case (TC) Checkpoints

1. **[Case01-05_UECC_NoSSU_LWP_Stability_Check]**：
   - **動作**：
     1. 配置 LUN 0 (Normal) 為 4KB LBS，並寫入 `write_len` (2 pages * ce_num * plane_ce_pages) 的 TLC 資料至 LBA 0 開始。
     2. 透過 `issue_4051_to_get_physical_address` 取得目標 LBA 對應的 `micron_pca` (Die, Plane, Block, Page)。
     3. 呼叫 `flipbit_on_TLC_smart`，在目標 Page 的 raw data 中注入 150 個 bit flip，並透過 `issue_40F6_to_erase_in_direct_nand_mode` 或 `issue_D060_to_erase_specific_block` 清除區塊，再寫入包含錯誤的 payload。
     4. 針對 Plane 0 至 4 (i < 5)，呼叫 `inject_UECC(uecc_pca)` 強制標記該物理區塊為 UECC 狀態。
     5. 呼叫 `collect_lwp_checks` 記錄重置前的 LWP 狀態為 `lwpA`。
     6. 執行 `api.init_tester_to_unit_ready` 進行 **HW_RESET**，且 `powerdown=False` (無 SSU)。
     7. 重置後，再次呼叫 `collect_lwp_checks` 記錄 LWP 狀態為 `lwpB`。
     8. 比較 `lwpA` 與 `lwpB`，並透過 `read_compare` 讀取原始寫入 LBA 區域的資料，與預期模式（Erase Pattern）進行 SW_COMPARE。
   - **預期結果**：
     - `lwpA` 與 `lwpB` 必須完全相同 (`identical == True`)。這代表在無 SSU 保護且發生 UECC 的情況下，韌體不會因為重置而錯誤地恢復或推進 LWP，保持故障前的狀態標記。
     - 資料比對必須通過，確認該區域資料未被韌體自動修復或覆蓋，符合 UECC 未修復時的預期行為（通常為讀取失敗或保留舊值，測試腳本中透過 `save_write_info` 標記為 Erase Pattern 來驗證此隔離性）。

2. **[Case06-07_NoUECC_NoSSU_LWP_Change_Check]**：
   - **動作**：
     1. 針對 Plane 5 至 7 (i >= 5)，重複上述寫入流程，但**跳過** `inject_UECC` 步驟，確保資料無 UECC 錯誤。
     2. 記錄重置前的 LWP 狀態為 `lwpA`。
     3. 執行 **HW_RESET (無 SSU)**。
     4. 記錄重置後的 LWP 狀態為 `lwpB`。
     5. 比較 `lwpA` 與 `lwpB`，並透過 `read_compare` 讀取原始寫入 LBA 區域的資料，與預期模式（新寫入資料 Pattern）進行 SW_COMPARE。
   - **預期結果**：
     - `lwpA` 與 `lwpB` 必須不同 (`identical == False`)。這代表在無 UECC 干擾的正常寫入情境下，HW_RESET 會導致韌體內部 LWP 狀態機重新初始化或發生狀態跳變（例如從寫入中狀態重置為初始狀態，或觸發內部重建導致 LWP 指標變化）。
     - 資料比對必須通過，確認該區域資料為最新寫入的內容，證明韌體在無錯誤情境下能正確處理重置後的資料可見性。