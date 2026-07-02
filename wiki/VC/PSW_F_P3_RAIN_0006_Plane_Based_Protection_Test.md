# Test Spec: UFS PTE Parity Integrity & UECC Refresh Stagnation Test

## Verification Criterion (VC)
驗證 PTE (Page Table Entry) 資料在經過完整 SSU (Start/Stop Unit) 電源循環後，其多 CE/Plane 結構下的 Parity 一致性；並確認在注入 UECC (Uncorrectable ECC) 錯誤後，透過 Vendor Command (C088) 強制停止 Refresh 機制，導致韌體無法自動修復該錯誤，最終在讀取比較階段因 Parity 不匹配或資料損毀而觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。此測試旨在確保韌體在 Refresh 被禁用時，UECC 錯誤不會被隱性修復，從而暴露潛在的資料完整性風險。

## Test Case (TC) Checkpoints

1. [PTE_Data_Creation_and_SSU_Flush_Check]：
   - 動作：針對 `TestNormalLun` 寫入超過 2 頁的資料以建立 PTE 數據，隨後發送兩組 `StartStopUnit` 命令：第一組 `power_condition=0x02` (Active/Idle) 且 `start=0` 以停止單元，第二組 `power_condition=0x01` (Active) 且 `start=0` 以確保資料刷出 (Flush)，最後執行 `HW_RESET` 且 `powerdown=False` 進行硬體重啟。
   - 預期結果：PTE 數據成功寫入 Flash，SSU 流程確保 PTE 狀態同步至非揮發性儲存，HW_RESET 後系統恢復至 Unit Ready 狀態，為後續驗證提供穩定的硬體基線。

2. [PTE_Parity_Integrity_Verification_Check]：
   - 動作：在重啟後，針對 PTE 所在的 VB (Virtual Block) 執行 Direct Read，遍歷所有有效的 CE (Chip Enable) 和 Plane，讀取該 Pageline 的所有 Page 資料。手動計算前 N-1 個 Page 資料前 8 位元組的 XOR 值 (`parity_manual`)，並與最後一個 Page 的前 8 位元組 (`raw_parity`) 進行比對。
   - 預期結果：`parity_manual` 必須嚴格等於 `raw_parity`。這驗證了 PTE 資料在 Flash 中的 Parity 機制運作正常，且 Direct Read 路徑能正確讀取原始資料，無傳輸或解碼錯誤。

3. [UECC_Inject_and_Refresh_Stop_Check]：
   - 動作：將 Phison PCA 轉換為 Micron PCA 格式，針對 PTE 所在的 Block 注入 UECC 錯誤 (`inject_UECC`)，並啟用 SLC 模式。隨後再次執行 `HW_RESET`，並立即發送 Vendor Command `C088`，參數設定為 `StopRefreshRefreshCanStillBeEnqueue`，強制停止韌體的背景 Refresh 機制。
   - 預期結果：UECC 錯誤成功注入至 PTE 資料中，導致該區塊資料處於不可糾正狀態。Vendor Command C088 成功執行，韌體後台的 ECC 修復/Refresh 流程被暫停，確保注入的錯誤不會被自動修正。

4. [Stagnant_UECC_Data_Comparison_Check]：
   - 動作：在 Refresh 停止的狀態下，執行 `read_compare_rain_result` 對之前寫入的 `write_record` 進行讀取與資料比對。同時發送 Vendor Command `40C5` 檢查 UECC Refresh Booking Queue 的狀態。
   - 預期結果：由於 Refresh 機制被停止且存在未修復的 UECC 錯誤，讀取回來的資料應與原始寫入資料不一致，或 Parity 檢查失敗。測試腳本預期觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，證明在 Refresh 禁用情境下，UECC 錯誤確實導致了資料驗證失敗，而非被韌體隱性修復。