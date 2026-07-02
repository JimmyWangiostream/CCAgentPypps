# Test Spec: UFS LWP Persistence & Data Integrity under UECC Injection without SSU

## Verification Criterion (VC)
驗證在無 Secure Storage Unit (SSU) 保護的硬體重啟 (HW_RESET) 情境下，韌體對 LWP (Last Write Point) 狀態的處理邏輯與資料完整性：
1. **LWP 狀態變更驗證**：確認在 Normal LUN 寫入資料並注入 UECC 錯誤後，執行 HW_RESET 且無 SSU 流程，韌體不會自動修復或重置 LWP，導致 LWP 指標發生改變（LWP_A != LWP_B），證明韌體在無保護機制下會保留異常狀態或進入非預期狀態。
2. **資料一致性驗證**：
   - 對於**非 LWP 區域**（Non-LWP）注入的 UECC 錯誤，確認讀取時會恢復為之前的舊資料（Erase Pattern），證明韌體在讀取時能透過備份或舊狀態還原非當前 LWP 的資料。
   - 對於**LWP 區域**（LWP）注入的 UECC 錯誤，確認讀取時會返回錯誤或異常資料，證明 UECC 錯誤直接影響當前寫入點的資料完整性，且未被韌體自動修正。
3. **多 CE/Plane 覆蓋驗證**：透過迴圈遍歷所有 Plane，確認上述行為在每個 CE (Chip Enable) 和 Plane 組合下均一致，排除特定硬體路徑的例外情況。

## Test Case (TC) Checkpoints

1. [Case01_LWP_Change_Verification]：
   - 動作：
     1. 配置 LUN (Normal LUN 0, Boot A/B, EM1)，設定 PSA State 為 OFF 後轉為 PRE_SOLDERING。
     2. 針對 Normal LUN (LUN 0) 從 LBA 0 開始順序寫入 2 頁 SLC 大小的資料 (write_len = slc_ce_page * ce_num * 2)。
     3. 透過 `get_and_print_open_vb_information` 取得當前 Open VB 資訊，並建構 `uecc_pca` 結構體，針對 Page 1 (newdata_pages-1) 的 CE0 及當前 Plane `i` 注入 UECC 錯誤 (`inject_UECC`)。
     4. 若 ce_num > 1，額外對 CE1 注入 UECC。
     5. 若 Plane `i` 為奇數，額外在 Page 0 (Non-LWP 區域) 的 CE0 注入 UECC。
     6. 呼叫 `collect_lwp_checks` 記錄重置前的 LWP 狀態為 `lwpA`。
     7. 執行 `api.init_tester_to_unit_ready` 進行 HW_RESET (無 SSU)。
     8. 重置後再次呼叫 `collect_lwp_checks` 記錄當前 LWP 狀態為 `lwpB`。
     9. 呼叫 `compare_lwp_checks` 比對 `lwpA` 與 `lwpB`。
   - 預期結果：
     - `compare_lwp_checks` 回傳 `identical == False`。
     - 這代表在無 SSU 保護下，HW_RESET 後 LWP 指標發生了改變（通常指向錯誤狀態或恢復到某個不一致點），驗證了韌體在無保護機制下無法維持穩定的 LWP 狀態。

2. [Case02_Data_Integrity_NonLWP_UECC]：
   - 動作：
     1. 在 Case01 的 HW_RESET 後，針對 Normal LUN 執行讀取比較 (`read_compare`)。
     2. 特別關注當 Plane `i` 為奇數時，在 Non-LWP 區域 (Page 0, LBA 偏移 4*i) 注入的 UECC 錯誤。
     3. 讀取該 Non-LWP 區域的資料，並與寫入前的舊資料模式 (PTN_ERASE) 進行 SW_COMPARE。
   - 預期結果：
     - Non-LWP 區域的讀取資料必須等於寫入前的舊資料（Erase Pattern / 0xFF 或特定舊 Pattern）。
     - 這證明韌體在讀取 Non-LWP 區域時，即使該處有 UECC 錯誤，也能透過韌體邏輯（如備份頁或舊 VB 狀態）還原出正確的舊資料，顯示 Non-LWP 區域的資料保護機制獨立於當前 LWP 狀態。

3. [Case03_Data_Integrity_LWP_UECC]：
   - 動作：
     1. 在 Case01 的 HW_RESET 後，針對 Normal LUN 執行讀取比較 (`read_compare`)。
     2. 關注 LWP 區域（Page 1, CE0/CE1）注入 UECC 錯誤的 LBA 範圍。
     3. 讀取該 LWP 區域的資料，並與寫入記錄 (`write_record`) 中的預期資料進行比對。
   - 預期結果：
     - LWP 區域的讀取資料**不應該**等於寫入時的預期資料，或者讀取操作會觸發錯誤處理機制。
     - 這證明在無 SSU 保護且 LWP 狀態異常的情況下，當前寫入點 (LWP) 的資料因 UECC 錯誤而損毀，且韌體未能在 HW_RESET 後自動修復該 LWP 的資料完整性，導致資料讀取失敗或數據錯誤。