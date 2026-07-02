# Test Spec: FTL Wear Leveling (WL) Trigger Mechanism Verification via Vendor Command Injection

## Verification Criterion (VC)
驗證 FTL 韌體在透過 Vendor Command (C072/C083) 強制修改 Wear Leveling 內部狀態（EC 計數器、Global Version、Thresholds）後，BKOPS 機制能否正確觸發並執行 Wear Leveling GC 流程：
1. **Static Pool (SLC/EM1)**：確認當 Source VB (EM1) 的 EC 被強制設為 0，且 Target VB (Free) 的 EC 被設為超過 Threshold (TH1/TH2) 時，系統能識別出巨大的 EC Gap，進而觸發 SWLG (Static Wear Leveling GC)。驗證指標包括：`totalSWLGCTriggerCount` 增加 1，`totalSWLBGGCTriggerCount` (TH1) 或 `totalSWLFGGCTriggerCount` (TH2) 增加 1，且 Source VB 的 `force_bit` 被標記為 1。
2. **Dynamic Pool (TLC/TLC_WB)**：確認當 Source VB (TLC) 的 EC 被強制設為 0，且 Target VB (Free) 的 EC 被設為超過 Threshold 時，系統觸發 SWLG (Dynamic Wear Leveling GC)。驗證指標包括：`totalSWLGCTriggerCount` 增加 1，且 Source VB 的 `force_bit` 被標記為 1。
3. **Edge Case (MAX_VALUE)**：確認當 Global Version 被強制設為 `0x7FFF` (MAX_VALUE) 時，韌體內部會將其重置為 0，防止版本號溢出導致邏輯錯誤。
4. **State Transition**：確認 GC 執行後，Source VB 從原 Pool (EM1/TLC) 遷移至 Free Queue，Target VB 從 Free Queue 遷移至原 Pool，且 `IsDfgSrc` 標記正確更新。

## Test Case (TC) Checkpoints

1. [Static_Pool_TH1_WL_GC_Trigger_Check]：
   - 動作：
     1. 配置 LUN：LUN 0 (Normal/TLC), LUN 1 (EM1/SLC), LUN 2 (WB/TLC)。
     2. 寫入資料以建立 VB，並透過 `issue_4098` 獲取初始 Wear Leveling 狀態 (`wear_leveling_A`)。
     3. 設定 `GC_case` 為 `USED_BLK_POOL_EM1` (Static Pool)，`threshold_case` 為 `TH1`。
     4. 計算 Static Pool 的 TH1 Threshold (`gEC_gap_delta_TH1_static`)。
     5. 透過 Vendor Command 設定所有 VB 的 EC payload，並將 Source VB (EM1 中的第一個 VB) 的 EC 設為 0，將 Target VB (Free Queue 中的隨機 VB) 的 EC 設為 `TH1 + 1`。
     6. 根據 `trigger_case` (預設為 `is_prior_round`)，更新對應的 FTL Version。
     7. 透過 Vendor Command `C072` 設定 Static/Dynamic Pool 的 Global EC 閾值及 Delta Thresholds。
     8. 再次寫入 EC Payload 到 RAM，並透過 `issue_4098` 獲取中間狀態 (`wear_leveling_C`) 確認設定生效。
     9. 執行 `polling_bkops_idle` 等待 BKOPS 完成。
     10. 透過 `issue_4098` 獲取最終狀態 (`wear_leveling_D`)。
   - 預期結果：
     - `wear_leveling_D.totalSWLGCTriggerCount_of_static_pool` 相比 `wear_leveling_A` 增加 1。
     - `wear_leveling_D.totalSWLBGGCTriggerCount_of_static_pool` 相比 `wear_leveling_A` 增加 1 (因為是 TH1)。
     - Source VB (`source_vb`) 的 `force_bit` 必須等於 1。
     - Source VB 的 `VBListNum` 從 `USED_BLK_POOL_EM1` 變更為 `FREE_BLK_QUEUE_EM1`。
     - Target VB (`target_vb`) 的 `VBListNum` 從 `FREE_BLK_QUEUE_EM1` 變更為 `USED_BLK_POOL_EM1`。
     - Source VB 的 `IsDfgSrc` 必須等於 1。

2. [Static_Pool_TH2_WL_GC_Trigger_Check]：
   - 動作：
     1. 重複 [Static_Pool_TH1_WL_GC_Trigger_Check] 的步驟 1-8，但將 `threshold_case` 設為 `TH2`。
     2. 設定 Target VB 的 EC 為 `TH2 + 1`。
     3. 執行 BKOPS 等待與狀態檢查。
   - 預期結果：
     - `wear_leveling_D.totalSWLGCTriggerCount_of_static_pool` 增加 1。
     - `wear_leveling_D.totalSWLFGGCTriggerCount_of_static_pool` 增加 1 (因為是 TH2)。
     - 其他狀態轉換 (VB List Num, Force Bit, IsDfgSrc) 與 TH1 案例相同。

