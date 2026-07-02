# Test Spec: UFS Firmware TempCo Trim Adaptation & EC Threshold Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 MLC 區塊擦寫計數（Erase Count, EC）變化時，TempCo Trim 參數的動態切換機制與硬體狀態一致性：
1. **初始狀態驗證**：確認韌體讀取的預設 TempCo Trim 值與 pConfig 中儲存的 EC0 預設值一致，且當前 MLC 平均 EC 符合預設閾值邏輯。
2. **低 EC 狀態驗證**：透過 Vendor Command 強制覆寫 SRAM 中的 EC 表為 `XTEMP_EC1 - 1`，觸發 HW_RESET 後，確認韌體載入對應 EC1 的 TempCo Trim 值，且 FW Geometry 回報的平均 EC 與設定值一致。
3. **高 EC 狀態驗證**：在低 EC 設定下執行隨機寫入，直到 FW Geometry 回報的平均 EC 達到 `XTEMP_EC1` 閾值，確認韌體自動切換至 EC2 的 TempCo Trim 值。
4. **邊界與恢復驗證**：驗證 EC 閾值觸發時的 Trim 值跳變精確性，並在測試結束後透過 Vendor Command 恢復原始 EC 表，確保系統狀態可逆。

## Test Case (TC) Checkpoints

1. [Case01_Initial_Config_and_Default_Trim_Check]：
   - 動作：
     1. 透過 `get_pConfig_data` 讀取 pConfig payload，解析位址 28-35 的 `XTEMP_EC` 閾值（4個值）及位址 36-99 的 `TEMPCO_TRIM_ADDR`。
     2. 解析位址 100 起每 32 bytes 對應 EC1-4 的 TempCo Trim 數據。
     3. 配置 LUN0 為 Normal Memory，大小 2GB（`l4_num_alloc_units = 0x200`, `b9_logical_block_size = 0xc`），禁用其他 LUN。
     4. 透過 Vendor Command `get_debug_info` 取得 `VB_list_cycle_address`，並讀取 SRAM 中的原始 EC 表（Backup EC）。
     5. 針對 `TEMPCO_TRIM_ADDR` 中的 6 組位址，透過 Vendor Command 0x4084 讀取當前 NAND Trim 值。
     6. 讀取 `fw_geometry.l4180_d2d3_avg_erase_cnt` 獲取當前 MLC 平均 EC。
     7. 比對當前平均 EC 與 `XTEMP_EC` 閾值，若 `mlc_avg_ec >= XTEMP_EC_value[XTEMP_EC]`，則驗證當前 Trim 值是否等於對應 EC 組的 `TEMPCO_TRIM` 前 24 個值。
   - 預期結果：
     - LUN 配置成功應用。
     - 當前讀取的 Trim 值列表（`defaultlist`）必須精確等於 `TEMPCO_TRIM[1]`（即 EC1 對應的預設 Trim 值）。
     - 若當前平均 EC 已超過某個閾值，則驗證邏輯需正確匹配該閾值對應的 Trim 組別，否則報錯 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [Case02_Low_EC_Setting_and_HW_Reset_Check]：
   - 動作：
     1. 針對第一個閾值 `XTEMP_EC_value[0]`（EC1），計算目標 EC 值為 `XTEMP_EC_value[0] - 1`。
     2. 呼叫 `set_device_ec`，透過 Vendor Command Write (CDB2=4) 將 SRAM 中對應 `total_VB_count` 長度的 EC 表覆寫為 `XTEMP_EC_value[0] - 1`。
     3. 執行 `api.init_tester_to_unit_ready` 進行 HW_RESET 並上電。
     4. 韌體啟動後，再次透過 Vendor Command 0x4084 讀取 NAND Trim 值。
     5. 讀取 `fw_geometry.l4180_d2d3_avg_erase_cnt`。
   - 預期結果：
     - 讀取的 Trim 值列表（`currentlist`）必須精確等於 `TEMPCO_TRIM[1]`（EC1 對應的 Trim 值）。
     - `fw_geometry.l4180_d2d3_avg_erase_cnt` 必須等於 `XTEMP_EC_value[0] - 1`。
     - 若任一條件不符，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 並恢復 EC。

3. [Case03_EC_Threshold_Trigger_and_Trim_Switch_Check]：
   - 動作：
     1. 在 Case02 的設定下（EC 設為 `XTEMP_EC_value[0] - 1`），執行隨機寫入操作。
     2. 寫入參數：LUN 0，LBA 範圍 0 至 `gLUCapacity[0]`，每次寫入大小隨機 64MB-128MB，共 200 次命令。
     3. 循環執行寫入並檢查 `fw_geometry.l4180_d2d3_avg_erase_cnt`，直到該值等於 `XTEMP_EC_value[0]`（觸發閾值）。
     4. 閾值觸發後，立即透過 Vendor Command 0x4084 讀取 NAND Trim 值。
   - 預期結果：
     - 寫入過程需在 60 分鐘內完成，否則報錯 `PATTERN_ASSERT_STUCK_WHILE_TIMEOUT`。
     - 讀取的 Trim 值列表必須精確等於 `TEMPCO_TRIM[2]`（EC2 對應的 Trim 值）。
     - 此結果證明當 MLC 平均 EC 達到 `XTEMP_EC_value[0]` 時，韌體已自動切換至下一階段的 TempCo Trim 參數。

4. [Case04_Subsequent_EC_Levels_Verification]：
   - 動作：
     1. 重複 Case02 和 Case03 的邏輯，針對 `XTEMP_EC_value[1]` 至 `XTEMP_EC_value[3]`（對應 EC2, EC3, EC4）。
     2. 設定 EC 為 `XTEMP_EC_value[i] - 1`，HW_RESET，驗證 Trim 值等於 `TEMPCO_TRIM[i+1]` 且平均 EC 一致。
     3. 執行隨機寫入直到平均 EC 達到 `XTEMP_EC_value[i]`，驗證 Trim 值切換為 `TEMPCO_TRIM[i+2]`。
   - 預期結果：
     - 所有 EC 階段的 Trim 值切換必須精確匹配 pConfig 中定義的 `TEMPCO_TRIM` 數據。
     - 任何階段的 Trim 值不匹配或 EC 計數器異常，均觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

5. [Case05_ECR_Recovery_Check]：
   - 動作：
     1. 測試結束後，呼叫 `recover_ec`。
     2. 該函數透過 Vendor Command Write 將之前備份的 `backup_ec_value`（原始 SRAM EC 表）寫回設備。
   - 預期結果：
     - 設備內的 EC 表恢復為測試前的原始狀態，確保後續測試或生產環境不受影響。