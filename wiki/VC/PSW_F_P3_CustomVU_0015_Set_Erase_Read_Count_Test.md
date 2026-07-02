# Test Spec: UFS VB Erase Count (EC) Persistence & LUN Reconfig Warning Mechanism

## Verification Criterion (VC)
驗證 UFS 韌體中 VB (Version Block) Erase Count (EC) 在 SRAM 暫存與非揮發性儲存之間的行為，以及 LUN Reconfiguration 觸發的 Health Report 警告機制：
1. **SRAM 寫入與 SPOR 恢復驗證**：確認透過 Vendor Command 將隨機 EC 值寫入 SRAM 後，執行 HW_RESET 且無 SSU 保護時，SRAM 中的 EC 值應恢復為掉電前的備份值（即韌體在初始化階段從 Flash 讀取並覆蓋 SRAM，或 SRAM 內容在 Reset 期間被保留/恢復機制處理，此處測試邏輯顯示 Reset 後 SRAM 值等於 Backup，暗示韌體在 Boot 階段從 Flash 讀取 EC 寫入 SRAM，或者該測試旨在驗證 Flash 中的 EC 未被 SRAM 的臨時寫入所污染，且 Reset 後 Flash 數據正確載入 SRAM）。*修正分析：根據 step2 邏輯，先備份 SRAM (Flash 數據)，然後將 SRAM 寫入隨機值，接著 HW_RESET。Reset 後讀取 SRAM，預期值等於 Backup。這驗證了韌體在 HW_RESET 後的初始化流程中，會從 Flash 讀取正確的 EC 表並寫入 SRAM，覆蓋掉測試中注入的隨機值。*
2. **Flash 持久化驗證**：確認透過 Vendor Command 將 EC 值寫入 Flash (`set_in_ram=False`) 後，執行 HW_RESET，SRAM 中的 EC 值應與寫入 Flash 的值一致，驗證 Flash 寫入的持久性。
3. **LUN Reconfig EC Warning 機制驗證**：
   - Case A (EC=0)：當所有 VB 的 EC 被重置為 0 後執行 LUN Reconfig，Health Report 中的 `lun_reconfig_ec_warning` 應為 0，因為 EC 為 0 可能代表未初始化或特殊狀態，不觸發 Wear Leveling 異常警告。
   - Case B (EC=Random)：當所有 VB 的 EC 被設定為隨機非零值 (0x100~0x300) 後執行 LUN Reconfig，Health Report 中的 `lun_reconfig_ec_warning` 應為 1，驗證韌體在 Reconfig 過程中檢測到 EC 值與預期或內部狀態不一致時，會正確設置此警告標誌。

## Test Case (TC) Checkpoints

1. [Case01_SRAM_Write_SPOR_Restore_Check]：
   - 動作：
     1. 讀取 SRAM 中 `VB_list_cycle_address` 的當前內容作為備份 (`erase_cnt_buffer_backup`)，並記錄當前所有 VB 的讀取計數。
     2. 生成一個隨機整數 `random_value` (範圍 0x1 到 0x1000)。
     3. 構造 payload，將 `random_value` 填入每個 VB 對應的 4 位元組欄位。
     4. 呼叫 `project_api.set_all_VB_erase_count` 並設定 `set_in_ram=True`，將該 payload 寫入 SRAM。
     5. 立即讀取 SRAM 確認寫入成功（預期每個 VB 的 4 位元組值等於 `random_value`）。
     6. 執行 `api.init_tester_to_unit_ready` 觸發 `HW_RESET`。
     7. Reset 完成後，再次讀取 SRAM 中 `VB_list_cycle_address` 的內容。
   - 預期結果：
     - SRAM 讀回的值必須嚴格等於 `erase_cnt_buffer_backup`。
     - 這證明韌體在 HW_RESET 後的初始化階段，會從 Flash 讀取原始的 EC 表並寫入 SRAM，覆蓋了測試中注入的 SRAM 隨機值，確保 SRAM 狀態與 Flash 一致。

2. [Case02_Flash_Persistence_Check]：
   - 動作：
     1. 設定 `random_value` 為 0。
     2. 構造 payload，將 0 填入所有 VB 欄位。
     3. 呼叫 `project_api.set_all_VB_erase_count` 並設定 `set_in_ram=False`，將該 payload 寫入 Flash (非揮發性儲存)。
     4. 執行 `api.init_tester_to_unit_ready` 觸發 `HW_RESET`。
     5. Reset 完成後，讀取 SRAM 中 `VB_list_cycle_address` 的內容。
     6. 遍歷所有 VB，讀取每個 VB 對應的 4 位元組值。
   - 預期結果：
     - 每個 VB 從 SRAM 讀取的 4 位元組值必須等於 `random_value` (即 0)。
     - 這證明 `set_in_ram=False` 成功將 EC 值持久化到 Flash，且 Reset 後韌體從 Flash 讀取並寫入 SRAM 的機制正確運作，保留了 Flash 中的新值。

3. [Case03_LUN_Reconfig_EC_Zero_Warning_Check]：
   - 動作：
     1. 讀取當前 Wear Leveling 資訊。
     2. 執行 `reconfig_lun()`，透過修改 Config Descriptor 並發送 CMD 觸發 LUN 重新配置。
     3. 讀取 Enhanced Health Report (`issue_40FE`)。
     4. 檢查 `health_report.lun_reconfig_ec_warning` 欄位。
   - 預期結果：
     - `health_report.lun_reconfig_ec_warning.value` 必須等於 0。
     - 這驗證在 EC 為 0 的情境下，LUN Reconfig 不會觸發 EC 相關的警告標誌。

4. [Case04_LUN_Reconfig_EC_Random_Warning_Check]：
   - 動作：
     1. 生成一個隨機整數 `random_value` (範圍 0x100 到 0x300)。
     2. 構造 payload，將 `random_value` 填入所有 VB 欄位。
     3. 呼叫 `project_api.set_all_VB_erase_count` 並設定 `set_in_ram=False`，將該 payload 寫入 Flash。
     4. 執行 `api.init_tester_to_unit_ready` 觸發 `HW_RESET`，確保 SRAM 同步 Flash 中的隨機 EC 值。
     5. 讀取當前 Wear Leveling 資訊。
     6. 執行 `reconfig_lun()`，觸發 LUN 重新配置。
     7. 讀取 Enhanced Health Report (`issue_40FE`)。
     8. 檢查 `health_report.lun_reconfig_ec_warning` 欄位。
   - 預期結果：
     - `health_report.lun_reconfig_ec_warning.value` 必須等於 1。
     - 這驗證當 Flash 中的 EC 值被修改為非標準隨機值後，LUN Reconfig 過程中的韌體邏輯會檢測到此異常並設置 Health Report 中的警告標誌，表明 EC 狀態與 Reconfig 預期不符或需要關注。

5. [Case05_EC_Recovery_Check]：
   - 動作：
     1. 呼叫 `project_api.set_all_VB_erase_count`，使用步驟 1 中儲存的 `erase_cnt_buffer_backup` 作為 payload，並設定 `set_in_ram=False`。
   - 預期結果：
     - 此步驟為恢復操作，將 Flash 中的 EC 表恢復為測試前的原始狀態，確保測試環境的完整性，不產生錯誤檢查點，但為後續測試提供乾淨狀態。