3. [Dynamic_Pool_WL_GC_Trigger_Check]：
   - 動作：
     1. 配置 LUN 並寫入資料。
     2. 設定 `GC_case` 為 `USED_BLK_POOL_TLC` (Dynamic Pool)。
     3. 設定 `threshold_case` 為 `TH1` (或 TH2)。
     4. 設定 Source VB (TLC 中的 VB) EC 為 0，Target VB (Free Queue 中的 VB) EC 為 `TH1 + 1` (或 `TH2 + 1`)。
     5. 透過 `C072` 設定 Dynamic Pool 的 Global EC 閾值。
     6. 執行 BKOPS 等待與狀態檢查。
   - 預期結果：
     - `wear_leveling_D.totalSWLGCTriggerCount_of_dynamic_pool` 增加 1。
     - 若為 TH1，`totalSWLBGGCTriggerCount_of_dynamic_pool` 增加 1；若為 TH2，`totalSWLFGGCTriggerCount_of_dynamic_pool` 增加 1。
     - Source VB 的 `force_bit` 必須等於 1。
     - Source VB 的 `VBListNum` 從 `USED_BLK_POOL_TLC` 變更為 `FREE_BLK_QUEUE_TLC`。
     - Target VB 的 `VBListNum` 從 `FREE_BLK_QUEUE_TLC` 變更為 `USED_BLK_POOL_TLC`。

4. [TLC_WB_Pool_WL_GC_Trigger_Check]：
   - 動作：
     1. 配置 LUN 並寫入資料，啟用 `WRITEBOOSTER_EN`。
     2. 設定 `GC_case` 為 `USED_BLK_POOL_TLC_WB`。注意：代碼邏輯中此情況下 `new_group` 會被強制設為 `USED_BLK_POOL_TLC`，且 `lun` 設為 `TestWBLun` (LUN 2)，`vbsize` 設為 SLC size。
     3. 設定 Source VB (WB LUN 中的 VB) EC 為 0，Target VB (Free Queue 中的 VB) EC 為 `TH1 + 1`。
     4. 執行 BKOPS 等待與狀態檢查。
   - 預期結果：
     - 此測試驗證 Write Booster 情境下的 Wear Leveling 觸發。
     - `wear_leveling_D.totalSWLGCTriggerCount_of_dynamic_pool` 增加 1。
     - Source VB 的 `VBListNum` 應從 `USED_BLK_POOL_TLC_WB` (或代碼中映射的邏輯組) 變更為 `FREE_BLK_QUEUE_TLC`。
     - Target VB 的 `VBListNum` 應從 `FREE_BLK_QUEUE_TLC` 變更為 `USED_BLK_POOL_TLC` (注意代碼邏輯中 `new_group` 被硬編碼為 TLC Pool)。
     - Source VB 的 `force_bit` 必須等於 1。

5. [Static_Pool_MAX_Version_Reset_Check]：
   - 動作：
     1. 配置 LUN 並寫入資料。
     2. 設定 `GC_case` 為 `USED_BLK_POOL_EM1`。
     3. 設定 `trigger_case` 為 `is_MAX_VALUE`。
     4. 透過 `api.set_ftl_version` 將 `slc_partition_current_vb_version` 設為 `0x7FFF`。
     5. 設定 Source VB EC 為 0，Target VB EC 為 `TH1 + 1`。
     6. 執行 BKOPS 等待。
     7. 檢查 `wear_leveling_C` (設定後) 或 `wear_leveling_D` (GC 後) 的 Global Version。
   - 預期結果：
     - `wear_leveling_C.globalVersion_of_static_pool.value` 必須等於 0。
     - 若不等於 0，測試應拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。
     - 這驗證了韌體在處理 MAX_VALUE 版本號時的邊界條件保護機制。

6. [Dynamic_Pool_MAX_Version_Reset_Check]：
   - 動作：
     1. 配置 LUN 並寫入資料。
     2. 設定 `GC_case` 為 `USED_BLK_POOL_TLC`。
     3. 設定 `trigger_case` 為 `is_MAX_VALUE`。
     4. 透過 `api.set_ftl_version` 將 `mlc_partition_current_vb_version` 設為 `0x7FFF`。
     5. 設定 Source VB EC 為 0，Target VB EC 為 `TH1 + 1`。
     6. 執行 BKOPS 等待。
     7. 檢查 `wear_leveling_C` 的 Global Version。
   - 預期結果：
     - `wear_leveling_C.globalVersion_of_dynamic_pool.value` 必須等於 0。
     - 若不等於 0，測試應拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。