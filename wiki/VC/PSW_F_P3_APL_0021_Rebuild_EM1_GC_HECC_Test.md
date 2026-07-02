# Test Spec: EM1 SLC VB UECC Injection & HW_RESET Recovery Verification

## Verification Criterion (VC)
驗證在 EM1 (Enhanced 1) LUN 配置為 SLC 模式並觸發 GC 閾值後，針對特定 CE/Plane 的 LWP 頁面注入 UECC (Uncorrectable ECC) 錯誤，執行無 SSU (Secure Storage Unit) 保護的 HW_RESET 後，韌體是否正確保留錯誤標記且 VB 狀態未發生異常重建。具體驗證點包括：1. LWP (Last Written Page) 在重置前後必須保持一致，證明韌體未嘗試自動修復或重建該 VB；2. 該 VB 必須仍處於 "Used SLC" 或 "GC Target" 狀態，證明其未被錯誤地標記為 Normal 或移除；3. 資料完整性通過 HW_COMPARE 確認寫入資料與讀回資料一致（儘管存在 UECC，但韌體層面可能透過 Read Retry 或特定機制恢復資料，或測試重點在於 LWP 狀態機而非資料內容的比特級正確性，此處重點在於 LWP 狀態碼的穩定性）。

## Test Case (TC) Checkpoints
1. [EM1_SLC_UECC_Injection_HW_Reset_LWP_Check]：
   - 動作：
     1. 配置 LUN 3 (TestEM1Lun) 為 Enhanced 1 類型，並透過 `issue_D0FD` 禁用所有前/背景操作。
     2. 呼叫 `write_until_threshold` 對 LUN 3 進行隨機寫入，直到 `USED_BLK_POOL_EM1` 中的 VB 數量達到設定閾值 `set_slc_threshold` (預設 20)，強制觸發 GC 機制並建立 SLC 模式的 Open VB。
     3. 透過 `issue_40C1` 獲取當前 Open VB 的邏輯 VB 號碼 (`vb`)。
     4. 呼叫 `collect_lwp_checks` 獲取重置前各 Plane 的 LWP 狀態 (`lwpA`)。
     5. 針對每個 Plane (`i` from 0 to Plane_Per_Die-1)，建構 PCA 結構體，指定 Die 0, CE 0, Plane `i`，並計算對應的 Page 位置 (`lwp_gc[i].LWP << 5`)。
     6. 呼叫 `inject_UECC(uecc_pca)` 在該 Page 注入 UECC 錯誤。
     7. 再次呼叫 `collect_lwp_checks` 獲取注入後的 LWP 狀態 (`lwpA`，此處代碼邏輯中變數名重複使用，實際應為注入後讀取或保持不變的參考值，代碼中 `lwpA` 在注入後未重新賦值，但後續比較的是 `lwpA` 與 `lwpB`)。*註：根據代碼邏輯，`lwpA` 是在注入前獲取，注入後直接進行 HW_RESET。*
     8. 呼叫 `api.init_tester_to_unit_ready` 執行 `HW_RESET`，且 `powerdown=False` (無 SSU 電源循環)。
     9. 重置後，再次呼叫 `issue_40C1` 獲取 Open VB 資訊，並呼叫 `collect_lwp_checks` 獲取重置後的 LWP 狀態 (`lwpB`)。
     10. 呼叫 `compare_lwp_checks(lwpA, lwpB)` 比對重置前後的 LWP 狀態。
     11. 呼叫 `get_sorted_VB_group_from_VU_406D()` 獲取 VB 分組資訊，檢查該 `vb` 是否位於 Group 14 (Used SLC) 或 Group 8 (SLC GC Target)。
     12. 執行 `read_compare` 使用 `HW_COMPARE` 驗證資料一致性。
   - 預期結果：
     1. `compare_lwp_checks` 返回 `identical=True`，表示 `lwpA` 與 `lwpB` 完全相同，證明在無 SSU 的 HW_RESET 下，UECC 錯誤導致 LWP 狀態被鎖定或保留，未發生重建導致 LWP 跳變。
     2. 該 `vb` 必須存在於 `sorted_vb_list_from_VU[14]` (Used SLC) 或 `sorted_vb_list_from_VU[8]` (SLC GC Target) 中。若不在這些群組，則測試失敗 (`SIGHTING_FAIL_DATA_COMPARE_FAIL`)，證明韌體未將此有錯誤的 VB 標記為 Normal 或進行其他異常狀態遷移。
     3. `read_compare` 成功，確認資料讀寫流程在韌體層面未因 UECC 注入而導致 Host 層面的資料錯誤（或韌體已透過內部機制處理，但測試重點在於 LWP 狀態碼的穩定性）。