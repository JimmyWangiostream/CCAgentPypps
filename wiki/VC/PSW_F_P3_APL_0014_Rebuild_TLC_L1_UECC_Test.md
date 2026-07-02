# Test Spec: UFS FTL LWP Consistency Check under UECC Injection and HW_RESET (No SSU)

## Verification Criterion (VC)
驗證韌體在 **無 Secure Storage Unit (SSU)** 保護的硬體重啟 (HW_RESET) 情境下，針對 **TLC LUN (LUN 0)** 的 **L2 (Logical-to-Physical Mapping)** 狀態機行為：
1.  **LWP 狀態變更驗證**：確認在對特定 CE/Plane 的 TLC Page 注入 **UECC (Unrecoverable ECC)** 錯誤後，執行 `HW_RESET` 且 **不觸發 SSU** 流程，韌體應能正確識別該 Page 為損壞狀態，並導致該 Plane 的 **LWP (Last Written Page)** 指標發生跳躍或變更（LWP_B != LWP_A），以反映該物理區塊已進入不可用或需重新映射的狀態。
2.  **LBA 映射一致性驗證**：確認在 LWP 發生變更後，透過 L1 列表查詢到的有效 LBA 範圍與預期寫入的 LBA 範圍一致，且未包含已注入 UECC 錯誤的損壞 LBA，確保韌體在無 SSU 保護下仍能維持基本的 LBA 到 Physical Address 的映射邏輯正確性，避免指向已損壞的 Page。

## Test Case (TC) Checkpoints

1.  **[Case01_TLC_UECC_Injection_and_HW_Reset_Check]**：
    -   **動作**：
        1.  配置 LUN 0 (Normal), LUN 1 (Boot A), LUN 2 (Boot B), LUN 3 (EM1)，並初始化測試環境。
        2.  針對 **LUN 0 (Normal LUN)** 執行順序寫入，寫入長度為 `tlc_ce_page * ce_num * 2` (即 2 個 TLC Write Block 的容量)，並使用 `HW_COMPARE` 確保資料寫入成功。
        3.  透過 `issue_40C1_to_get_open_vb_information` 獲取當前 Open VB 資訊，鎖定目標 VB。
        4.  計算目標物理地址：針對每個 Plane (`i` from 0 to `Plane_Per_Die-1`)，鎖定 **CE 0** 的 **第 2 個 TLC Page** (Index 1, 因為 `newdata_pages=2`, `(newdata_pages-1)<<5` 對應 Page 1 的起始偏移，實際計算邏輯指向該 Page)。
        5.  使用 `inject_UECC(uecc_pca)` 在該特定 PCA (CE=0, Plane=i, Mode=TLC, Page=1) 注入 **UECC 錯誤**。
        6.  使用 `direct_read_raw_data_and_check_status` 讀取該 Page，預期狀態為 `ReadStatus.UECC`，確認錯誤注入成功。
        7.  記錄注入 UECC 後的 LWP 狀態為 **LWP_A** (`collect_lwp_checks`)。
        8.  執行 **HW_RESET** 且 **無 SSU** (透過 `push_spor_times(10)` 模擬瞬間掉電重啟，未觸發 Secure Storage Unit 的完整電源循環與韌體重建流程)。
        9.  重啟後，再次獲取 Open VB 資訊，並記錄新的 LWP 狀態為 **LWP_B** (`collect_lwp_checks`)。
        10. 比較 LWP_A 與 LWP_B，並檢查 L1 列表中有效 LBA 的連續性與範圍。
    -   **預期結果**：
        1.  **LWP 必須變更**：`compare_lwp_checks` 返回 `identical == False`。這代表韌體在重啟後，偵測到原 LWP 指向的 Page 存在 UECC 錯誤，因此將該 Plane 的 LWP 指標向前或向後調整（通常是指向下一個可用 Page 或標記為損壞），確保後續寫入不會覆蓋損壞區塊。
        2.  **LBA 映射正確**：若 LWP 變更導致映射改變，查詢到的有效 LBA 列表 (`lbalist`) 應反映寫入後的實際狀態。若 LWP 未變但 Page 損壞，韌體應在讀取時返回錯誤，但在寫入路徑上應避免再次使用該 Page。驗證邏輯中檢查 `is_plus_one` 確保 LBA 連續性，若 LWP 變更導致 LBA 斷層，則需確認韌體是否正確處理了該斷層（例如標記為未分配或保留）。核心驗證點在於 **LWP 狀態碼的改變** 與 **UECC 錯誤在無 SSU 下未被自動修復（仍為 UECC 標記）** 的事實。