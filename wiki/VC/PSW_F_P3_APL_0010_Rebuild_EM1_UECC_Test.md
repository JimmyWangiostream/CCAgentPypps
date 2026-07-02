# Test Spec: EM1 LUN SLC Mode UECC Injection & SPOR LWP Consistency Test

## Verification Criterion (VC)
驗證 EM1 LUN 在 SLC 模式下，針對不同 Plane 進行 UECC 注入後，執行無 SSU 的 HW_RESET（SPOR）對 LWP (Logical Write Pointer) 狀態的影響：
1. **Plane 0 (i=0)**：在 Page 1 的 CE0 和 CE1 注入 UECC 後，LWP 狀態在 Reset 前後應保持**一致 (Identical)**。這驗證了在特定寫入序列下，韌體能正確處理或忽略這些錯誤而不改變 LWP 進度。
2. **Plane 1, 3, 5... (i 為奇數)**：除了 Page 1 的 CE0/CE1 注入外，額外在 Page 0 的 CE0 (Non-LWP 區域) 注入 UECC。此情境下，LWP 狀態在 Reset 前後應**不同 (Different)**。這驗證了 Non-LWP 區域的錯誤注入可能觸發韌體內部狀態機變化或 LWP 回滾/跳躍機制，導致 Reset 後 LWP 指針發生位移。
3. **資料完整性**：驗證寫入資料與預期模式（新資料 vs 舊資料/擦除模式）在 SW Compare 下完全匹配，確保 UECC 注入未導致資料損壞或讀取失敗。

## Test Case (TC) Checkpoints
1. [EM1_SLC_UECC_SPOR_LWP_Consistency_Check]:
   - 動作：
     1. 配置 LUN 0 (Normal), 1 (BootA), 2 (BootB), 3 (EM1) 為 ENABLE 狀態，其中 EM1 LUN 設定為 Enhanced_1 記憶體類型。
     2. 針對 EM1 LUN (LUN 3) 執行 Sequential Write，寫入長度為 `slc_ce_page * ce_num * 2` 的資料（對應 2 個 SLC Page），並使用 `HW_COMPARE` 驗證寫入正確性。
     3. 透過 `issue_40C1` 獲取當前 EM1 LUN 的 Open VB 號碼 (`vb`)。
     4. 針對每個 Plane `i` (0 到 `Plane_Per_Die - 1`) 執行以下循環：
        - **UECC 注入**：
          - 計算 PCA：Block 由 `vb` 決定，CE=0，Plane=`i`，Page=`newdata_pages - 1` (即 Page 1)。
          - 呼叫 `inject_UECC(uecc_pca)` 在 Page 1 CE0 Plane `i` 注入 UECC。
          - 若 `ce_num > 1`，將 CE 設為 1，再次呼叫 `inject_UECC` 在 Page 1 CE1 Plane `i` 注入 UECC。
        - **Non-LWP 注入 (僅奇數 Plane)**：
          - 若 `i % 2 == 1`，將 PCA 的 Page 設為 0 (Page 0)，CE 設為 0，呼叫 `inject_UECC` 在 Page 0 CE0 Plane `i` 注入 UECC。記錄此區域為 `nonlwp_old_data_startlba`。
        - **LWP 快照 A**：呼叫 `collect_lwp_checks` 獲取 Reset 前的 LWP 狀態 (`lwpA`)。
        - **SPOR 執行**：呼叫 `api.init_tester_to_unit_ready` 執行 `HW_RESET` (無 SSU)。
        - **LWP 快照 B**：Reset 後，再次呼叫 `issue_40C1` 獲取 Open VB，並呼叫 `collect_lwp_checks` 獲取 Reset 後的 LWP 狀態 (`lwpB`)。
        - **LWP 比對**：呼叫 `compare_lwp_checks` 比較 `lwpA` 與 `lwpB`。
          - 若 `i == 0` (Plane 0)，預期 `identical == True`。
          - 若 `i % 2 != 0` (奇數 Plane)，預期 `identical == False`。
        - **資料驗證準備**：根據 `i` 的奇偶性設定 `save_write_info` 的參數，定義預期讀取的資料模式（新資料或擦除模式）。
        - **資料讀取驗證**：呼叫 `read_compare` 使用 `SW_COMPARE` 驗證讀取資料與預期模式一致。
   - 預期結果：
     - **Plane 0 (i=0)**：`lwpA` 與 `lwpB` 必須完全相同 (`identical == True`)。若不同，測試失敗並拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - **奇數 Plane (i=1, 3...)**：`lwpA` 與 `lwpB` 必須不同 (`identical == False`)。若相同，測試失敗並拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 所有 LUN 的資料讀取驗證必須通過，無資料錯誤。