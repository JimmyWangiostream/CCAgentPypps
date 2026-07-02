# Test Spec: UFS PSA (Pre-Soldering Area) Lifecycle & Interruption Recovery Test

## Verification Criterion (VC)
驗證 UFS 裝置在 PSA (Pre-Soldering Area) 機制下的完整生命週期與異常中斷恢復能力：
1. **狀態機邏輯驗證**：確認在 `PRE_SOLDERING` 狀態下，當寫入數據量超過設定的 `dPSADataSize` 時，裝置必須拒絕寫入並返回 `TARGET_FAILURE`；當嘗試進入 `LOADING_COMPLETE` 但數據已溢出時，必須返回 `GENERAL_FAILURE`。
2. **中斷與恢復機制**：驗證在 `PRE_SOLDERING` 狀態下，透過寫入 `OFF` 屬性強制中斷 PSA 流程，韌體內部狀態 (`debug_info.payload[469]`) 必須正確切換為 `Interrupt (0x01)`，且不會進入錯誤狀態。
3. **電源循環與 BKOPS 觸發**：驗證在 PSA 數據寫入過程中，透過 `SSU Power Down/Active` 配合 VCC 斷電重啟，裝置能正確維持 PSA 狀態，並在重啟後透過隨機寫入觸發 `BG_OP_STATUS` 非零狀態，確保後台操作正常執行。
4. **Post-Reflow 遷移完整性**：驗證在 `LOADING_COMPLETE` 狀態下執行 HW_RESET 後，裝置進入 `SOLDERED` 狀態並觸發 `Post-Reflow` 遷移。在此遷移過程中（透過 Vendor Command 0x405C 監控進度），若遭遇 `SSU Power Down` 或大量隨機寫入干擾，遷移進度不得倒退，且最終必須達到 100% 完成，內部狀態變更為 `Relocate Complete (0x03)`，且最終數據比對無誤。

## Test Case (TC) Checkpoints

1. **[Case01_PSA_Overflow_Rejection_Check]**：
   - 動作：配置 2 個 Normal LUN 與 2 個 EM1 LUN，設定 `dPSADataSize` 為 16GB。對 PSA Sensitive LUN (LUN 0, 1) 寫入 15GB 數據。接著將 `dPSADataSize` 修改為 8GB，並嘗試對 LUN 0 寫入 16MB 數據。隨後嘗試將 `bPSAState` 寫入 `LOADING_COMPLETE`。
   - 預期結果：當 `dPSADataSize` 設為 8GB 時，寫入 16MB 數據應返回 `TARGET_FAILURE` (0x01)；嘗試設置 `LOADING_COMPLETE` 應返回 `GENERAL_FAILURE` (0xFF)。這證明韌體嚴格執行 PSA 容量限制，防止數據溢出。

2. **[Case02_PSA_Interruption_State_Check]**：
   - 動作：在 `PRE_SOLDERING` 狀態下，將 `bPSAState` 寫入 `OFF` 以中斷 PSA 流程。讀取韌體 Debug Info 中的 `payload[469]` 欄位。
   - 預期結果：`payload[469]` 的數值必須等於 `0x01` (Interrupt)。這代表韌體能正確處理 PSA 流程的中斷請求，並停留在中斷狀態，而非崩潰或進入未定義狀態。

3. **[Case03_PSA_PowerCycle_BKOPS_Trigger_Check]**：
   - 動作：在 PSA 數據寫入過程中（寫入一半後），執行 `issue_SSU_powerdown_active` (SSU Power Down + VCC Off + VCC On + SSU Active)。重啟後，透過隨機寫入觸發 BKOPS，並輪詢讀取 `AttributeIDN.BG_OP_STATUS` 直到其值不等於 `0x00`。
   - 預期結果：裝置在 VCC 斷電重啟後能正常恢復並接受寫入指令；`BG_OP_STATUS` 最終必須非零，證明後台操作 (BKOPS) 在 PSA 數據遷移期間能被正確觸發與執行，未因 PSA 狀態而阻塞。

4. **[Case04_PSA_PostReflow_Interruption_Robustness_Check]**：
   - 動作：將 `bPSAState` 設為 `LOADING_COMPLETE`，執行 HW_RESET 進入 `SOLDERED` 狀態並觸發 Post-Reflow。在 Post-Reflow 進度達到 30% 時，執行 `issue_SSU_powerdown_active`；在進度達到 60% 時，執行 2GB 隨機寫入干擾。持續監控 Vendor Command 0x405C 返回的 `PercentageForSLCPSAblocks`。
   - 預期結果：Post-Reflow 進度必須單調遞增，不得出現倒退（例如從 60% 回到 50%）。最終進度必須達到 `100`。這驗證了韌體在電源循環與 I/O 干擾下的數據遷移原子性與恢復機制。

5. **[Case05_PSA_Final_State_Data_Integrity_Check]**：
   - 動作：等待 Post-Reflow 進度達到 100% 後，讀取 `bPSAState` 屬性與 `debug_info.payload[469]`。隨後執行 `api.read_compare` 比對所有寫入記錄。
   - 預期結果：
     1. `bPSAState` 必須為 `SOLDERED`。
     2. `payload[469]` 必須為 `0x03` (Relocate Complete)。
     3. 數據比對必須全部通過，無任何 ECC 錯誤或數據損壞。這證明 PSA 數據已完整、正確地從預留區遷移至正常儲存空間。