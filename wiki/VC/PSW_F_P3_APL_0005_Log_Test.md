# Test Spec: UFS Log LWP UECC Injection & SPOR Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 **Log LWP (Logical Write Pointer)** 發生 **UECC (Uncorrectable Error Correction Code)** 錯誤且 **無 SSU (Secure Storage Unit)** 保護下的 **HW_RESET (Hard Reset)** 行為：
1.  **Case 01 (Last Valid Page)**：確認當 UECC 注入於 Log LWP 的最後一個有效頁面（Last Valid Page）時，韌體在 SPOR (Start of Power On Reset) 後能正確識別錯誤並觸發 Log 列表刷新（List Refresh），導致 VB (Version Block) 號碼與 FEP (First Free Physical Page) 發生預期變更，且韌體恢復正常運作。
2.  **Case 02 (Intermediate Valid Page)**：確認當 UECC 注入於 Log LWP 的中间有效頁面（Intermediate Valid Page，具體為 splitinfo 列表中的特定索引）時，韌體同樣能觸發 Log 列表刷新機制，確保 VB 號碼與 FEP 發生變更，驗證韌體對非末尾位置 UECC 的處理一致性。
3.  **控制邏輯驗證**：透過比較注入前後的 `LOG_block_VB_number_logical` 與 `LOG_Block_First_free_physical_page`，驗證韌體是否正確執行 Log Reconstruction 而非靜默失敗或崩潰。

## Test Case (TC) Checkpoints

1.  **[Case01_LastValidPage_UECC_SPOR_Check]**：
    -   **動作**：
        1.  初始化測試環境，配置 LUN (Normal, BootA, BootB, EM1)，並獲取初始 Flash 幾何資訊。
        2.  透過 Vendor Command (VU 0x40C1) 讀取 Open VB 資訊，記錄初始狀態 `open_vb_1` (Table 1)。
        3.  執行 **HW_RESET without SSU**，讀取 Open VB 資訊記錄為 `open_vb_2` (Table 2)。
        4.  **驗證點 A**：確認 `open_vb_1.LOG_block_VB_number_logical` 等於 `open_vb_2.LOG_block_VB_number_logical`，證明無 SSU 的硬體重啟未觸發韌體狀態變更。
        5.  讀取當前 Open VB 資訊為 `open_vb_current` (Table 3)，計算 CE/Plane/Page 對應關係。
        6.  透過 `api.direct_read` 掃描 Log LWP 頁面，尋找 payload 偏移量 `0x4004` 處數值為 `0x94` 的有效頁面。記錄第一個找到的有效頁面索引為 `lastvalid` (即 Last Valid Page)。
        7.  呼叫 `injectUECC_from_FEP`，針對 `open_vb_current` 的 VB 號碼與 FEP，在偏移量 `lastvalid - 1` 處注入 UECC 錯誤。
        8.  執行 **HW_RESET without SSU** (透過 `SPOR_init_mp`)。
        9.  韌體恢復後，讀取 Open VB 資訊記錄為 `open_vb_after` (Table 4)。
        10. 比較 `open_vb_current` 與 `open_vb_after` 的 VB 號碼與 FEP。
    -   **預期結果**：
        -   `SPOR_init_mp()` 必須返回 `True` (表示韌體恢復成功)。
        -   `open_vb_current.LOG_block_VB_number_logical` **不等於** `open_vb_after.LOG_block_VB_number_logical` **或者** `open_vb_current.LOG_Block_First_free_physical_page` **不等於** `open_vb_after.LOG_Block_First_free_physical_page`。
        -   這代表韌體檢測到 Log LWP 的 UECC 錯誤後，執行了 Log 列表重建/刷新機制，導致邏輯區塊版本號與物理頁面指針發生改變。

2.  **[Case02_IntermediatePage_UECC_SPOR_Check]**：
    -   **動作**：
        1.  韌體恢復後，再次讀取 Open VB 資訊為 `open_vb_current` (Table 5)。
        2.  重複掃描 Log LWP 頁面，尋找 payload `0x4004` 為 `0x94` 的有效頁面，並將所有找到的索引存入 `splitinfo` 列表。
        3.  根據 `splitinfo` 的長度選擇注入目標：若長度 > 3，選擇索引 `splitinfo[1]`；若長度 > 2，選擇索引 `splitinfo[0]`。此目標為中間有效頁面。
        4.  呼叫 `injectUECC_from_FEP`，針對當前 VB 與 FEP，在選定的中間頁面索引處注入 UECC 錯誤。
        5.  執行 **HW_RESET without SSU** (透過 `SPOR_init_mp`)。
        6.  韌體恢復後，讀取 Open VB 資訊記錄為 `open_vb_after` (Table 6)。
        7.  比較 `open_vb_current` 與 `open_vb_after` 的 VB 號碼與 FEP。
    -   **預期結果**：
        -   `SPOR_init_mp()` 必須返回 `True`。
        -   `open_vb_current.LOG_block_VB_number_logical` **不等於** `open_vb_after.LOG_block_VB_number_logical` **或者** `open_vb_current.LOG_Block_First_free_physical_page` **不等於** `open_vb_after.LOG_Block_First_free_physical_page`。
        -   這代表韌體不僅能處理末尾頁面的 UECC，也能正確處理中間頁面的 UECC 並觸發 Log 列表刷新機制。