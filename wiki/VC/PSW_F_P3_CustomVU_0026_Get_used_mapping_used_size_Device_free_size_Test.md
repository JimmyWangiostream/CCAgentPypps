# Test Spec: UFS VU 40A8 Mapping & Free Space Verification under SLC/MLC & WriteBooster Configurations

## Verification Criterion (VC)
驗證 UFS 裝置在動態配置 Normal (MLC) 與 Enhanced_1 (SLC) LUN 比例，以及 WriteBooster 開關狀態下，Vendor Command 0x40A8 (Get Used Mapping/Free Size) 的回應數據與實際邏輯區塊分配的一致性：
1. **初始狀態驗證**：確認在特定 LUN 配置（Normal/EM1 比例變化）及 WriteBooster 啟用/禁用下，Mode 1 回報的 `data_free_size` 等於 Normal LUN 的總容量（MB），Mode 2 回報的 `mapping_size_of_device` 為 0（無有效映射）。
2. **寫入後狀態驗證**：在 Normal LUN 執行隨機寫入（Write10）後，確認 Mode 1 的 `data_free_size` 精確扣除已寫入的 Normal LUN 有效數據量，Mode 2 的 `mapping_size_of_device` 精確等於已寫入的 Normal LUN 有效 Node 總數。
3. **Unmap 後狀態驗證**：對已寫入的 Normal LUN 執行 Unmap 操作後，確認 Mode 1 的 `data_free_size` 恢復（加上被 Unmap 的數據量），Mode 2 的 `mapping_size_of_device` 精確扣除被 Unmap 的 Node 總數。
4. **邊界條件驗證**：驗證當寫入長度非 4KB 整數倍時，韌體是否正確處理 Overwrite/Alignment 邏輯，確保 `data_free_size` 計算無誤。

## Test Case (TC) Checkpoints

1. **[Case01_100_Normal_0_EM1_PreWrite_Check]**：
   - 動作：配置 LUN 為 100% Normal (MLC) / 0% Enhanced_1 (SLC)，若 `wb_case=1` 則啟用 WriteBooster。執行 `issue_40A8_to_get_used_mapping_used_size_device_free_size` 兩次：
     - Mode 1：獲取 `data_free_size`。
     - Mode 2：獲取 `mapping_size_of_device`。
   - 預期結果：
     - Mode 1 的 `data_free_size` 必須等於所有 Normal LUN 的總容量（MB），計算公式為 `(sum(gLUCapacity[normal_luns]) * 4KB) / 1MB`。
     - Mode 2 的 `mapping_size_of_device` 必須嚴格等於 `0`，代表初始狀態下無任何邏輯區塊映射。

2. **[Case02_50_Normal_50_EM1_PreWrite_Check]**：
   - 動作：配置 LUN 為 50% Normal / 50% Enhanced_1。執行與 Case 01 相同的 Mode 1 和 Mode 2 查詢。
   - 預期結果：
     - Mode 1 的 `data_free_size` 必須等於 Normal LUN 組的總容量（MB），EM1 LUN 的容量不應計入此欄位（因為 EM1 通常用於系統或特定用途，此測試假設僅 Normal LUN 提供用戶可用空間給此指標，或根據韌體定義，此處預期僅 Normal LUN 容量）。
     - Mode 2 的 `mapping_size_of_device` 必須嚴格等於 `0`。

3. **[Case03_0_Normal_100_EM1_PreWrite_Check]**：
   - 動作：配置 LUN 為 0% Normal / 100% Enhanced_1。執行 Mode 1 和 Mode 2 查詢。
   - 預期結果：
     - Mode 1 的 `data_free_size` 必須等於 `0`（因為沒有 Normal LUN 提供空間）。
     - Mode 2 的 `mapping_size_of_device` 必須嚴格等於 `0`。

4. **[Case04_Normal_Write_PostCheck]**：
   - 動作：
     1. 針對所有 Normal LUN 執行隨機長度寫入（Write10），記錄每個 LUN 的寫入長度 `total_len` 及總有效 Node 數 `total_valid_node`。
     2. 若 `total_valid_node` 非 4096 的倍數，計算餘數 `overwrite_len`，並在擁有最大寫入量的 LUN (`max_write_lun`) 上執行額外的 `overwrite_len` 寫入以對齊。
     3. 針對所有 Enhanced_1 LUN 執行隨機寫入。
     4. 再次執行 Mode 1 和 Mode 2 查詢。
   - 預期結果：
     - Mode 1 的 `data_free_size` 必須等於 `(total_normal_node - total_valid_node) * 4KB / 1MB`。這驗證了韌體正確扣除了 Normal LUN 上的有效數據空間。
     - Mode 2 的 `mapping_size_of_device` 必須嚴格等於 `total_valid_node`。這驗證了韌體正確統計了 Normal LUN 上的有效映射節點數。

5. **[Case05_Normal_Unmap_PostCheck]**：
   - 動作：
     1. 針對之前寫入的 Normal LUN 執行 Unmap 操作，記錄被 Unmap 的長度 `total_invalid_node`。
     2. 針對 Enhanced_1 LUN 執行隨機 Unmap。
     3. 再次執行 Mode 1 和 Mode 2 查詢。
   - 預期結果：
     - Mode 1 的 `data_free_size` 必須等於 `(total_normal_node - total_valid_node + total_invalid_node) * 4KB / 1MB`。這驗證了 Unmap 操作後，對應的邏輯區塊被標記為無效，`data_free_size` 相應增加。
     - Mode 2 的 `mapping_size_of_device` 必須嚴格等於 `total_valid_node - total_invalid_node`。這驗證了韌體正確移除了被 Unmap 的邏輯區塊映射，僅保留剩餘的有效映射。

6. **[Case06_WriteBooster_Effect_Check]**：
   - 動作：在 `wb_case=1` (WriteBooster Enabled) 的情境下，重複 Case 04 和 Case 05 的寫入與 Unmap 流程。
   - 預期結果：
     - 儘管 WriteBooster 可能改變底層物理頁面的分配策略（例如先寫入 WB Buffer 再搬遷），但 Vendor Command 0x40A8 回報的邏輯層面 `data_free_size` 和 `mapping_size_of_device` 必須與 `wb_case=0` 時的數值邏輯完全一致。這驗證了 WriteBooster 的透明性，即邏輯空間管理不受 WB 機制干擾。