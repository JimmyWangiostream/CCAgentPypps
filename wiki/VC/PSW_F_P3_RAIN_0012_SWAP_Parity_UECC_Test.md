# Test Spec: UFS Rain Parity SWAP Block UECC Injection & POR Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Power-On Reset (POR) 後，針對 Rain Parity 架構中「SWAP Block」與「Host Block」的 UECC 錯誤處理機制：
1. **SWAP Block 預置錯誤**：在 POR 前，透過 `inject_UECC_in_swap` 函數在特定的 SWAP VB 的特定 Page 注入 UECC 錯誤。此步驟模擬韌體內部結構區塊的損壞。
2. **Host Block 錯誤注入**：在 POR 後，針對連續的三個 Host LBA 區塊（First, Second, Third PCA）注入 UECC 錯誤。
3. **讀取狀態驗證**：
   - 透過 Host Read10 命令讀取包含 Second PCA 的範圍，並進行 CRC 校驗，預期返回 UECC 狀態。
   - 透過 Direct Read 原始資料讀取 Second 與 Third PCA，預期返回 UECC 狀態。
   - 核心驗證點：確認韌體在 POR 後，對於 Host Block 的 UECC 錯誤是否正確報告給 Host（未自動修復或掩蓋），以及 SWAP Block 的預置錯誤是否影響後續的 Host 讀取行為或導致系統崩潰。

## Test Case (TC) Checkpoints
1. [Case01_SWAP_UECC_POR_Host_UECC_Read_Check]：
   - 動作：
     1. **環境初始化**：根據測試模式（TLC/SLC/WB）配置 LUN，清除所有資料。若為 WB 模式則啟用 Write Booster 標誌，否則清除。
     2. **資料寫入**：寫入超過 `rain_goup_cnt * 3` 個 Pageline 的資料至測試 LUN，確保 First, Second, Third PCA 存在。
     3. **SWAP Block 錯誤注入**：呼叫 `inject_UECC_in_swap`，該函數會計算對應的 SWAP VB 和 Pageline，遍歷 CE 與 Plane（跳過無效 Plane），在找到的第一個有效 CE/Plane 組合的 SWAP Page 注入 UECC 錯誤。
     4. **POR 觸發**：執行 `HW_RESET`（無 Power Down），模擬冷啟動。
     5. **Host Block 錯誤注入**：POR 完成後，針對 First, Second, Third PCA 分別注入 UECC 錯誤。
     6. **Host Read10 驗證**：從 First LBA 開始讀取長度為 `second_lba - first_lba` 的資料，並設定 CRC 比較（若寫入記錄存在）。發送命令並等待超時。
     7. **Direct Read 驗證**：對 Second PCA 和 Third PCA 執行 Direct Read Raw Data，預期狀態為 `project_api.ReadStatus.UECC`，並啟用 REH (Read Error Handling)。
   - 預期結果：
     - **Host Read10**：命令執行完成，狀態碼應反映讀取錯誤（UECC），CRC 校驗失敗或返回錯誤狀態，證明 Host Block 的 UECC 錯誤未被韌體自動修復並透明化給 Host。
     - **Direct Read**：Second 與 Third PCA 的讀取結果狀態必須嚴格等於 `project_api.ReadStatus.UECC`。
     - **系統穩定性**：儘管 SWAP Block 存在預置 UECC 且 Host Block 存在注入 UECC，韌體不應崩潰（Crash）或進入不可恢復狀態，證明 POR 後的韌體初始化流程能正確處理這些並存的錯誤標記。