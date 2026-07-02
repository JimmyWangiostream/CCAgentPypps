# Test Spec: UFS Vendor Command Read Retry & Sticky Read Verification

## Verification Criterion (VC)
驗證 UFS 韌體在啟用 Sticky Read 機制下的 Read Retry (REH) 行為與錯誤計數一致性：
1. **Sticky Read 強制鎖定驗證**：確認透過 Vendor Command `0x4066` 將當前 Read Last Table 強制設為 Sticky Read 後，後續的 Read Retry 流程會優先使用該 Sticky 設定，並正確反映在 `0x40BB` 的回傳狀態中（Read Last Result 與 Re-Read Result 的互斥與數值邏輯）。
2. **REH 步驟與錯誤位元數一致性**：驗證在不同 REH 步驟（Big/Small Index）下，透過 `0x40BB` 讀取的錯誤位元數（Error Bits）與透過 `0x409E` 讀取的原始錯誤位元數必須完全一致，確保韌體內部錯誤統計機制無偏差。
3. **Read Last 與 Re-Read 狀態切換邏輯**：驗證在 LUN0 (TLC) 與 LUN1 (SLC) 的不同區塊類型下，當 REH 步驟改變時，`0x40BB` 中 `readLastResult` 與 `reReadResult` 的數值（0 或 1）及對應的 `errorBits`（特別是 0x3FFF 代表未修正或特定狀態）是否符合硬體預期的狀態機轉換。

## Test Case (TC) Checkpoints

1. [Case01_LUN0_TLC_Sticky_Read_Initial_Check]：
   - 動作：配置 LUN0 為 Normal (TLC)，寫入 TLC VB 大小資料。隨機選取 LBA 並轉換為 PBA。透過 `issue_4066_force_current_read_last_as_sticky_read` 將當前 Read Last Table 強制設為 Sticky Read。接著啟用 Sticky Read 功能 (`issue_4066_to_dis_en_sticky_read`)。執行 REH 步驟 Big=0, Small=0 的 `issue_D014_to_set_read_recovery_module`。執行讀取操作後，透過 `issue_40BB_to_get_error_bit_numbers_and_read_retry_step` 讀取狀態。
   - 預期結果：`output_40BB.reReadResult.value` 必須等於 0；`output_40BB.reReadErrorBits.value` 必須不等於 0x3FFF；`output_40BB.reReadBigStep.value` 與 `reReadSmallStep.value` 必須分別等於 0 和 0；同時 `output_40BB.readLastResult.value` 必須等於 1；`output_40BB.readLastErrorBits.value` 必須等於 0x3FFF。這代表 Sticky Read 機制生效，Read Last 被標記為已使用（Result=1），而 Re-Read 尚未執行或無錯誤（Result=0）。

2. [Case02_LUN0_TLC_REH_Step_1_Check]：
   - 動作：保持 LUN0 的 Sticky Read 啟用狀態。執行 REH 步驟 Big=1, Small=0 的 `issue_D014_to_set_read_recovery_module`。執行讀取操作後，透過 `issue_40BB_to_get_error_bit_numbers_and_read_retry_step` 讀取狀態。
   - 預期結果：`output_40BB.readLastResult.value` 必須等於 0；`output_40BB.readLastErrorBits.value` 必須不等於 0x3FFF；`output_40BB.readLastBigStep.value` 與 `readLastSmallStep.value` 必須分別等於 1 和 0；同時 `output_40BB.reReadResult.value` 必須等於 1；`output_40BB.reReadErrorBits.value` 必須等於 0x3FFF。這代表韌體在 Sticky Read 啟用下，嘗試了新的 Read Last 步驟（Big=1），而 Re-Read 狀態被標記為已觸發但錯誤位元為 0x3FFF（可能代表未修正或特定硬體狀態）。

3. [Case03_LUN0_TLC_REH_Step_2_Plus_Check]：
   - 動作：保持 LUN0 的 Sticky Read 啟用狀態。執行 REH 步驟 Big>=2 的 `issue_D014_to_set_read_recovery_module`。執行讀取操作後，透過 `issue_40BB_to_get_error_bit_numbers_and_read_retry_step` 讀取狀態。
   - 預期結果：`output_40BB.readLastResult.value` 必須等於 1；`output_40BB.readLastErrorBits.value` 必須等於 0x3FFF；`output_40BB.reReadResult.value` 必須等於 1；`output_40BB.reReadErrorBits.value` 必須等於 0x3FFF。這代表在較深的 REH 步驟下，Read Last 與 Re-Read 均處於特定狀態（Result=1），且錯誤位元均為 0x3FFF，驗證韌體在深層 REH 下的狀態機行為。

4. [Case04_Error_Bit_Consistency_409E_vs_40BB]：
   - 動作：針對 LUN0 與 LUN1，在執行完 REH 步驟後，透過 `issue_4060_to_read_raw_data` 讀取原始資料。接著分別透過 `issue_409E_to_get_error_bit_numbers` (參數 ECC info=1) 與 `issue_40BB_to_get_error_bit_numbers_and_read_retry_step` 獲取錯誤位元數。提取 `0x409E` 回傳的 `errorBitNumber1~4` 與 `0x40BB` 回傳的 `errorBitNumber1~4`。
   - 預期結果：`0x409E` 回傳的四個錯誤位元數值陣列必須與 `0x40BB` 回傳的四個錯誤位元數值陣列完全相等。若不相等，則觸發 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`。此步驟驗證韌體內部錯誤計數器在 Raw Data 讀取後，透過不同 Vendor Command 暴露給 Host 的數據一致性。

5. [Case05_LUN1_SLC_Sticky_Read_Verification]：
   - 動作：配置 LUN1 為 Enhanced 1 (SLC)，寫入 SLC VB 大小資料。隨機選取 LBA 並轉換為 PBA。重複 Case01 至 Case03 的 Sticky Read 強制設定、啟用、以及不同 REH 步驟 (Big=0, Big=1, Big>=2) 的讀取與 `0x40BB` 狀態檢查流程。
   - 預期結果：LUN1 (SLC) 的 `0x40BB` 狀態變化邏輯應與 LUN0 (TLC) 保持一致的硬體行為模式（即 Sticky Read 啟用下的 Result 與 Error Bits 互斥與數值邏輯），確保 SLC 模式下的 Read Retry 機制同樣受 Sticky Read 正確控制。