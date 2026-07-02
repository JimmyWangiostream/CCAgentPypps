# Test Spec: UFS PT (Physical Table) Integrity & Recovery Mechanism Verification

## Verification Criterion (VC)
驗證 UFS 韌體在硬體重置（HW_RESET）且無安全儲存單元（SSU）保護的情境下，對物理表（PT）區塊的錯誤處理與恢復機制：
1.  **VC1 (Baseline Stability)**：確認在無錯誤注入下，HW_RESET 後 PT 區塊的 PCA（Physical Cell Address）資訊（CE, Plane, FEP）保持不變，證明韌體能正確讀取並維持 PT 結構。
2.  **VC2 (Major Page UECC Handling)**：確認當 PT 的 Major Page（FEP-2）發生 UECC 錯誤時，HW_RESET 後韌體無法自動修復，導致 PT 區塊映射發生改變（PCA 變化），代表韌體在無備援或修復機制下，錯誤的 PT 導致區塊重新分配或標記失效。
3.  **VC3 (Mirror Page UECC Handling)**：確認當 PT 的 Mirror Page（FEP-1）發生 UECC 錯誤時，HW_RESET 後韌體同樣無法自動修復，導致 PT 區塊映射發生改變（PCA 變化），驗證 Mirror 頁面的錯誤同樣會觸發 PT 結構的不穩定或重映射。
4.  **VC4-VC7 (Critical Sector Corruption & Assert Trigger)**：確認當 PT 的關鍵頁面（Page 0, Page 1, 或 Page 2 及以下）被注入 UECC 錯誤後，HW_RESET 會觸發韌體 Assert 機制（Assert Number 0x5027）並導致初始化失敗（Init Fail）。此驗證確保韌體在檢測到不可恢復的 PT 結構損壞時，能正確進入錯誤狀態而非錯誤地繼續運行，防止數據進一步損毀。

## Test Case (TC) Checkpoints

1.  **[Case01_Baseline_PT_Stability_Check]**：
    -   動作：透過 Vendor Command 0x40C6 讀取當前 PT 區塊的物理資訊（CE, Plane, FEP），建構 PCA 並直接讀取該 LWP 的 4KB Payload 存檔。接著執行 `HW_RESET`（無 SSU 電源循環）。重置後再次讀取 PT 區塊資訊，建構新 PCA 並讀取 Payload。比對重置前後的 PT PCA 資訊。
    -   預期結果：重置後的 PT PCA（CE, Plane, FEP）必須與重置前完全一致；Payload 內容應保持穩定。證明在無錯誤情境下，PT 區塊在 SPOR 後結構保持不變。

2.  **[Case02_MajorPage_UECC_PCA_Change_Check]**：
    -   動作：獲取當前 PT 區塊資訊，計算 Major Page 的 FEP 索引（`FEP - 2`），建構對應 PCA 並注入 UECC 錯誤。執行 `HW_RESET`（無 SSU）。重置後讀取 PT 區塊資訊，建構 PCA 並讀取 Payload。比對注入錯誤前（Table2）與重置後（Table3）的 PT PCA 資訊。
    -   預期結果：重置後的 PT PCA 必須與注入錯誤前**不同**（`compare_pb_fep` 返回 False）。證明 Major Page 的 UECC 錯誤導致韌體在啟動時無法正確識別原有 PT 區塊，進而觸發區塊重新分配或標記為異常，PCA 發生跳變。

3.  **[Case03_MirrorPage_UECC_PCA_Change_Check]**：
    -   動作：獲取當前 PT 區塊資訊，計算 Mirror Page 的 FEP 索引（`FEP - 1`），建構對應 PCA 並注入 UECC 錯誤。執行 `HW_RESET`（無 SSU）。重置後讀取 PT 區塊資訊，建構 PCA 並讀取 Payload。比對注入錯誤前（Table3）與重置後（Table4）的 PT PCA 資訊。
    -   預期結果：重置後的 PT PCA 必須與注入錯誤前**不同**（`compare_pb_fep` 返回 False）。證明 Mirror Page 的 UECC 錯誤同樣導致韌體無法正確識別原有 PT 區塊，PCA 發生跳變，驗證 Mirror 頁面的完整性對 PT 穩定性至關重要。

4.  **[Case04_CriticalSector_Corruption_Assert_Check]**：
    -   動作：執行 `make_index_refresh_update_PT` 四次以更新 PT 結構。針對三種情境（Case 0: Page 0, Case 1: Page 1, Case 2: Page 2 及以下）分別注入 UECC 錯誤。嘗試執行 `HW_RESET` 並捕獲異常。
        -   若為 Case 0 或 Case 1：預期 `init_tester_to_unit_ready` 拋出異常，且韌體 Assert Number 必須等於 `0x5027`。
        -   若為 Case 2：預期 `init_tester_to_unit_ready` 拋出異常（初始化失敗）。
        -   若未拋出異常或 Assert Number 不符，則測試失敗。
    -   預期結果：
        -   Case 0 & 1：必須觸發 Assert，且 `api.get_fw_assert_number()` 返回值嚴格等於 `0x5027`。
        -   Case 2：必須觸發初始化失敗異常。
        -   這證明當 PT 的核心結構頁面（Page 0/1/2）發生 UECC 時，韌體能正確檢測並進入 Assert 狀態，阻止系統在損壞的元數據上運行。