# Test Spec: UFS FTL GC Triggered UECC Persistence Check (No SSU Recovery)

## Verification Criterion (VC)
驗證在觸發 TLC GC 並寫入新資料後，針對特定 LWP (Logical Write Pointer) 頁面注入 UECC (Uncorrectable ECC) 錯誤，執行 **無 SSU (Secure Storage Unit) 的 HW_RESET** 後，韌體是否會錯誤地保留或恢復該錯誤狀態，以及 GC Target VB 的歸屬群組是否正確。
核心驗證點：
1.  **LWP 狀態變更驗證**：確認在寫入觸發 GC 後，LWP 指標已移動（LWP_A != LWP_B），證明寫入操作生效。
2.  **錯誤注入與持久化檢查**：在 GC 觸發後的特定頁面注入 UECC，執行 HW_RESET（無電源循環/無 SSU 重建流程），檢查韌體是否因缺乏 SSU 保護而導致錯誤狀態殘留或邏輯異常。
3.  **GC Target VB 狀態驗證**：確認發生錯誤的 VB 在 Reset 後仍處於 `Used VB` (Group 15)、`GC Target` (Group 9) 或 `Free Pool` (Group 25) 的合法狀態，若出現在其他群組則視為 FTL 邏輯損壞。

## Test Case (TC) Checkpoints

1.  **[TC01_Precondition_GC_Trigger_LWP_Movement]**：
    -   動作：
        1.  初始化 LUN 配置，將 LUN 0 設為 Normal (TLC) 類型，LUN 3 設為 EM1 類型，並禁用所有 Foreground/Background 操作。
        2.  針對 LUN 0 持續寫入資料，直到 `used_vb_cnt` 達到 TLC GC 閾值 (`tlc_threshold`)，強制觸發 GC 流程。
        3.  獲取當前 Normal Defrag GC Open VB 的 VB 號碼 (`vb`)。
        4.  收集該 VB 在各 Plane 上的當前 LWP 狀態，記錄為 `LWP_A`。
        5.  執行 `api.init_tester_to_unit_ready` 進行 **HW_RESET** (ResetType: HW_RESET, Powerdown: False)，**不執行** SSU 電源循環。
        6.  Reset 完成後，再次收集同一 VB 的 LWP 狀態，記錄為 `LWP_B`。
        7.  比對 `LWP_A` 與 `LWP_B`。
    -   預期結果：
        -   `LWP_A` 與 `LWP_B` **必須不相等** (`identical == False`)。
        -   這證明在寫入觸發 GC 的過程中，LWP 指標已經發生移動，系統處於正常的寫入/GC 狀態，而非死鎖或靜止狀態。若相等，則測試失敗 (`SIGHTING_FAIL_DATA_COMPARE_FAIL`)。

2.  **[TC02_UECC_Injection_And_NoSSU_Reset_Check]**：
    -   動作：
        1.  在觸發 GC 後的 VB (`vb`) 中，針對 CE0 的每個 Plane (`i`)，計算對應的 LWP 頁面 (`lwp_gc[i].LWP`)。
        2.  計算該頁面的 Page Order，並透過 `inject_UECC(uecc_pca)` 函數，在該物理頁面的 Payload 中注入 **UECC 錯誤** (Uncorrectable ECC)。
        3.  執行 **HW_RESET** (ResetType: HW_RESET, Powerdown: False)，**明確不觸發 SSU** (Secure Storage Unit) 的完整電源循環與韌體重建流程。
        4.  Reset 完成後，獲取 VB 列表資訊 (`get_sorted_VB_group_from_VU_406D`)。
        5.  檢查發生錯誤注入的 VB (`vb`) 目前所在的 VB 群組索引 (`errgroup`)。
    -   預期結果：
        -   VB (`vb`) 必須位於以下三個合法群組之一：
            -   **Group 15**: `Used VB` (已使用區塊)
            -   **Group 9**: `TLC GC Target` (GC 目標區塊)
            -   **Group 25**: `TLC Free Pool` (TLC 空閒池)
        -   若 VB 出現在其他群組（例如 Group 0-14, 16-24 等），則判定為 FTL 邏輯狀態異常，測試失敗 (`SIGHTING_FAIL_DATA_COMPARE_FAIL`)。
        -   此步驟驗證在無 SSU 保護下，系統對 GC 過程中發生 UECC 的 VB 狀態管理是否符合預期（通常應保留在 Used/GC Target 中等待後續處理，而非錯誤地標記為 Free 或 Invalid）。

3.  **[TC03_Data_Integrity_Post_Reset]**：
    -   動作：
        1.  在 TC02 完成 HW_RESET 後，重新啟用 Foreground 和 Background 操作。
        2.  對之前寫入的 `write_record` 中的資料進行 **Read-Back 並與 HW Compare** (`read_compare`)。
    -   預期結果：
        -   資料比對必須通過。
        -   這確認雖然注入了 UECC 錯誤，但該錯誤並未導致整個 LUN 或關鍵系統資料的不可恢復損壞，且韌體在 Reset 後能正常恢復讀寫功能。