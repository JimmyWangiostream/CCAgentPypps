# Test Spec: VC-32 (12.h) Program Fail Selection New PB Succeed on First Try in Normal Area

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生 Program Fail 時的錯誤處理與狀態機轉換邏輯：
1. **預階段驗證 (Pre-stage)**：確認在 EM1 LUN 上觸發 Erase Fail 並寫入資料導致 L2 VB 切換後，BB Table (BBT) 能正確更新並包含該失效區塊，且預測替換區塊池（Replacement Pool）剩餘數量正確。
2. **核心驗證 (Step 1)**：針對 EM1 LUN 的當前 L2 VB 區塊注入 Program Fail (PF)，執行寫入操作時，韌體應觸發 Assert 0x203（表示設備進入非響應狀態但未進入強制唯讀模式），確認韌體在首次嘗試選擇新替換區塊（New PB）失敗後，能正確捕捉硬體錯誤並進入特定的 Assert 狀態，而非無限期掛起或錯誤地進入 ReadOnly 模式。

## Test Case (TC) Checkpoints
1. [PreStage_EF_L2VB_Change_BBT_Update_Check]：
   - 動作：
     1. 配置 LUN 0 為 Normal，LUN 1 為 EM1。
     2. 在 EM1 LUN (LUN 1) 寫入 4KB 資料以初始化。
     3. 執行 HW_RESET 並關閉 FW_DEBUG_MODE。
     4. 透過 Vendor Command (VC) 40C1 讀取當前 L2 Open Logical VB (L2_vb)，透過 VC 40DC 讀取下一個 L2 VB (L2_vb_next)。
     5. 透過 VC 405E 記錄初始 Bad Block Count (BB_count)。
     6. 透過 VC 40D6 讀取預測的替換區塊，確認池中有足夠區塊。
     7. 透過 VC C012 對 L2_vb_next 注入 Erase Fail (fail_type=1)。
     8. 在 Normal LUN (LUN 0) 連續寫入資料，直到 VC 40C1 返回的 L2_vb 發生跳變（從 L2_vb 變為 L2_vb_new），觸發 L2 VB 切換。
     9. 再次透過 VC 405E 讀取 BB_count_new 並計算 BBT。
   - 預期結果：
     - BB_count_new 必須等於 BB_count + 1。
     - BBT 中必須包含目標區塊資訊（CE=0, Plane=0, Block=L2_vb_next），代表 Erase Fail 已被正確標記為 Bad Block 並更新至韌體內部表單。

2. [Step1_PF_Assert_0x203_Check]：
   - 動作：
     1. 透過 VC 40C1 讀取 EM1 LUN 當前的 L2 VB (L2_vb)。
     2. 透過 VC C012 對該 L2_vb 區塊注入 Program Fail (fail_type=0)。
     3. 在 EM1 LUN (LUN 1) 執行 Write10 命令寫入 4KB 資料。
     4. 捕獲命令執行期間的異常狀態。
   - 預期結果：
     - Write10 命令應觸發 G_TIMEOUT_ALL 異常（設備無響應）。
     - 韌體 Assert 號碼必須為 0x203。
     - 這代表韌體在嘗試將資料寫入已標記為 Program Fail 的區塊，且未能成功選擇新的替換區塊（或選擇過程觸發特定硬體/韌體狀態）時，正確地觸發了 Assert 0x203，確認設備處於非唯讀的掛起狀態，符合 VC-32 對於 "succeed on the first try" 情境下錯誤邊界條件的驗證要求（註：根據代碼邏輯，此處驗證的是 PF 發生後的 Assert 行為，若預期是成功切換則代碼應無 Assert，但代碼明確檢查 Assert 0x203，故驗證目標為確認此特定錯誤路徑的 Assert 行為）。