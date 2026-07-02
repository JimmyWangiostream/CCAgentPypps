# Test Spec: VC-28 (11.d) Program Fail Selection New PB Failed Over N Times FW Stuck Test

## Verification Criterion (VC)
驗證在正常區域（Normal Area）發生連續寫入失敗且韌體嘗試選擇新替換區塊（New PB）失敗超過 N 次的情境下，韌體是否會進入死鎖（Stuck）狀態並觸發特定的韌體斷言（FW Assert）。具體驗證邏輯為：透過 Vendor Command 強制建立 L2 邏輯區塊及其前兩個預測替換區塊（Next Replacement Block）的 Program Fail 狀態，隨後執行寫入操作觸發寫入失敗流程。預期結果為韌體因無法找到可用的替換區塊而卡死，並產生特定的斷言編號 `0x204`，以此確認韌體在極端錯誤情境下的錯誤處理機制與狀態機行為。

## Test Case (TC) Checkpoints
1. [Case01_FW_Stuck_Assert_0x204_Check]：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 獲取當前開啟的 VB 資訊，並從回應中提取 L2 邏輯 VB 號碼（`L2_vb`）。
     2. 透過 Vendor Command `0x40D6` 查詢 CE=0, Plane=0 下的前兩個預測替換區塊號碼，分別記為 `next_replacement_block_1` 與 `next_replacement_block_2`。
     3. 建構 `PhysicalAddressInformation` 結構體，針對上述三個區塊（L2 VB, 1st Next PB, 2nd Next PB）設定相同的 Die/Plane/Page 資訊，並透過 Vendor Command `0xC012` 以 `fail_type=0` 強制注入 Program Fail 狀態，確保這三個區塊均無法用於寫入。
     4. 對 LUN 0 的 LBA 0 發起長度為 `WRITE_10_MAX_BLOCK_LEN` 的 Write10 寫入指令，並設定 `fua=1` 強制刷新。
     5. 發送指令並捕獲 `G_TIMEOUT_ALL` 異常，隨後呼叫 `api.get_fw_assert_number()` 讀取韌體斷言編號。
   - 預期結果：
     - 寫入指令必須觸發 `G_TIMEOUT_ALL` 異常，表示主機端等待韌體回應超時。
     - `api.get_fw_assert_number()` 回傳的值必須精確等於 `0x204`。
     - 此結果證明韌體在嘗試寫入時，因 L2 區塊及其預設的兩個替換區塊均標記為 Program Fail，導致無法選擇新的替換區塊（Selection New PB Failed），進而觸發韌體死鎖機制並產生斷言 `0x204`。