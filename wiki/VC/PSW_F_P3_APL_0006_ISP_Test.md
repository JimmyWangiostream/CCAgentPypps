# Test Spec: ISP1/ISP2/TEMP ISP UECC Injection & SPOR Recovery Logic Verification

## Verification Criterion (VC)
驗證韌體在無 SSU (Secure Storage Unit) 保護下的 HW_RESET 情境中，對 ISP1、ISP2 及 TEMP ISP 區塊的 UECC 錯誤處理機制與狀態恢復邏輯：
1. **ISP1/ISP2 互換與修復機制**：確認當 ISP1 或 ISP2 單一區塊發生 UECC 時，韌體在 SPOR 後會觸發備援區塊互換（ISP1 變為原 ISP2，ISP2 變為原 ISP1），且 TEMP ISP 邏輯 VB 號碼保持不變；若 ISP1 與 ISP2 同時發生 UECC，則系統應進入 Assert 狀態（Stuck），無法完成啟動。
2. **TEMP ISP 錯誤處理**：確認 TEMP ISP 區塊發生 UECC 時，韌體不會觸發互換機制，而是直接修復該 TEMP ISP 區塊，使其邏輯 VB 號碼發生跳變（指向新的備援區塊），而 ISP1/ISP2 的狀態保持不變。

## Test Case (TC) Checkpoints

1. [Case01_Baseline_Initial_State_Check]：
   - 動作：透過 Vendor Command (VU 0x4097) 讀取初始狀態下的 ISP1 PCA (Physical Cell Address) 資訊、ISP2 PCA 資訊以及 TEMP ISP 的邏輯 VB 號碼。
   - 預期結果：成功獲取 ISP1、ISP2 的 PCA 結構（包含 b10_block_l, b6_plane, b5_ce, b11_block_h）及 TEMP ISP VB 號碼，作為後續比對的基準值 (Table 1)。

2. [Case02_No_Error_SPOR_Stability_Check]：
   - 動作：執行 `HW_RESET` 且 `powerdown = False` (無 SSU 硬體重啟)。重啟後再次透過 VU 0x4097 讀取 ISP1 PCA、ISP2 PCA 及 TEMP ISP VB 號碼。
   - 預期結果：ISP1 PCA 必須與 Case01 完全一致；ISP2 PCA 必須與 Case01 完全一致；TEMP ISP VB 號碼必須與 Case01 完全一致。證明無錯誤注入時，SPOR 不會改變區塊映射。

3. [Case03_ISP1_UECC_Single_Failure_Check]：
   - 動作：
     1. 針對 Case01 取得的 ISP1 PCA 執行 `inject_UECC` 注入不可修復的 UECC 錯誤。
     2. 執行 `HW_RESET` (無 SSU)。
     3. 讀取重啟後的 ISP1 PCA、ISP2 PCA 及 TEMP ISP VB 號碼。
   - 預期結果：
     - **ISP1 PCA**：必須等於 Case01 中的 **ISP2 PCA** (證明 ISP1 與 ISP2 內容互換，原 ISP2 成為新的 ISP1)。
     - **ISP2 PCA**：必須不等於 Case01 中的 ISP1 或 ISP2 PCA (證明原 ISP1 因 UECC 被標記為 Bad 或移除，新 ISP2 來自其他備援區塊)。
     - **TEMP ISP VB**：必須與 Case01 完全一致 (證明 TEMP ISP 不受 ISP 互換機制影響)。

4. [Case04_ISP2_UECC_Single_Failure_Check]：
   - 動作：
     1. 針對 Case03 結束後的 ISP2 PCA 執行 `inject_UECC` 注入 UECC 錯誤。
     2. 執行 `HW_RESET` (無 SSU)。
     3. 讀取重啟後的 ISP1 PCA、ISP2 PCA 及 TEMP ISP VB 號碼。
   - 預期結果：
     - **ISP1 PCA**：必須等於 Case03 結束後的 ISP1 PCA (證明 ISP1 狀態穩定，未受 ISP2 錯誤影響)。
     - **ISP2 PCA**：必須發生改變 (不等於 Case03 結束後的 ISP2 PCA)，證明原 ISP2 因 UECC 被替換。
     - **TEMP ISP VB**：必須與 Case01 完全一致 (保持不變)。

5. [Case05_TEMP_ISP_UECC_Recovery_Check]：
   - 動作：
     1. 獲取當前 TEMP ISP 的邏輯 VB 號碼。
     2. 根據 `flash_setting` 中的 `Max_Fdevice` (CE) 與 `Plane_Per_Die` (Plane)，遍歷尋找一個非 ICS Bad Block 的有效 Plane。
     3. 針對該 TEMP ISP 的有效 Plane 執行 `inject_UECC`。
     4. 執行 `HW_RESET` (無 SSU)。
     5. 讀取重啟後的 ISP1 PCA、ISP2 PCA 及 TEMP ISP VB 號碼。
   - 預期結果：
     - **ISP1 PCA**：必須與 Case04 結束後的 ISP1 PCA 一致。
     - **ISP2 PCA**：必須與 Case04 結束後的 ISP2 PCA 一致。
     - **TEMP ISP VB**：必須發生改變 (不等於注入前的 TEMP ISP VB)，證明韌體檢測到 TEMP ISP UECC 後，觸發了 TEMP ISP 區塊的修復/重建機制，指向了新的備援 VB。

6. [Case06_Dual_ISP_UECC_Assert_Check]：
   - 動作：
     1. 針對當前 ISP1 PCA 執行 `inject_UECC`。
     2. 針對當前 ISP2 PCA 執行 `inject_UECC`。
     3. 執行 `HW_RESET` (無 SSU)。
     4. 檢查系統啟動狀態 (透過 `SPOR_init_mp` 返回值)。
   - 預期結果：系統啟動失敗，`SPOR_init_mp` 返回 `False` (或觸發 Assert)，證明當 ISP1 與 ISP2 同時失效時，韌體無備援機制可恢復，系統進入死鎖/Assert 狀態以保護數據完整性。