# Test Spec: UFS Host Unmap Command Multi-Block Descriptor Validation

## Verification Criterion (VC)
驗證 UFS 主機端透過 `Unmap` 命令發送包含多個 Block Descriptor 的請求時，韌體與控制器能否正確解析並執行非連續邏輯區塊的釋放操作：Case 01 確認 LBA 0 的 1 個邏輯區塊被正確標記為 Unmap；Case 02 確認 LBA 1 的 2 個邏輯區塊（LBA 1 與 LBA 2）被正確標記為 Unmap。整體驗證重點在於 `Unmap` 命令中 `Block Descriptor List` 的結構完整性與 LBA 範圍計算的準確性，確保控制器能正確處理 `l4_lba_l` (LBA Low) 與 `l8_number_of_logical_blocks` (Number of Logical Blocks) 欄位的組合，並對 Normal LUN 執行對應的邏輯區塊釋放流程。

## Test Case (TC) Checkpoints
1. [Unmap_Multi_Block_Descriptor_Execution]：
   - 動作：
     1. 初始化 `Unmap` 命令物件。
     2. 建立第一個 `UnmapBlockDescriptor`：設定 `l4_lba_l` 為 0，`l8_number_of_logical_blocks` 為 1。此描述符代表釋放起始於 LBA 0 的 1 個邏輯區塊。
     3. 建立第二個 `UnmapBlockDescriptor`：設定 `l4_lba_l` 為 1，`l8_number_of_logical_blocks` 為 2。此描述符代表釋放起始於 LBA 1 的 2 個邏輯區塊（即 LBA 1 和 LBA 2）。
     4. 將上述兩個描述符加入 `unmaplist`。
     5. 透過 `cmd.assign_multi_cmd(lun=0, block_descriptor=unmaplist)` 將描述符列表綁定至 LUN 0 的 `Unmap` 命令。
     6. 將命令入隊 (`enqueue`) 並發送 (`send`) 至 UFS 裝置。
   - 預期結果：
     - 命令發送成功，無協議層錯誤（如 INVALID FIELD 或 COMMAND SEQUENCE ERROR）。
     - UFS 裝置韌體應正確解析 `Block Descriptor List`，並對 LUN 0 執行以下邏輯區塊釋放：
       - LBA 0：狀態變更為 Unmap。
       - LBA 1：狀態變更為 Unmap。
       - LBA 2：狀態變更為 Unmap。
     - 驗證控制器能正確處理多描述符結構，確保每個描述符的 LBA 起始地址與區塊數量被獨立且準確地應用於內部邏輯區塊映射表（L2P Table）或快閃記憶體管理單元，未發生 LBA 偏移計算錯誤或描述符丟失。