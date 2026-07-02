# Test Spec: UFS List VB UECC Injection & SPOR Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 List VB (Version Block) 遭受不同層級 UECC (Uncorrectable Error Correction Code) 錯誤注入後，執行無 SSU (Secure Storage Unit) 保護的 HW_RESET (Hard Reset) 時的恢復機制與數據一致性：
1.  **基礎狀態驗證**：確認在無錯誤注入情況下，HW_RESET 後 List VB 的邏輯區塊號碼 (VB Number) 與物理頁面指標 (FEP) 保持不變，證明韌體基礎路徑正常。
2.  **Mirror Page 恢復驗證**：針對 List VB 的 Mirror Page LWP (Logical Write Page) 注入 UECC，驗證 HW_RESET 後韌體能否透過備份資料修復 List，導致 VB Number 與 FEP 發生預期內的跳變（Refresh），證明 Mirror 機制生效。
3.  **Major Page 恢復驗證**：針對 List VB 的 Major Page LWP-2 注入 UECC，驗證 HW_RESET 後韌體能否修復 List，導致 VB Number 與 FEP 發生預期內的跳變，證明 Major 資料修復機制生效。
4.  **深度損壞邊界驗證 (VC10)**：在 List VB 跨越多個 Super Page 的情境下，逐步增加 LWP 的 UECC 注入數量（從 LWP 0 到 LWP-3），驗證韌體的恢復極限。預期在注入 LWP 0~2 時 SPOR (Start of Power On Reset) 成功且 List 刷新；當注入範圍擴大至 LWP 0~3 (case_10=3) 時，預期韌體無法恢復，導致 SPOR 失敗並觸發 Assert 或進入 MP (Manufacturing Program) 模式，驗證韌體的錯誤邊界保護機制。

## Test Case (TC) Checkpoints

1.  [Case01_Baseline_NoError_Check]：
    -   動作：透過 Vendor Command 0x40C1 讀取 Open VB Information，解析出初始的 `List_Block_VB_number_logical` 與 `List_block_First_free_physical_page` (FEP)，並計算對應的 PCA (Physical Channel Address) 資訊（包含 b10_block_l, b11_block_h, b5_ce, b6_plane, l12_fpage）。接著執行 `api.init_tester_to_unit_ready` 進行 HW_RESET (無 SSU)。重置後再次讀取 Open VB Information 並計算新的 PCA。
    -   預期結果：比較重置前後的 PCA 資訊，所有欄位 (`b10_block_l`, `b6_plane`, `b5_ce`, `b11_block_h`, `l12_fpage`) 必須完全一致。VB Number 與 FEP 數值不變，證明無錯誤注入時 HW_RESET 不改變 List 狀態。

2.  [Case02_Mirror_LWP_UECC_Recovery_Check]：
    -   動作：記錄當前 VB Number 與 FEP。在 List VB 的 Mirror Page LWP 區域注入 UECC 錯誤（根據循環變數 `t` 調整 `startoffset` 與 `num`，分別測試 LWP 0 的 offset 0/1 及 LWP 1 的 offset 0）。注入後執行 HW_RESET (無 SSU)。重置後讀取 Open VB Information，獲取新的 VB Number 與 FEP。
    -   預期結果：新的 VB Number 與 FEP 必須與注入前**不同** (`compare_vb_fep` 返回 False)。這代表韌體檢測到 Mirror Page 的 UECC 錯誤後，成功從備份或重建機制中恢復了 List 結構，導致邏輯區塊映射發生跳變 (Refresh)。

3.  [Case03_Major_LWP2_UECC_Recovery_Check]：
    -   動作：記錄當前 VB Number 與 FEP。在 List VB 的 Major Page LWP-2 區域注入 UECC 錯誤（根據循環變數 `t` 調整 `startoffset` 為 2 或 3，`num` 為 1 或 2）。注入後執行 HW_RESET (無 SSU)。重置後讀取 Open VB Information，獲取新的 VB Number 與 FEP。
    -   預期結果：新的 VB Number 與 FEP 必須與注入前**不同**。這代表韌體檢測到 Major Page 的 UECC 錯誤後，成功觸發了 List 重建流程，驗證了 Major 資料的容錯與恢復能力。

4.  [Case04_Deep_Corruption_SPOR_Fail_Check]：
    -   動作：首先透過大量 Sequential Write 將 List VB 擴展至超過 2 個 Super Page (`List_block_First_free_physical_page.value >= ce_plane_num * 2`)。接著進入循環 `case_10` (0 到 3)：
        -   當 `case_10` < 3 時：注入 UECC 覆蓋 LWP 0 到 LWP-`case_10`+4 (例如 LWP 0~3)。執行 HW_RESET 並檢查 `SPOR_init_mp()` 狀態。
        -   當 `case_10` == 3 時：注入 UECC 覆蓋 LWP 0 到 LWP-7 (即 `num`=7)。執行 HW_RESET 並檢查 `SPOR_init_mp()` 狀態。
    -   預期結果：
        -   對於 `case_10` 0, 1, 2：`SPOR_init_mp()` 必須返回 `True` (表示 SPOR 成功進入正常運作模式)，且重置後的 VB Number 與 FEP 必須與注入前**不同** (List 已刷新)。
        -   對於 `case_10` == 3：`SPOR_init_mp()` 必須返回 `False` (表示 SPOR 失敗，韌體進入 MP 模式或觸發 Assert)。這驗證了當 List VB 的損壞範圍超過韌體可修復的閾值時，系統會拒絕啟動並進入安全模式，防止數據進一步損壞。