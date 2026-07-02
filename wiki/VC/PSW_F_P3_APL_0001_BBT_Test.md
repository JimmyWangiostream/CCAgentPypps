# Test Spec: BBT UECC Injection & SPOR Recovery Validation

## Verification Criterion (VC)
驗證韌體在 BBT (Bad Block Table) 頁面遭遇 UECC (Uncorrectable ECC) 錯誤時的硬體行為與韌體恢復/崩潰機制：
1.  **VC1 (Baseline)**：確認在無錯誤注入且無 SSU 的 HW_RESET 後，BBT 的 PCA (Physical Channel Address) 資訊（Block, CE, Plane）保持不變，證明韌體能正確讀取並維持 BBT 結構。
2.  **VC2 (Single Page UECC Recovery)**：確認在 BBT Page 0 注入 UECC 後，執行 HW_RESET 會觸發 BBT 重建機制，導致讀回的 BBT PCA 發生改變（Refresh），證明韌體能檢測錯誤並重新生成有效的 BBT 映射。
3.  **VC3 (Second Page UECC Recovery)**：確認在 BBT Page 1 注入 UECC 後，執行 HW_RESET 同樣會觸發 BBT 重建機制，導致 BBT PCA 再次改變，證明多頁面錯誤注入下的重建邏輯一致性。
4.  **VC4 (Critical Failure)**：確認當 BBT Page 0 與 Page 1 **同時**注入 UECC 時，韌體無法重建 BBT，導致 `init_tester_to_unit_ready` 初始化失敗並觸發 FW Assert，證明雙重關鍵錯誤會導致系統初始化崩潰。

## Test Case (TC) Checkpoints

1.  **[VC1_Baseline_PCA_Stability_Check]**：
    -   動作：透過 VU 0x4097 讀取初始 BBT 物理區塊資訊 (`bbt_sub_vb_info`)，提取其 Block, CE, Plane 組成 `direc_read_pca`。針對 Normal LUN (LUN 0) 寫入 `tlc_ce_page` 大小資料，針對 Boot LUN (LUN 1) 寫入 `slc_ce_page` 大小資料。執行 `HW_RESET` (無 SSU)。重置後再次透過 VU 0x4097 讀取 BBT 資訊組成 `direc_read_pca_after`。
    -   預期結果：`compare_pca_info(direc_read_pca_after, direc_read_pca)` 必須返回 `True`。即 BBT 的 Block, CE, Plane 欄位數值在無錯誤注入的硬體重啟後必須完全一致，證明基礎 BBT 讀取機制正常且未發生意外重建。

2.  **[VC2_Page0_UECC_Recovery_Check]**：
    -   動作：基於 VC1 的 `direc_read_pca_after`，呼叫 `inject_UECC` 函數在 BBT Page 0 注入 UECC 錯誤。接著對 Normal LUN 與 Boot LUN 執行相同的 Sequential Write。執行 `HW_RESET` (無 SSU)。重置後讀取 BBT 資訊組成 `direc_read_pca_after3`。
    -   預期結果：`compare_pca_info(direc_read_pca_after3, direc_read_pca_after)` 必須返回 `False`。即 BBT 的 PCA 資訊必須發生改變，證明韌體在檢測到 Page 0 的 UECC 後，執行了 BBT 重建流程，產生了新的物理區塊映射。

3.  **[VC3_Page1_UECC_Recovery_Check]**：
    -   動作：基於 VC2 的 `direc_read_pca_after3`，修改其 `l12_fpage` 欄位為 `1<<5` (指向 Page 1)，呼叫 `inject_UECC` 在 BBT Page 1 注入 UECC 錯誤。接著對 Normal LUN 與 Boot LUN 執行相同的 Sequential Write。執行 `HW_RESET` (無 SSU)。重置後讀取 BBT 資訊組成 `direc_read_pca_after5`。
    -   預期結果：`compare_pca_info(direc_read_pca_after5, direc_read_pca_after3)` 必須返回 `False`。即 BBT 的 PCA 資訊必須再次發生改變，證明韌體在檢測到 Page 1 的 UECC 後，同樣執行了 BBT 重建流程。

4.  **[VC4_Dual_Page_UECC_Init_Failure_Check]**：
    -   動作：基於 VC3 的最終狀態 `direc_read_pca_after5`，先呼叫 `inject_UECC` 在 BBT Page 0 注入錯誤，再修改 `l12_fpage` 為 `1<<5` 並呼叫 `inject_UECC` 在 BBT Page 1 注入錯誤（雙重 UECC）。接著對 Normal LUN 與 Boot LUN 執行相同的 Sequential Write。執行 `HW_RESET` (無 SSU)，並預期 `api.init_tester_to_unit_ready` 拋出異常。
    -   預期結果：`api.init_tester_to_unit_ready` 必須拋出異常 (Exception)，且程式碼中的 `status` 變數應為 `False`。若未拋出異常，則測試失敗。這證明當 BBT 的關鍵頁面 (Page 0 和 Page 1) 同時損毀時，韌體無法恢復，導致系統初始化失敗並觸發 Assert。