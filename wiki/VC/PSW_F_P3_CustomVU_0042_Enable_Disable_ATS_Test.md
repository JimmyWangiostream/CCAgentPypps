# Test Spec: UFS Auto-Stop Timer (AST) State Machine & Vendor Command Validation

## Verification Criterion (VC)
驗證 UFS 裝置的 Auto-Stop Timer (AST) 計時器機制及其透過 Vendor Command (D088) 的控制邏輯：
1. **基礎計時行為驗證**：確認在預設啟用狀態下，AST 計時器（位於 Smart Info 0x4A8 偏移處）隨時間流逝正確遞增。
2. **禁用功能驗證**：確認透過 Vendor Command D088 發送 Payload[12]=0 禁用 AST 後，計時器停止遞增；重新啟用（Payload[12]=1）後，計時器恢復遞增。
3. **異常/預設狀態驗證**：若初始狀態未遞增（可能預設禁用或硬體異常），則執行反向測試：先強制啟用 AST，確認計時器遞增；再強制禁用，確認計時器停止。此分支確保韌體對 D088 命令的響應邏輯在兩種初始狀態下均正確。

## Test Case (TC) Checkpoints
1. [AST_Increment_Initial_Check]：
   - 動作：讀取 Smart Info 結構中偏移量 0x4A8 至 0x4B0 的 8 位元組資料，解析為 Little-Endian 整數 `backup_ats_times`。隨後進入 Idle 狀態 15 秒。再次讀取同一偏移量資料得到 `get_ats_times`。
   - 預期結果：若 `get_ats_times > backup_ats_times`，代表 AST 預設為啟用狀態，進入 [AST_Disable_Then_Enable_Check] 流程；若 `get_ats_times <= backup_ats_times`，代表 AST 預設為禁用或計時器未運行，進入 [AST_Enable_Then_Disable_Check] 流程。

2. [AST_Disable_Then_Enable_Check]：
   - 動作：
     a. 記錄當前計時器值 `backup_ats_times`。
     b. 發送 Vendor Command D088，設定 Payload[12] 為 0x00（禁用 Auto Standby Timer）。
     c. 再次讀取 Smart Info 0x4A8 得到 `backup_ats_times`（確保命令生效後的基準值）。
     d. Idle 15 秒。
     e. 讀取 Smart Info 0x4A8 得到 `get_ats_times`。
     f. 檢查計時器是否未增加：若 `get_ats_times > backup_ats_times`，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     g. 發送 Vendor Command D088，設定 Payload[12] 為 0x01（重新啟用 Auto Standby Timer）。
   - 預期結果：禁用 AST 期間，Smart Info 0x4A8 的計時器數值必須保持不變（等於 `backup_ats_times`），證明 D088 禁用命令成功凍結了硬體計時器；重新啟用後測試結束，代表韌體能正確響應 D088 的開關控制。

3. [AST_Enable_Then_Disable_Check]：
   - 動作：
     a. 發送 Vendor Command D088，設定 Payload[12] 為 0x01（強制啟用 Auto Standby Timer）。
     b. 記錄當前計時器值 `backup_ats_times`。
     c. Idle 15 秒。
     d. 讀取 Smart Info 0x4A8 得到 `get_ats_times`。
     e. 檢查計時器是否增加：若 `get_ats_times <= backup_ats_times`，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     f. 發送 Vendor Command D088，設定 Payload[12] 為 0x00（強制禁用 Auto Standby Timer）。
   - 預期結果：啟用 AST 期間，Smart Info 0x4A8 的計時器數值必須嚴格大於 `backup_ats_times`，證明計時器機制正常運作；禁用命令發送後測試結束，代表韌體能正確處理從禁用到啟用的狀態切換。