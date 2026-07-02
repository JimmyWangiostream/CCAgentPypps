# Test Spec: VC-15 (3.d) Erase Fail with Exhausted Replacement Blocks causing FW Stuck

## Verification Criterion (VC)
驗證在正常區域（Normal Area）發生連續寫入時，若當前 L2 VB 的下一個備用區塊（Next Replacement Block）連續兩次預測失敗（即 1st 和 2nd next replacement block 均被標記為 Erase Fail），韌體應觸發特定的韌體斷言（FW Assert 0x204）並進入掛起（Stuck）狀態。此測試旨在確認當韌體無法找到有效的備用區塊進行替換時，系統不會崩潰或進入非預期的錯誤循環，而是通過特定的 Assert 機制報告硬體資源耗盡的嚴重錯誤。

## Test Case (TC) Checkpoints
1. [Case01_Exhausted_Replacement_Blocks_FW_Stuck_Check]：
   - 動作：
     1. 透過 Vendor Command 40C1 讀取當前 L2 VB 號碼（L2_vb），並透過 40DC 讀取下一個開放的 L2 VB 號碼（L2_vb_next）。
     2. 透過 Vendor Command 40D6 預測並獲取接下來兩個備用區塊的地址：next_replacement_block_1 和 next_replacement_block_2。
     3. 透過 Vendor Command C012 強制注入 Erase Fail 錯誤，將以下三個區塊標記為失效：
        - 當前 L2 對應的下一個區塊 (L2_vb_next)
        - 第一個預測備用區塊 (next_replacement_block_1)
        - 第二個預測備用區塊 (next_replacement_block_2)
        錯誤類型設定為 fail_type=1。
     4. 從 LBA 0 開始執行連續的 Write10 命令（每次寫入 WRITE_10_MAX_BLOCK_LEN 長度），並設置 fua=1。
     5. 在寫入循環中，持續監控 L2 VB 是否發生變化。若 L2 VB 未變化，則繼續增加 LBA 並發送下一個寫入命令。
     6. 捕獲寫入命令的回應，預期會觸發 G_TIMEOUT_ALL 異常。
     7. 在異常發生後，檢查韌體 Assert 號碼是否為 0x204。
   - 預期結果：
     - 寫入操作最終會因韌體無法處理 Erase Fail 而超時（G_TIMEOUT_ALL）。
     - 韌體 Assert 號碼必須精確等於 0x204。
     - 這代表韌體在嘗試替換區塊時，發現連續的備用區塊均失效，導致無法完成寫入操作，從而觸發 0x204 斷言並進入掛起狀態，符合 VC-15 對於 Erase Fail 導致 FW Stuck 的驗證要求。