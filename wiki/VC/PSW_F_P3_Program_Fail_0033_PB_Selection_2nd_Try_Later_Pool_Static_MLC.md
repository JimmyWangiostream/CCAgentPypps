# Test Spec: VC-57 (13.h) Program Fail with Replacement Block Exhaustion & Assert Check

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生寫入失敗（Program Fail）且替換區塊池（Replacement Pool）枯竭時的硬體行為與韌體保護機制：
1. **替換區塊枯竭預警**：透過 VU 40D6 確認預測的下一個替換區塊（Next Replacement Block）為 0xFFFF 或數量不足，且 BBT revoke 計數器達到最大值，代表系統已無可用替換資源。
2. **雙重寫入失敗注入**：針對當前 L2 VB 的特定邏輯頁面（Logical Page）以及其預定的下一個替換區塊（Next Replacement Block）同時注入 Program Fail 錯誤（fail_type=3），模擬寫入路徑完全阻塞的情境。
3. **韌體 Assert 行為檢查**：在執行 Write10 命令觸發上述雙重失敗後，裝置應進入非響應狀態並觸發韌體 Assert，預期 Assert 編號為 `0x203`。此狀態確認韌體在無法修復錯誤且無替換資源時，正確地停止了寫入操作並進入保護模式（非 Read-Only 模式，而是 Assert 掛起），防止資料進一步損壞。

## Test Case (TC) Checkpoints

1. [Case01_Replacement_Pool_Exhaustion_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 VB (`L2_vb`) 及透過 VU 40DC 獲取下一個 L2 VB (`L2_vb_next`)。
     2. 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 VU 40D6 獲取預測的接下來 2 個替換區塊 (`next_replacement_block_1`, `next_replacement_block_2`)。
     4. 讀取韌體內部變數 `gUfsApiStruct.ftl->bbt.max_revoke_cnt` 與 `gUfsApiStruct.ftl->bbt.revoke_cnt`。
     5. 若 `revoke_cnt == max_revoke_cnt` 且 `next_replacement_block_2 != 0xFFFF`，則透過 VU C012 對 `L2_vb_next` 注入 Erase Fail (fail_type=1)，並持續寫入直到 L2 VB 切換，重複此循環直到 `next_replacement_block_2 == 0xFFFF` 或 revoke 計數達上限，確保替換池枯竭。
     6. 進入 Step1 邏輯，獲取當前 L2 VB 的 `first_empty_physical_page`，並根據頁區規則（Region Max WL）將其轉換為對應的 `logical_page`。
     7. 透過 VU 40D6 獲取下一個替換區塊 (`next_replacement_block`)。
     8. 透過 VU C012 注入雙重 Program Fail：
        - Block 0: 當前 L2 VB 的指定 `logical_page`。
        - Block 1: 下一個替換區塊 (`next_replacement_block`) 的 Page 0。
        - 設定 `fail_type=3` 且 `block_info_list_count=2`。
     9. 執行 Write10 命令寫入 1 LBA 資料。
   - 預期結果：
     - 韌體應捕捉到寫入超時或異常，並觸發 Assert。
     - 呼叫 `api.get_fw_assert_number()` 必須返回 `0x203`。
     - 這代表韌體在替換區塊池枯竭且當前區塊與替換區塊均寫入失敗時，正確執行了 Assert 機制，確認裝置處於非正常運作但受保護的狀態。

2. [Case02_BBT_Update_Verification]：
   - 動作：
     1. 在 Case01 的循環過程中，每次注入 Erase Fail 後，透過 VU 4013 獲取 BE Fail 狀態。
     2. 透過 VU 405E 獲取新的 Bad Block 資訊，並計算 BBT 數據。
     3. 驗證新的 Bad Block 計數 (`BB_count_new`) 是否等於舊計數加 1 (`BB_count + 1`)。
     4. 驗證 BBT 數據中是否包含目標區塊資訊 (`target_data_L2`)，即 Die 0, Plane 0, Block `L2_vb_next`。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`。
     - BBT 查詢結果中必須找到匹配目標區塊的條目，證明韌體正確更新了 Bad Block Table 以反映注入的錯誤區塊。

3. [Case03_MLC_Page_Wear_Leveling_Check]：
   - 動作：
     1. 在 `pre_process` 的後期階段，持續寫入 16 Bytes 資料直到 `first_empty_physical_page` 達到 1620。
     2. 驗證物理頁到邏輯頁的轉換邏輯：
        - 當 `physical_page < 1620` 時，`logical_page = physical_page // 3`。
        - 當 `1620 <= physical_page < 1652` 時，`logical_page = (physical_page - 1620) // 2 + 540`。
        - 當 `1652 <= physical_page < 3308` 時，`logical_page = (physical_page - 1652) // 3 + 556`。
        - 當 `3308 <= physical_page < 3312` 時，`logical_page = (physical_page - 3308) // 1 + 1108`。
   - 預期結果：
     - 物理頁與邏輯頁的映射關係必須嚴格符合上述分區規則，確保在後續的 Program Fail 注入中，目標邏輯頁面計算正確，從而精確命中預期寫入失敗的硬體位置。