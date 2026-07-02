# Test Spec: PSW_F_P3_PSA_0006 PSA State Across H8 Test

## Verification Criterion (VC)
驗證 UFS 裝置在進入並退出 Host-Initiated Hibernate (H8) 低功耗狀態後，Production-State-Awareness (PSA) 的韌體狀態與配置數據是否完整保留：Case 01 確認在啟用 PSA (dPSADataSize 設為最大值)、寫入 PSA 區域資料並設定狀態為 PRE_SOLDERING 後，執行 H8 進入/退出循環，讀回 dPSADataSize 必須與寫入前一致，證明非易失性狀態在 H8 期間未被清除；Case 02 為控制組，確認關閉 PSA (dPSADataSize=0, PSAState=OFF) 後，系統能正確執行清理程序並維持在 OFF 狀態，確保狀態機邏輯的完整性。

## Test Case (TC) Checkpoints
1. [Case01_H8_Preservation_Check]：
   - 動作：
     1. 讀取 Device Descriptor 中的 `l37_psa_max_data_size` 欄位，獲取 PSA 支援的最大數據大小（單位為 4 KiB）。
     2. 透過 `WriteAttribute` 將 `AttributeIDN.PSA_DATA_SIZE` 寫入上述最大值，啟用 PSA 功能。
     3. 執行 `Unmap` 命令清除 LUN0 和 LUN1 的邏輯區塊映射，確保 PSA 區域可用。
     4. 透過 `WriteAttribute` 將 `AttributeIDN.PSA_STATE` 設定為 `PRE_SOLDERING`，標記 PSA 正在載入中。
     5. 針對 LUN0 從 LBA 0 開始，寫入佔 PSA 區域 10% 容量的固定模式資料（Pattern Mode: HW_FIX），以填充 PSA 數據區。
     6. 執行 `CmdSeqHibernate` 序列，設定 `hibernate_enter=1`, `hibernate_exit=1`, `loopcount=1`, `delayafterenter=1000` ms，觸發裝置進入 H8 狀態並停留 1 秒後自動退出。
     7. H8 退出後，立即透過 `ReadAttribute` 讀取 `AttributeIDN.PSA_DATA_SIZE` 的當前值。
   - 預期結果：讀回之 `dPSADataSize` 數值必須嚴格等於步驟 2 中寫入的最大值（即 `l37_psa_max_data_size`）。若數值改變，則代表 H8 狀態轉換導致 PSA 配置數據丟失，測試失敗。此結果證明韌體在 H8 低功耗循環中正確保留了 PSA 的數據大小配置。

2. [Case02_Cleanup_Verification_Check]：
   - 動作：
     1. 在 H8 測試完成後，透過 `WriteAttribute` 將 `AttributeIDN.PSA_DATA_SIZE` 寫入 0，嘗試關閉 PSA。
     2. 透過 `WriteAttribute` 將 `AttributeIDN.PSA_STATE` 寫入 `OFF` (對應整數值)。
     3. 執行 `ReadAttribute` 讀取 `AttributeIDN.PSA_DATA_SIZE` 確認其值。
     4. 執行 `ReadAttribute` 讀取 `AttributeIDN.PSA_STATE` 確認其狀態。
   - 預期結果：
     1. `dPSADataSize` 讀回值必須等於 0。
     2. `bPSAState` 讀回值必須等於 `api.PSAState.OFF` 的整數表示。
     此結果證明韌體能正確響應 PSA 禁用指令，並維持在預期的初始非活動狀態，無殘留狀態錯誤。