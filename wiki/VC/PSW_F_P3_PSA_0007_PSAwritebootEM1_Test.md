# Test Spec: PSW_F_P3_PSA_0006 PSA State Across H8 Test

## Verification Criterion (VC)
驗證 UFS 裝置在進入 Host-Initiated Hibernate (H8) 狀態前後，Production-State-Awareness (PSA) 相關屬性（Attribute）的持久性與狀態一致性：Case 01 確認在啟用 PSA（寫入 `dPSADataSize` 為最大值）並設定狀態為 `PRE_SOLDERING` 後，透過 H8 進入/離開循環（包含 1000ms 停留時間），`dPSADataSize` 的數值必須保持不變，證明 PSA 配置數據在低功耗狀態下未丟失；Case 02 為控制組，確認 PSA 禁用流程（寫入 `dPSADataSize=0` 且 `bPSAState=OFF`）後，讀回屬性值必須嚴格等於 0 與 OFF 狀態碼，驗證韌體能正確執行 PSA 資源清理與狀態重置。

## Test Case (TC) Checkpoints
1. [Case01_H8_PSA_Persistence_Check]：
   - 動作：
     1. 讀取 Device Descriptor 中的 `l37_psa_max_data_size` 欄位，獲取 PSA 支援的最大數據大小（單位為 4 KiB）。
     2. 透過 `WriteAttribute` 將 `AttributeIDN.PSA_DATA_SIZE` 寫入上述最大值，啟用 PSA 功能。
     3. 透過 `WriteAttribute` 將 `AttributeIDN.PSA_STATE` 寫入 `api.PSAState.PRE_SOLDERING`，允許後續寫入操作進入 PSA 區域。
     4. 針對 LUN0，從 LBA 0 開始，以 `HW_FIX` 模式寫入填充資料，填充量為 PSA 最大容量的 10%（由 `PSA_FILL_PERCENT` 控制），確保 PSA 區域有實際數據。
     5. 執行 `CmdSeqHibernate` 命令，設定 `hibernate_enter=1`, `hibernate_exit=1`, `loopcount=1`, `delayafterenter=1000` ms，觸發裝置進入 H8 狀態並停留 1 秒後自動退出。
     6. H8 退出後，立即透過 `ReadAttribute` 讀取 `AttributeIDN.PSA_DATA_SIZE` 的當前值。
   - 預期結果：讀回之 `dPSADataSize` 數值必須嚴格等於步驟 2 中寫入的最大值（`l37_psa_max_data_size`）。若數值發生改變（例如歸零或變為其他值），則判定為 PSA 狀態在 H8 循環中丟失，測試失敗。

2. [Case02_PSA_Disable_Cleanup_Check]：
   - 動作：
     1. 在 Case 01 完成後，透過 `WriteAttribute` 將 `AttributeIDN.PSA_DATA_SIZE` 寫入 0，嘗試禁用 PSA。
     2. 透過 `WriteAttribute` 將 `AttributeIDN.PSA_STATE` 寫入 `api.PSAState.OFF`，明確標記 PSA 狀態為關閉。
     3. 執行 `Send` 命令確保命令隊列清空並完成寫入。
     4. 透過 `ReadAttribute` 分別讀取 `AttributeIDN.PSA_DATA_SIZE` 與 `AttributeIDN.PSA_STATE` 的最終狀態。
   - 預期結果：
     - `dPSADataSize` 讀回值必須嚴格等於 0。
     - `bPSAState` 讀回值必須嚴格等於 `int(api.PSAState.OFF)`（通常為 0 或對應的枚舉整數值）。
     - 若任一屬性值不符合預期，代表韌體未能正確執行 PSA 資源釋放或狀態機重置，測試失敗。