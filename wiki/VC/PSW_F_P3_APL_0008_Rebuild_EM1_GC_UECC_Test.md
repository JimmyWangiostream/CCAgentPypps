# Test Spec: EM1 SLC VB GC Triggered UECC Injection & HW_RESET Without SSU Stability Test

## Verification Criterion (VC)
驗證在 EM1 (Enhanced 1) LUN 觸發 SLC 模式 GC 後，針對該 GC Target VB 的特定物理頁面注入 UECC (Uncorrectable ECC) 錯誤，並執行無 SSU (Secure Storage Unit) 保護的 HW_RESET。驗證韌體在恢復後：1) LWP (Logical Write Pointer) 狀態發生預期變更（證明 GC 流程中斷或狀態重置）；2) 該 VB 仍保留在 GC Target 或 Used Pool 中（證明錯誤未導致 VB 被標記為 Bad 或移除）；3) 數據完整性在後續讀取中符合預期（證明 UECC 錯誤在特定讀取路徑下被正確處理或隔離，未導致系統崩潰）。

## Test Case (TC) Checkpoints
1. [EM1_GC_Trigger_and_UECC_Injection]：
   - 動作：
     1. 配置 LUN 3 (EM1) 為測試目標，禁用所有前/後台操作 (`issue_D0FD`)。
     2. 對 LUN 3 執行連續寫入，直到 `USED_BLK_POOL_EM1` 的使用量達到 SLC GC 閾值 (`slc_threshold`)。
     3. 透過 `issue_40C1` 獲取當前 EM1 GC 目標 VB 號碼 (`open_logical_VB_number_for_EM1_GC`)。
     4. 收集該 VB 在各 Plane 上的 LWP (Logical Write Pointer) 資訊 (`collect_lwp_checks`)。
     5. 針對每個 Plane 的 CE0，在當前 LWP 頁面 (`lwp_gc[i].LWP`) 及前一頁面 (`lwp_gc[i].LWP - 1`) 注入 UECC 錯誤 (`inject_UECC`)。
   - 預期結果：寫入操作成功觸發 GC 機制；UECC 錯誤已成功注入至 EM1 GC Target VB 的特定物理頁面中，且 VB 號碼被正確記錄。

2. [HW_Reset_Without_SSU_LWP_Verification]：
   - 動作：
     1. 在注入 UECC 後，記錄當前各 Plane 的 LWP 狀態為 `LWP_A`。
     2. 執行 `HW_RESET` 且 `powerdown=False` (無 SSU 電源循環)。
     3. 韌體恢復後，再次獲取 EM1 GC Target VB 的 LWP 狀態為 `LWP_B`。
     4. 比較 `LWP_A` 與 `LWP_B`。
   - 預期結果：`LWP_A` 與 `LWP_B` 必須不同 (`identical == False`)。這證明在無 SSU 保護的硬體重啟後，韌體未能維持原有的 LWP 狀態，或者 GC 流程中的 LWP 標記發生了重置/變更，這是驗證韌體在異常狀態下行為一致性的關鍵指標。

3. [GC_Target_VB_Pool_Validation]：
   - 動作：
     1. 透過 `issue_406D` 獲取所有 VB 分組資訊 (`get_sorted_VB_group_from_VU_406D`)。
     2. 檢查注入 UECC 的 GC Target VB 號碼是否存在於以下群組之一：
        - Group 14: `USED_SLC` (Used SLC VB)
        - Group 8: `SLC_GC_TARGET` (SLC GC Target)
        - Group 24: `EM1_FREE_POOL` (EM1 Free Pool)
   - 預期結果：該 VB 必須位於 Group 14、8 或 24 中。若 VB 出現在其他群組，則測試失敗。這驗證了即使存在 UECC 錯誤，韌體也未將該 VB 錯誤地標記為 Bad Block 或從 GC 目標列表中移除，確保了 GC 邏輯的穩定性。

4. [Data_Integrity_Check_Post_Reset]：
   - 動作：
     1. 重新啟用前/後台操作 (`issue_D0FD` enable)。
     2. 對測試 LUN 執行讀取並與寫入記錄 (`write_record`) 進行硬體比較 (`read_compare` with `HW_COMPARE`)。
   - 預期結果：讀取比較結果必須通過。這表明儘管注入了 UECC 錯誤，但在特定的讀取路徑或韌體處理邏輯下，數據恢復或錯誤掩蔽機制生效，或者注入的錯誤頁面未被當前驗證路徑直接讀取導致數據一致性檢查失敗。