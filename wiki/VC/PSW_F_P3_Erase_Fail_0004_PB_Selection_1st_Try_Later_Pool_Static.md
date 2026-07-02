# Test Spec: VC-9 (1.h) Erase Fail with New PB Selection and FW Assert Check

## Verification Criterion (VC)
驗證韌體在「選擇新替換區塊（New PB）成功」且「位於 Normal Area」的情境下，當觸發 Erase Fail (EF) 並執行連續寫入時，硬體行為與韌體狀態機轉換：
1. **BBT 更新驗證**：確認 Bad Block Table (BBT) 正確記錄被注入 EF 的 L2 VB 區塊，且 Bad Block Count (BB_count) 嚴格增加 1。
2. **VB 狀態鎖定驗證**：確認在寫入過程中，L2 Open Logical VB 號碼必須保持不變（代表韌體未自動切換 VB，而是嘗試修復或鎖定當前狀態）。
3. **FW Assert 機制驗證**：確認當連續寫入觸發 Erase Fail 且韌體無法即時恢復時，裝置進入非響應狀態，並觸發特定的韌體 Assert 錯誤碼 `0x203`（Device remains unresponsive after initialization），此為預期行為，代表韌體在嘗試強制 Read-Only 或修復失敗時進入的安全停滯狀態，而非系統崩潰。

## Test Case (TC) Checkpoints

1. [PreProcess_BBT_Initialization_Check]：
   - 動作：
     1. 透過 Vendor Command `VU 40C1` 讀取當前 L2 Open Logical VB (L2_vb)。
     2. 透過 Vendor Command `VU 40DC` 讀取下一個預期的 L2 VB (L2_vb_next)。
     3. 透過 Vendor Command `VU 405E` 讀取初始 Bad Block Count (BB_count) 及 BBT 資料。
     4. 透過 Vendor Command `VU 40D6` 讀取預測的下一個替換區塊（Pool Type 1, Shared for ICS/Static），確保剩餘可用替換區塊數量大於 1（檢查 `next_replacement_block_2 != 0xFFFF`）。
     5. 透過 Vendor Command `VU C012` 針對 `L2_vb_next` 的 Block 0, Plane 0 注入 Erase Fail (fail_type=1)。
     6. 從 LBA 0 開始執行連續 Write10 指令，每次寫入 `WRITE_10_MAX_BLOCK_LEN` 長度，並持續檢查 L2_vb 是否改變。若 L2_vb 未改變則繼續寫入，直到 L2_vb 改變或達到替換區塊耗盡條件。
     7. 寫入結束後，透過 `VU 4013` 讀取 BE Fail Status，並透過 `VU 405E` 再次讀取 BBT。
     8. 驗證新的 BB_count 是否等於 `BB_count + 1`，並驗證 BBT 中是否包含目標區塊 `target_data_L2` (CE=0, Plane=0, Block=L2_vb_next)。
   - 預期結果：
     - 初始替換區塊池充足（`next_replacement_block_2 != 0xFFFF`）。
     - 注入 EF 後，經過連續寫入觸發 VB 切換（在 pre_process 中預期 L2_vb 會改變以消耗舊 VB 或完成修復流程，具體取決於韌體實現，但此處重點在於驗證 BBT 更新）。
     - 最終 BB_count 必須精確增加 1。
     - BBT 資料中必須能找到與注入 EF 的區塊地址完全匹配的條目。

2. [Step1_FW_Assert_0x203_Check]：
   - 動作：
     1. 重置環境，重新獲取當前 L2_vb 及下一個 L2_vb_next。
     2. 針對 `L2_vb_next` (CE=0, Plane=0) 透過 `VU C012` 注入 Erase Fail (fail_type=1)。
     3. 從 LBA 0 開始執行連續 Write10 指令。
     4. 在每次 `ExecuteCMD.send` 時設置 `skip_response_check=True` 以捕獲底層硬體響應。
     5. 監控是否拋出 `G_TIMEOUT_ALL` 異常。
     6. 若拋出異常，立即呼叫 `api.get_fw_assert_number()` 獲取韌體 Assert 編號。
     7. 同時監控 L2_vb 狀態，確認在寫入過程中 L2_vb_new 必須等於初始 L2_vb（即 VB 號碼未發生改變，代表韌體卡在當前區塊的修復/錯誤處理循環中）。
   - 預期結果：
     - 寫入操作最終導致裝置超時（Timeout），拋出 `G_TIMEOUT_ALL`。
     - 韌體 Assert 編號必須精確等於 `0x203`。
     - 在超時發生前，L2_vb 號碼必須保持不變（若 L2_vb 改變則視為異常，因為這意味著韌體跳過了錯誤處理流程）。
     - 此結果驗證了韌體在面對無法即時修復的 Erase Fail 且 VB 未切換時，會進入 `0x203` 定義的非響應狀態，符合 VC 中關於「FW should be update BB table and force read only mode」的錯誤處理路徑驗證（此處 0x203 為該路徑下的具體硬體/韌體停滯標記）。