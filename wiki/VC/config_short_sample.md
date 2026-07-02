# Test Spec: UFS Configuration Descriptor Dynamic Allocation & Multi-LUN Setup Test

## Verification Criterion (VC)
驗證 UFS 裝置在動態配置描述符（Configuration Descriptor）修改下的硬體行為：Case 01 確認主 LUN (Index 0) 的分配單元數（Alloc Units）減少 4 後，韌體能正確更新內部狀態並反映在讀回的描述符中；Case 02 確認並行配置三個額外 LUN (Index 1, 2, 3) 為單一分配單元（1AU）、啟用狀態（b0_lu_enable=1）及 4KB 邏輯區塊大小（b9_logical_block_size=0xC），並透過 b2_conf_desc_continue 鏈結機制確保配置指令的完整傳輸與應用，最終驗證所有 LUN 的配置參數在硬體層面已正確生效。

## Test Case (TC) Checkpoints
1. [Case01_Primary_LUN_Alloc_Reduction_Check]：
   - 動作：讀取當前配置描述符，將 Index 0 (Primary LUN) 的 `b2_conf_desc_continue` 設為 1 以標記鏈結開始，將其 `units[0].l4_num_alloc_units` 減去 4，接著呼叫 `push_write_config` 寫入 Index 0 並執行 `ExecuteCMD.send()` 發送配置指令。發送後再次讀取配置描述符，並針對 Index 0 執行 `print_config` 輸出詳細內容。
   - 預期結果：讀回的配置描述符中，Index 0 的 `l4_num_alloc_units` 欄位數值必須等於原始值減 4；`b2_conf_desc_continue` 欄位必須為 1，代表該配置單元是連續配置序列的一部分，且硬體已接受此容量縮減請求。

2. [Case02_Multi_LUN_Initialization_Check]：
   - 動作：針對 Index 1, 2, 3 的配置描述符進行設定：將 `b2_conf_desc_continue` 設為 1 (Index 1-2) 或 0 (Index 3 為最後一個)，將 `units[0].b0_lu_enable` 設為 1 以啟用 LUN，將 `units[0].l4_num_alloc_units` 設為 1，並將 `units[0].b9_logical_block_size` 設為 0xC (代表 4KB)。依次呼叫 `push_write_config` 寫入這四個描述符 (Index 0-3) 並執行 `ExecuteCMD.send()`。
   - 預期結果：硬體必須正確解析這四個連續的配置描述符單元；Index 1, 2, 3 的 LUN 必須處於 Enabled 狀態，且每個 LUN 的邏輯區塊大小必須精確設定為 4KB (0xC)，分配單元數為 1；Index 3 的 `b2_conf_desc_continue` 必須為 0，標誌著配置描述符鏈結的結束，確保韌體不會誤讀後續記憶體內容。