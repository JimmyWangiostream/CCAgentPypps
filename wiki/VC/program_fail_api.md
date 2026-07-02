# Test Spec: UFS LUN Configuration & Enhanced Memory 1 (EM1) Allocation Verification

## Verification Criterion (VC)
驗證 UFS 裝置在透過 Vendor Command 或標準 Descriptor 寫入流程中，對 Normal LUN 與 Enhanced Memory 1 (EM1) LUN 的資源分配邏輯與硬體狀態初始化：
1. **LUN 配置正確性**：確認 `ExecuteCMD.WriteDescriptor` 能正確將指定的 LUN ID 映射為 `MemoryType.NORMAL` 或 `MemoryType.ENHANCED_1`，並依據 `shared.param.gGeometry` 中的幾何參數（如 `l13_segment_size`, `b17_allocation_unit_size`）精確計算並分配 `num_alloc_units`。
2. **EM1 資源優先級與總量限制**：驗證 EM1 LUN 分配的總 AU 數量嚴格受限於 `l44_enhanced1_max_n_alloc_u` 參數，且 Normal LUN 與 EM1 LUN 之間依據數量比例公平分配剩餘容量。
3. **硬體狀態同步**：確認在 Descriptor 寫入並發送後，透過 `ReadDescriptor` 讀回的 Unit Descriptor 中，`b3_lu_enable` 狀態與 `b3_memory_type` 與預期設定完全一致，且 `TestUnitReady` 成功通過，代表韌體已接受該 LUN 配置並準備就緒。

## Test Case (TC) Checkpoints
1. [LUN_Configuration_Allocation_Check]：
   - 動作：
     1. 計算總可用 AU 數量：`Total_AU_Count = gGeometry.q4_total_raw_device_capacity / (l13_segment_size * b17_allocation_unit_size)`。
     2. 根據輸入的 `normal_list` 與 `em1_list` 長度，計算 EM1 專屬 AU 上限：`EM1_total_AU = min(gGeometry.l44_enhanced1_max_n_alloc_u, Total_AU_Count / (len(normal) + len(em1)) * len(em1))`。
     3. 計算 Normal 專屬 AU 數量：`normal_total_AU = Total_AU_Count / (len(normal) + len(em1)) * len(normal)`。
     4. 執行 4 次 `WriteDescriptor` 循環（index 0-3），針對每個 LUN Unit (0-31)：
        - 若 LUN ID 在 `normal_list` 中：設定 `b3_memory_type = NORMAL`，`l4_num_alloc_units = normal_total_AU / len(normal_list)`，`b10_provisioning_type = THIN_PROVISIONING_ERASE`。
        - 若 LUN ID 在 `em1_list` 中：設定 `b3_memory_type = ENHANCED_1`，`l4_num_alloc_units = EM1_total_AU / len(em1_list)`，`b10_provisioning_type = THIN_PROVISIONING_ERASE`。
        - 其他 LUN：設定 `b0_lu_enable = DISABLE`。
     5. 發送 Descriptor 寫入命令，隨後執行 `ReadDescriptor` 讀回所有 LUN 的 Unit Descriptor。
     6. 對所有啟用的 LUN 執行 `TestUnitReady`。
   - 預期結果：
     - 讀回的 Unit Descriptor 中，`b3_memory_type` 必須精確對應為 `NORMAL` (0x00) 或 `ENHANCED_1` (0x01)。
     - `l4_num_alloc_units` 欄位數值必須等於計算出的整數值，且所有啟用 LUN 的 AU 總和等於 `Total_AU_Count`。
     - `b10_provisioning_type` 必須為 `THIN_PROVISIONING_ERASE`。
     - `TestUnitReady` 必須返回成功狀態碼，表示硬體已接受配置並進入 Ready 狀態。

2. [EM1_Resource_Limit_Verification]：
   - 動作：
     1. 檢查 `EM1_total_AU` 的計算邏輯，確保其未超過 `shared.param.gGeometry.l44_enhanced1_max_n_alloc_u` 定義的硬體上限。
     2. 驗證在 `WriteDescriptor` 中，對於 `em1_list` 中的每個 LUN，其分配的 `l4_num_alloc_units` 是基於 `EM1_total_AU` 平均分配，而非基於總容量。
     3. 確認 `WriteBoosterBuffer` 相關設定：在 index 0 的 Descriptor 中，`l18_num_shared_write_booster_buffer_alloc_units` 設定為 `gGeometry.l79_write_booster_buffer_max_n_alloc_units`，其餘 index 為 0。
   - 預期結果：
     - EM1 LUN 的總分配 AU 數量嚴格小於或等於 `l44_enhanced1_max_n_alloc_u`。
     - Normal LUN 的分配不受 EM1 上限影響，僅受剩餘容量比例影響。
     - Write Booster Buffer 的共享配置僅在第一個 Descriptor Block (index 0) 生效，確保硬體 Write Booster 區域正確初始化。

3. [Descriptor_Synchronization_Check]：
   - 動作：
     1. 在 `WriteDescriptor` 發送後，立即執行 `ReadDescriptor` 並使用 `api.update_descriptor` 更新本地緩存。
     2. 檢查 `shared.param.gUnit[lun]` 中的 `b3_lu_enable` 欄位。
     3. 對所有 `b3_lu_enable` 為 True 的 LUN 執行 `TestUnitReady`。
   - 預期結果：
     - 本地緩存中的 `b3_lu_enable` 狀態必須與硬體實際狀態一致（即 `normal_list` 和 `em1_list` 中的 LUN 為 Enable，其他為 Disable）。
     - 所有啟用的 LUN 必須通過 `TestUnitReady`，證明韌體已將 Descriptor 配置應用於硬體邏輯單元，且無配置衝突或硬體錯誤。