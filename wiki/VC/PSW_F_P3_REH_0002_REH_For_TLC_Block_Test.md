# Test Spec: UFS REH (Read Error Handling) Sticky Read & ERS Verification

## Verification Criterion (VC)
驗證 UFS 韌體在啟用 Sticky Read 機制與 NAND 溫度模擬情境下，Read Error Handling (REH) 模組的錯誤恢復步驟（Big/Small Step）設定與回報一致性，以及 Error Recovery Statistics (ERS) 計數器的遞增行為：
1. **Sticky Read 設定驗證**：確認透過 Vendor Command `0x4066` 強制將當前 Read Last Table 設為 Sticky Read 後，系統能正確接受並返回 `STICKY_READ_STATUS.SUCCESS`，排除 `FAILED` 狀態。
2. **REH 步驟設定與回報一致性**：針對 TLC Block 的不同 Page Type，透過 `0xD014` (Op0) 指定特定的 Big Index 與 Small Index 進行 ECC 恢復，隨後透過 `0x40F9` 讀取該 Die/Plane/Block/Page 的 REH 統計數據。預期回報的 Big/Small Step 必須與設定值嚴格匹配（含特定邊界條件如 Big=7/Small=0 允許 Small=1 的容錯邏輯），且 `maxErrorBits` 必須大於 0，證明該步驟確實被觸發並檢測到錯誤。
3. **ERS 計數器遞增驗證**：在執行 REH 恢復前後，透過 `0x40BA` 讀取 Error Recovery Statistics。預期針對特定 Die/Plane/Record 的 ERS 數值在恢復後必須嚴格大於恢復前的原始數值，證明韌體正確更新了錯誤恢復的統計計數器。

## Test Case (TC) Checkpoints
1. [Sticky_Read_Configuration_Check]：
   - 動作：在寫入 3倍 TLC VB Size 的資料後，建立 `read_last_ref_table`，並針對所有 Die 與 Page Type，隨機選擇 ARC 值，透過 `issue_4066_force_current_read_last_as_sticky_read` 強制設定 Sticky Read。
   - 預期結果：所有 `issue_4066` 呼叫必須返回 `STICKY_READ_STATUS.SUCCESS` (result.value != FAILED)。若返回 FAILED，則測試失敗，代表 Sticky Read 機制設定無效或硬體狀態不允許。

2. [REH_Step_Setting_and_Retrieval_Check]：
   - 動作：隨機選取 LBA 並透過 `issue_4051` 轉換為 PBA (Die, Plane, Block, Page)。針對 TLC Block 的三種 Page Type (TLC, MLC, SLC)，遍歷 `iter_reh_steps` 產生的 Big/Small Step 組合。透過 `issue_D014` (Op0) 設定 `isSpeciBlock=1` 並指定對應的 Big/Small Index 進行恢復。隨後透過 `issue_4052` 驗證 PBA 回轉 LBA 的正確性，並執行 Host Read 4KB。最後透過 `issue_40F9` 讀取該物理位置的 REH 統計數據 (`rr_number_and_error_bits`)。
   - 預期結果：
     1. `issue_4052` 回傳的 LBA 必須與原始選取的 LBA 一致。
     2. `issue_40F9` 回傳的 `bigStep` 與 `smallStep` 必須符合 `check_read_recovery_step` 的邏輯：通常需完全相等；若設定為 Big=7, Small=0，則回報 Small=0 或 1 皆視為成功；若設定 Big=9，則回報 Big=255, Small=255 視為成功。
     3. `maxErrorBits` 必須大於 0。若上述任一條件不符，觸發 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`。

3. [ERS_Increment_Verification_Check]：
   - 動作：在執行 `issue_D014` 設定 REH 步驟前，先透過 `issue_40BA` 讀取並備份當前的 Error Recovery Statistics (`bk_ers`)。在執行 REH 恢復並讀取資料後，再次透過 `issue_40BA` 讀取當前 ERS (`ers`)。針對每個被觸發的 REH Record，計算特定 Die 與 Plane 下的 ERS 數值 (`val`) 並與備份值 (`org_val`) 比較。
   - 預期結果：對於所有被觸發的 REH 步驟，計算出的 `val` 必須嚴格大於 `org_val`。若發現 `val <= org_val`，則將錯誤訊息加入 `error_ERS_Message` 列表。測試結束後，若該列表非空，則觸發 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`，代表韌體未正確更新錯誤恢復統計計數器。