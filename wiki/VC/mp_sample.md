# Test Spec: UFS Link Initialization and Basic Write Verification

## Verification Criterion (VC)
驗證 UFS 裝置在韌體初始化後，Link 能否成功建立於指定的最高 HS Gear 模式，並確認 Host 端發送的基本 Write 指令（LBA 0, Length 1）能否被裝置正確接收並處理。此測試旨在確認 PHY 層鏈路訓練（Link Training）與 Block 層基本 I/O 路徑的基礎连通性，排除因 Link 狀態異常或初始配置錯誤導致的通訊失敗。

## Test Case (TC) Checkpoints
1. [Link_Training_and_Basic_Write_Check]：
   - 動作：
     1. 執行 `api.MP().execute()` 初始化多處理器或相關硬體模組。
     2. 呼叫 `api.first_init_to_max_hs_gear`，根據 `_param.current_speed` 中的 `link_startup_mode` 與 `refclk` 參數，強制 UFS Link 啟動並鎖定至最高速度的 HS Gear（例如 HS-Gear4 或 HS-Gear5，視硬體支援而定）。
     3. 透過 `ExecuteCMD.Write10()` 建構一個 SCSI WRITE(10) 指令，設定目標 LUN 為 0，起始 LBA 為 0，傳輸長度為 1 個邏輯區塊（通常為 512 Bytes 或 4KB，視 LBP 設定），並設定 FUA (Force Unit Access) 為 1，確保資料直接寫入非揮發性記憶體而非快取。
     4. 將指令排入佇列並透過 `ExecuteCMD.send()` 發送至 UFS 裝置。
   - 預期結果：
     1. UFS Link 必須成功建立，且 Link 狀態寄存器顯示為 Active 狀態，Link 速度符合指定的 Max HS Gear。
     2. `ExecuteCMD.send()` 必須返回成功狀態碼（Status OK, 0x00），表示裝置已正確解碼並接受該 Write 指令。
     3. 若 Link 訓練失敗或指令回應錯誤狀態（如 ILLEGAL REQUEST 或 UNIT ATTENTION），則測試失敗，代表 Link 初始化配置或基本 I/O 路徑存在硬體/韌體缺陷。