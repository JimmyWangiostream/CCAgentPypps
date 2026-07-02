# Test Spec: UFS FTL Block Management Consistency Verification (4087/4004)

## Verification Criterion (VC)
驗證韌體內部 FTL 區塊管理結構（BBT, Bad Block Table）與外部報告 API（4087 Get ICS/CS Info, 4004 Get Boundary Blocks）之間的數據一致性與邏輯完整性：
1. **ICS 區塊數量一致性**：驗證 4087 API 回報的 `number_of_ics_table` 是否精確等於 4004 API 回報的 `ics_bound_ce0plane0` 減去 `spare_bound_ce0plane0`。
2. **CS 區塊總數邏輯驗證**：驗證 4087 API 回報的 `max_number_of_cs` 是否等於系統總虛擬區塊數 (`total_vb`) 減去 ICS 區塊數。
3. **早期壞塊計數一致性**：驗證 4087 API 回報的 `number_of_early_bb_at_t0` 是否等於透過遍歷所有 CE (Chip Enable) 與 Plane 讀取 BBT 結構中 `bad_blk_cnt` 欄位所累加的總和。
4. **運行時剩餘 CS 區塊計算驗證**：驗證 4087 API 回報的 `remianing_cs_at_run_time` 是否等於 `total_vb` 減去 ICS 區塊數、減去 Spare 區塊數（含偏移量 +1）、再減去當前 BBT 中的 `revoke_cnt`。

## Test Case (TC) Checkpoints
1. [ICS_Boundary_Consistency_Check]：
   - 動作：呼叫 `project_api.issue_4087_get_ics_cs_info_description()` 取得 4087 回應結構，提取 `number_of_ics_table.value` 作為 `compare_value`；同時呼叫 `project_api.issue_4004_get_boundaryblocks_for_hiddentable_static_dynamicpool()` 取得 4004 回應結構，計算 `ics_bound_ce0plane0.value - spare_bound_ce0plane0.value` 作為 `expected_value`。
   - 預期結果：`compare_value` 必須嚴格等於 `expected_value`。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表 FTL 內部 ICS 邊界定義與外部報告 API 存在數據不一致。

2. [Max_CS_Count_Logical_Check]：
   - 動作：透過 `read_fw_value('gUfsApiStruct.ftl->addr_rule.geometry.total_vb')` 讀取韌體記憶體中的總虛擬區塊數 (`total_vb`)；從 4087 API 回應中取得 `number_of_ics_table.value`；計算 `expected_value = int(total_vb) - number_of_ics_table.value`；從 4087 API 回應中取得 `max_number_of_cs.value` 作為 `compare_value`。
   - 預期結果：`compare_value` 必須嚴格等於 `expected_value`。驗證系統定義的最大 CS 區塊數量確實為總 VB 數扣除 ICS 保留區塊後的剩餘空間。

3. [Early_Bad_Block_Count_Aggregation_Check]：
   - 動作：初始化 `bad_blk_cnt = 0`；遍歷所有 CE (範圍 0 至 `flash_setting.Max_Fdevice - 1`) 與所有 Plane (範圍 0 至 5)；對於每個 CE/Plane 組合，動態構建並讀取韌體記憶體路徑 `gUfsApiStruct.ftl->bbt.bbt_info_ce[ce].bbt_info[plane].bad_blk_cnt`，將讀取值累加至 `bad_blk_cnt`；從 4087 API 回應中取得 `number_of_early_bb_at_t0.value` 作為 `compare_value`；設定 `expected_value = bad_blk_cnt`。
   - 預期結果：`compare_value` 必須嚴格等於 `expected_value`。驗證 4087 API 回報的早期壞塊總數是否與 FTL BBT 結構中各 CE/Plane 層級壞塊計數的硬體實際累加值完全吻合。

4. [Remaining_CS_Runtime_Calculation_Check]：
   - 動作：讀取韌體記憶體中的 `total_vb`；計算 `ics_blk = ics_bound_ce0plane0.value - spare_bound_ce0plane0.value`；讀取韌體記憶體中的 `revoke_cnt` (`gUfsApiStruct.ftl->bbt.revoke_cnt`)；從 4004 API 回應中取得 `spare_bound_ce0plane0.value`；計算 `expected_value = total_vb - ics_blk - (spare_bound_ce0plane0.value + 1) - revoke_cnt`；從 4087 API 回應中取得 `remianing_cs_at_run_time.value` 作為 `compare_value`。
   - 預期結果：`compare_value` 必須嚴格等於 `expected_value`。驗證韌體在運行時報告的剩餘 CS 區塊數，是否精確符合「總 VB 減去 ICS 區塊、減去 Spare 區塊（含 1 個偏移量修正）、減去當前撤銷計數」的硬體資源分配邏輯。