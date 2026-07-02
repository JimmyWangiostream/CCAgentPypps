# Test Spec: VC-36 (13.h) Program Fail with Exhausted Replacement Blocks and FW Assert Handling

## Verification Criterion (VC)
驗證在正常區域（Normal Area）發生 Program Fail 且替換區塊池（Replacement Pool）耗盡時的韌體行為：
1. **預處理階段**：確認當 `bbt_revoke_cnt` 達到最大值 `bbtmax_revoke_cnt` 且預測替換區塊剩餘數量不足時，系統能正確識別並進入測試情境。
2. **主測試階段 (LIST PF)**：針對 LIST VB 及其下一個預測替換區塊同時注入 Program Fail，模擬替換資源完全耗盡的情境。
3. **異常恢復機制**：驗證在替換區塊耗盡且持續寫入導致韌體進入錯誤狀態時，設備應觸發 FW Assert `0x203`（Device remains unresponsive after initialization），並確認此時設備**未**進入強制唯讀模式（Read-Only Mode），而是保持無回應狀態等待主機重啟。
4. **BBT 一致性檢查**：在預處理階段確認 Bad Block Table (BBT) 計數正確增加，且目標區塊已正確標記為壞塊。

## Test Case (TC) Checkpoints

1. [PreProcess_BBT_Exhaustion_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 Open VB 號碼，透過 VU 40DC 獲取下一個 L2 Open VB 號碼。
     2. 透過 VU 405E 獲取當前 Bad Block Count (`BB_count`)。
     3. 透過 VU 40D6 獲取預測的接下來 2 個替換區塊號碼 (`next_replacement_block_1`, `next_replacement_block_2`)。
     4. 讀取韌體變數 `gUfsApiStruct.ftl->bbt.max_revoke_cnt` 與 `gUfsApiStruct.ftl->bbt.revoke_cnt`。
     5. 若 `revoke_cnt == max_revoke_cnt` 且 `next_replacement_block_2 != 0xFFFF`，則跳出循環；否則，透過 VU C012 對 `L2_vb_next` 注入 Program Fail (`fail_type=1`)，並執行連續 Write10 直到 L2 VB 切換，重複此過程直到滿足跳出條件。
     6. 最後透過 VU 4013 獲取 BE Fail 狀態，並透過 VU 405E 再次獲取 BBT 數據。
   - 預期結果：
     - 循環結束後，新的 `BB_count_new` 必須等於 `BB_count + 1`。
     - 計算後的 BBT 數據 (`BB_data_new`) 中必須包含目標區塊 (`target_data_L2`)，代表壞塊標記已正確更新。
     - 系統進入主測試階段時，確保 BBT 已處於替換資源即將耗盡或已耗盡的狀態。

2. [LIST_PF_Exhaustion_Assert_0x203_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 LIST VB (`LIST_vb`)，透過 VU 40DC 獲取下一個 LIST VB (`LIST_vb_next`)。
     2. 透過 VU 40D6 獲取預測的下一個替換區塊號碼 (`next_replacement_block`)。
     3. 透過 VU C012 同時對 `LIST_vb_next` 與 `next_replacement_block` 注入 Program Fail (`fail_type=0`, `block_info_list_count=2`)，模擬 LIST 區塊及其替換池均失效。
     4. 進入隨機寫入循環：隨機生成 LBA 並執行 Write10。
     5. 捕獲 `G_TIMEOUT_ALL` 異常。
     6. 若捕獲異常，檢查韌體 Assert 號碼是否為 `0x203`。
     7. 若 Assert 為 `0x203`，執行 `HW_RESET` 並斷電重啟 (`powerdown=True`)，結束測試。
     8. 若未捕獲異常或 Assert 非 `0x203`，檢查 `LIST_vb` 是否發生變化。
   - 預期結果：
     - 當替換區塊耗盡且發生 Program Fail 時，設備應進入無回應狀態並觸發 FW Assert `0x203`。
     - 在 Assert `0x203` 發生時，`LIST_vb` 號碼必須**保持不變**（代表韌體未嘗試切換 VB，因為無可用替換區塊）。
     - 設備狀態應為「未進入唯讀模式」，而是處於 Assert 掛起狀態，等待主機進行 HW_RESET。
     - 若 Assert 號碼不是 `0x203` 或 `LIST_vb` 發生變化，則判定為 `SIGHTING_RESPONSE_UNEXPECTED`。