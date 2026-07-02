# Test Spec: PS8329 B68S ASIC ID & NAND Topology Verification via Vendor Command 0x40B3

## Verification Criterion (VC)
驗證 UFS 韌體透過 Vendor Command `0x40B3` 回傳的 ASIC ID 資訊與硬體實體配置的一致性：
1. **CE 數量一致性**：確認韌體報告的 `nand_id_item_count` 必須嚴格等於硬體配置的 `Max_Fdevice` (CE 數量)。
2. **控制器型號識別**：確認韌體報告的 `controller_and_nand_type_ascii` 必須精確匹配預期字串 `'PS8329 B68S'`。
3. **Die 索引與 Flash ID 映射**：針對每個存在的 CE (0 至 3)，確認其對應的 `die_idx` 與實際 CE 索引一致，且 `nand_flash_id` 必須為固定的硬體識別碼 `0x2cd30832e8361200`。此驗證確保韌體正確識別了多通道 NAND 的拓撲結構與晶片身份。

## Test Case (TC) Checkpoints
1. [ASIC_ID_40B3_Response_Validation]：
   - 動作：
     1. 呼叫 `get_flash_setting()` 獲取硬體配置的 `Max_Fdevice` (記為 `ce_num`)。
     2. 透過 `project_api.issue_40B3_to_get_asic_id()` 發送 Vendor Command `0x40B3` 並獲取回應結構體 `ascid`。
     3. **檢查 CE 數量**：驗證 `ascid.nand_id_item_count.value` 是否等於 `ce_num`。
     4. **檢查控制器型號**：將 `ascid.controller_and_nand_type_ascii.value` 轉換為 ASCII 字串，並驗證其是否等於 `'PS8329 B68S'`。
     5. **檢查 Die 索引與 Flash ID**：根據 `ce_num` 的實際值，依序驗證以下欄位：
        - 若 `ce_num >= 1`：驗證 `ascid.die_idx_0.value == 0` 且 `ascid.nand_flash_id_idx0.value == 0x2cd30832e8361200`。
        - 若 `ce_num >= 2`：驗證 `ascid.die_idx_1.value == 1` 且 `ascid.nand_flash_id_idx1.value == 0x2cd30832e8361200`。
        - 若 `ce_num >= 4`：驗證 `ascid.die_idx_2.value == 2` 且 `ascid.nand_flash_id_idx2.value == 0x2cd30832e8361200`；同時驗證 `ascid.die_idx_3.value == 3` 且 `ascid.nand_flash_id_idx3.value == 0x2cd30832e8361200`。
   - 預期結果：
     - `nand_id_item_count` 必須與 `Max_Fdevice` 完全一致，否則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 控制器型號字串必須為 `'PS8329 B68S'`，否則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 所有存在的 CE 通道，其 `die_idx` 必須從 0 開始遞增對應，且每個通道的 `nand_flash_id` 必須精確等於 `0x2cd30832e8361200`。任何不匹配均視為硬體拓撲識別失敗，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。