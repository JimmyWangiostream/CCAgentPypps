# Test Spec: VC-36 (13.h) Program Fail with Replacement Pool Exhaustion and FW Assert Handling

## Verification Criterion (VC)
驗證在正常區域（Normal Area）進行寫入操作時，當備用區塊池（Replacement Pool）即將耗盡（剩餘預測區塊少於2個）的情境下，系統對連續程式失敗（Program Fail）的處理機制：
1. **BBT 更新與只讀模式觸發**：確認當 L2 VB 區塊因程式失敗被標記為 Bad Block 後，BBT（Bad Block Table）計數器正確增加，且該區塊被正確記錄在 BBT 中。
2. **L1 VB 切換與雙重注入**：確認 L1 VB 切換後，針對新的 L1 VB 及其下一個預測備用區塊同時注入程式失敗，模擬備用區塊池完全耗盡且無可用替換區塊的極端情況。
3. **FW Assert 0x203 與 HW_RESET 恢復**：確認在備用區塊耗盡且持續發生程式失敗時，韌體不會進入死鎖或錯誤的只讀模式，而是觸發特定的韌體斷言（Assert 0x203），並透過 HW_RESET + Power Down 流程恢復設備至 Unit Ready 狀態，驗證韌體在資源枯竭時的崩潰恢復機制。

## Test Case (TC) Checkpoints

1. [PreProcess_BBT_Initialization_and_L2_PF]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 VB (`L2_vb`)，透過 VU 40DC 獲取下一個 L2 VB (`L2_vb_next`)。
     2. 透過 VU 405E 獲取初始 Bad Block 計數 (`BB_count`)。
     3. 透過 VU 40D6 獲取預測的接下來 2 個備用區塊 (`next_replacement_block_1`, `next_replacement_block_2`)，並讀取 FW 內部變數 `bbt.max_revoke_cnt` 與 `bbt.revoke_cnt`。
     4. 若 `bbt_revoke_cnt` 已等於 `bbtmax_revoke_cnt` 且 `next_replacement_block_2` 不為 0xFFFF，則跳出循環；否則，透過 VU C012 對 `L2_vb_next` 注入程式失敗 (`fail_type=1`)。
     5. 執行順序寫入（Write10, LUN 0, LBA 0, 長度最大），直到讀取 VU 40C1 發現 `L2_vb` 發生改變，確認 L2 VB 已切換。
     6. 透過 VU 4013 獲取 BE 失敗狀態，並透過 VU 405E 獲取新的 BBT 數據。
   - 預期結果：
     - 新的 Bad Block 計數 `BB_count_new` 必須等於 `BB_count + 1`。
     - 新的 BBT 數據中必須包含目標區塊資訊 `target_data_L2` (CE:0, Plane:0, Block:`L2_vb_next`)，確認 L2 VB 區塊已被正確標記為 Bad Block 並記錄在 BBT 中。
     - 此循環持續執行，直到 FW 預測的備用區塊池僅剩最後兩個區塊（即 `next_replacement_block_2` 為 0xFFFF 或 revoke 計數滿），為後續的極端測試做準備。

2. [Step1_L1_VB_Switch_and_Dual_Block_PF_Injection]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L1 VB (`L1_vb`)，透過 VU 40DC 獲取下一個 L1 VB (`L1_vb_next`)。
     2. 透過 VU 40D6 獲取下一個預測備用區塊 (`next_replacement_block`)。
     3. 透過 VU C012 同時對兩個區塊注入程式失敗：
        - 目標 1: `L1_vb_next` (新的 L1 VB)。
        - 目標 2: `next_replacement_block` (預測的備用區塊)。
        - 設定 `fail_type=0` 且 `block_info_list_count=2`。
     4. 進入隨機寫入循環（Write10, LUN 0, 長度 16 Bytes, LBA 隨機），持續觸發程式操作。
   - 預期結果：
     - 由於 L1 VB 及其備用區塊均被注入失敗，且備用池已耗盡，韌體應無法正常完成寫入操作，導致設備無響應或觸發韌體異常。

3. [Step1_FW_Assert_0x203_and_HW_Reset_Recovery]：
   - 動作：
     1. 在隨機寫入循環中，捕獲 `G_TIMEOUT_ALL` 異常（表示設備無響應）。
     2. 檢查韌體斷言號碼 `api.get_fw_assert_number()`。
     3. 若斷言號碼為 `0x203`：
        - 清除命令隊列 `ExecuteCMD.clear()`。
        - 執行 `api.init_tester_to_unit_ready`，設定 `resetmode=HW_RESET` 且 `powerdown=True`，進行硬體重啟與電源循環。
        - 結束測試流程 (`return`)。
     4. 若未觸發斷言或斷言號碼非 0x203，則嘗試再次讀取 VU 40C1 獲取 L1 VB。
        - 若 L1 VB 發生改變 (`L1_vb_new != L1_vb`)，拋出 `SIGHTING_RESPONSE_UNEXPECTED` 錯誤（因為在雙重 PF 注入下，L1 VB 不應正常切換）。
        - 若再次超時且斷言非 0x203，同樣拋出錯誤。
   - 預期結果：
     - 設備必須觸發韌體斷言 `0x203`，該斷言代碼對應 "Device remains unresponsive after initialization. Confirmed not in read-only mode."，證明韌體在備用區塊完全耗盡且無法恢復時，選擇了崩潰斷言而非進入靜默的只讀模式。
     - 透過 HW_RESET 與 Power Down 後，設備必須成功恢復至 Unit Ready 狀態，驗證韌體在極端錯誤狀態下的可恢復性。