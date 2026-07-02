# Test Spec: VC-32 (12.h) Program Fail with New PB Selection and Read-Only Mode Enforcement

## Verification Criterion (VC)
驗證韌體在「正常區域」發生 Program Fail 且成功選取新替換區塊（New PB）的情境下，硬體行為與韌體狀態機轉換：
1. **預備階段**：確認系統能正確預測替換區塊，並透過 Vendor Command `C012` 在目標 L2 VB 強制注入 Erase Fail，確保該區塊被標記為 Bad Block 並進入替換池邏輯。
2. **故障觸發階段**：在 L2 VB 切換後，針對新的 L2 VB 強制注入 Program Fail (`fail_type=0`)，並執行 Write10 指令。
3. **狀態檢查階段**：驗證韌體在遭遇 Program Fail 後，是否正確觸發 Assert 機制（預期 Assert Code `0x203`），並確認設備進入非唯讀的掛起狀態（Unresponsive），同時驗證 Bad Block Table (BBT) 已正確更新，包含新增的 Bad Block 計數及具體的物理地址資訊。

## Test Case (TC) Checkpoints

1. [PreProcess_EraseFail_Prediction_Check]：
   - 動作：
     1. 透過 Vendor Command `40C1` 讀取當前 L2 Open Logical VB (`L2_vb`)。
     2. 透過 Vendor Command `40DC` 讀取下一個預期的 L2 VB (`L2_vb_next`)。
     3. 透過 Vendor Command `405E` 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 Vendor Command `40D6` 查詢替換池預測區塊（`pool_type=1`, `next_n=5`），確認 `next_replacement_block_2` 不為 `0xFFFF`（表示替換池尚有空間或邏輯正常）。
     5. 透過 Vendor Command `C012` 針對 `L2_vb_next` 的 Block 0, Page 0 強制注入 Erase Fail (`fail_type=1`)。
     6. 執行連續 Write10 寫入，直到 `40C1` 返回的 L2 VB 發生改變，確保測試目標區塊已成為當前活躍的 L2 VB。
     7. 透過 Vendor Command `4013` 讀取 BE Fail 狀態。
     8. 再次透過 `405E` 讀取 Bad Block 資訊，計算 BBT 並驗證 `BB_count_new` 等於 `BB_count + 1`，且 BBT 數據中包含目標物理地址（CE=0, Plane=0, Block=`L2_vb_next`）。
   - 預期結果：
     - `BB_count` 必須增加 1，證明 Erase Fail 成功標記區塊。
     - BBT 查詢結果必須包含目標 Block 資訊，證明韌體已正確記錄該 Bad Block。
     - 此階段確保測試環境已準備好，目標 L2 VB 已因 Erase Fail 被標記，且系統邏輯已準備處理後續的 Program Fail 情境。

2. [Step1_ProgramFail_Assert_0x203_Check]：
   - 動作：
     1. 透過 Vendor Command `40C1` 獲取當前 L2 VB (`L2_vb`)。
     2. 透過 Vendor Command `C012` 針對當前 L2 VB 的 Block 0, Page 0 強制注入 Program Fail (`fail_type=0`)。
     3. 構造 Write10 指令（LUN=0, LBA=0, Length=Max, FUA=1）並發送。
     4. 捕獲 `G_TIMEOUT_ALL` 異常，表示設備在發送指令後無回應。
     5. 呼叫 `api.get_fw_assert_number()` 讀取韌體 Assert 代碼。
   - 預期結果：
     - 設備必須在 Write10 發送後進入無回應狀態（Timeout）。
     - `api.get_fw_assert_number()` 返回的值必須精確等於 `0x203`。
     - 此結果驗證韌體在遭遇 Program Fail 且嘗試選取新 PB 的過程中，觸發了特定的硬體/韌體錯誤處理機制（Assert 0x203），且根據 VC 描述，此狀態代表「Device remains unresponsive after initialization. Confirmed not in read-only mode」，即設備掛起但未進入唯讀保護模式，符合預期行為。