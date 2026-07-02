# Test Spec: PTE LWP UECC Injection & SSU/HW_RESET Recovery Mechanism Verification

## Verification Criterion (VC)
驗證韌體在 PTE (Parameter Table Entry) LWP (Logical Write Page) 發生不可修復錯誤 (UECC) 時，不同電源管理策略下的硬體行為與韌體恢復機制：
1.  **Case 01 (Non-SSU HW_RESET)**：確認在無 Secure Storage Unit (SSU) 保護的硬體重啟下，PTE LWP 中的 UECC 標記 (0x02020202) 會殘留，證明韌體未觸發重建或修復流程。
2.  **Case 02 (SSU HW_RESET)**：確認在有 SSU 保護的硬體重啟 (POR) 下，韌體觸發 PTE Reconstruction 機制，將 PTE LWP 狀態修復為 Normal (0x00000000)，且 PTE VB 號碼保持不變。
3.  **Case 03 (Control Group)**：確認在無錯誤注入且經過 SSU 重啟後，再執行無 SSU 重啟，PTE LWP 狀態應維持 Normal (0x00000000)，排除環境變數干擾。

## Test Case (TC) Checkpoints

1.  **[Case01_Non_SSU_UECC_Check]**：
    -   動作：
        1.  配置 LUN (Normal LUN 0, Boot A/B, EM1)，寫入 4KB 資料至 Normal LUN (LBA 0)。
        2.  透過 Vendor Command `issue_40C1_to_get_open_vb_information` 取得當前 PTE Block VB 號碼 (`vb`) 與 PTE Block First Free Physical Page (`fep`)。
        3.  呼叫 `injectUECC_from_FEP(vb, fep, startoffset=0, num=1)` 在 PTE LWP 注入 UECC 錯誤，並記錄物理地址 PCA 資訊 (`pca1`)。
        4.  執行 `api.init_tester_to_unit_ready`，設定 `resetmode=HW_RESET` 且 `powerdown=False` (無 SSU 硬體重啟)。
        5.  重啟後，再次取得 PTE VB 號碼 (`vb1`)。
        6.  使用 Vendor Command `issue_4060_to_read_raw_data` 直接讀取 PTE LWP 的原始 NAND 資料 (Die=`pca1.b5_ce`, Plane=`pca1.b6_plane`, Block=`vb1`, Page=`pca1.l12_fpage >> 5`)。
        7.  檢查讀回資料中 payload 偏移量 `0x4000` 到 `0x4004` 的 4 個位元組。
    -   預期結果：
        -   PTE VB 號碼 (`vb1`) 應與注入前 (`vb`) 相同。
        -   payload 欄位 `raw_data[0x4000:0x4004]` 必須等於 `b'\x02\x02\x02\x02'` (即數值 0x02020202)。
        -   這代表在無 SSU 保護的重啟下，韌體未執行 PTE 修復，UECC 錯誤標記殘留於 LWP 中。

2.  **[Case02_SSU_Recovery_Check]**：
    -   動作：
        1.  重置 LUN 配置，再次寫入 4KB 資料至 Normal LUN (LBA 0)。
        2.  透過 `issue_40C1_to_get_open_vb_information` 取得新的 PTE VB 號碼 (`vb`) 與 FEP (`fep`)。
        3.  呼叫 `injectUECC_from_FEP(vb, fep, startoffset=0, num=1)` 在 PTE LWP 注入 UECC 錯誤，並記錄物理地址 PCA 資訊 (`pca1`)。
        4.  執行 `api.init_tester_to_unit_ready`，設定 `resetmode=HW_RESET` 且 `powerdown=True` (觸發 SSU 完整電源循環流程)。
        5.  重啟後，取得當前 PTE VB 號碼 (`vb1`) 並與注入前比較。
        6.  使用 Vendor Command `issue_4060_to_read_raw_data` 直接讀取 PTE LWP 的原始 NAND 資料 (Die=`pca1.b5_ce`, Plane=`pca1.b6_plane`, Block=`vb1`, Page=`pca1.l12_fpage >> 5`)。
        7.  檢查讀回資料中 payload 偏移量 `0x4000` 到 `0x4004` 的 4 個位元組。
    -   預期結果：
        -   PTE VB 號碼必須維持不變 (`vb == vb1`)。
        -   payload 欄位 `raw_data[0x4000:0x4004]` 必須等於 `b'\x00\x00\x00\x00'` (即數值 0x00000000)。
        -   這代表韌體在 SSU 電源循環後觸發了 PTE Reconstruction 機制，UECC 錯誤已被自動修復，狀態恢復為 Normal。

3.  **[Case03_Control_Group_Normal_Check]**：
    -   動作：
        1.  重置 LUN 配置，寫入 4KB 資料至 Normal LUN (LBA 0)。
        2.  取得 PTE VB 號碼 (`vb`) 與 FEP (`fep`)，但**不執行** `injectUECC` 錯誤注入。
        3.  執行 `api.init_tester_to_unit_ready`，設定 `resetmode=HW_RESET` 且 `powerdown=True` (SSU 重啟)。
        4.  重啟後，取得 PTE VB 號碼 (`vb1`)。
        5.  再次寫入 4KB 資料至 Normal LUN (LBA 0)。
        6.  執行 `api.init_tester_to_unit_ready`，設定 `resetmode=HW_RESET` 且 `powerdown=False` (無 SSU 重啟)。
        7.  重啟後，取得 PTE VB 號碼 (`vb1`)。
        8.  使用 Vendor Command `issue_4060_to_read_raw_data` 讀取 PTE LWP 的原始 NAND 資料 (Die/Plane/Page 基於初始 PCA 或當前狀態，代碼中使用 `pca1` 但 Case 03 未注入，故需確保讀取的是正確的 PTE 物理位置，代碼邏輯中 `pca1` 在 Case 03 被初始化為空 PCA，此處假設測試邏輯依賴於 VB/Page 映射或代碼實際執行時會重新獲取物理地址，但根據提供的代碼片段，`pca1` 在 Case 03 為空物件，這可能是一個潛在的測試腳本缺陷，但依據 VC 驗證目標，我們關注的是**無錯誤注入**下的狀態)。*註：根據代碼邏輯，Case 03 中 `pca1 = PCA()` 為空，後續讀取 `pca1.b5_ce` 等屬性會導致錯誤。但在驗證邏輯分析中，我們假設此步驟意圖為驗證正常路徑。若嚴格遵循代碼，此步驟會因 AttributeError 失敗。然而，基於 VC 的意圖，我們描述其預期行為：*
        9.  檢查讀回資料中 payload 偏移量 `0x4000` 到 `0x4004` 的 4 個位元組。
    -   預期結果：
        -   PTE VB 號碼應保持穩定。
        -   payload 欄位 `raw_data[0x4000:0x4004]` 必須等於 `b'\x00\x00\x00\x00'` (即數值 0x00000000)。
        -   這代表在無錯誤注入且經過多次重啟的情境下，PTE LWP 狀態始終保持 Normal，作為對照組驗證測試環境的穩定性。