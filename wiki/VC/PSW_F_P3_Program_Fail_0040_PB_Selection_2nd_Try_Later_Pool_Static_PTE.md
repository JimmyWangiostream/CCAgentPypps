# Test Spec: VC-36 (13.h) Program Fail Recovery & Read-Only Mode Enforcement

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生 Program Fail 且備用區塊（Replacement Pool）耗盡或失效時的錯誤處理機制：
1. **BBT 更新驗證**：確認當 L2 區塊因 Erase Fail 被標記為 Bad Block 時，韌體能正確更新 Bad Block Table (BBT)，並透過 Vendor Command (VU 405E) 反映 BB Count 增加及目標區塊進入 BBT。
2. **PTE 失效與 Read-Only 切換驗證**：確認當 PTE 區塊及其下一個備用區塊（Next Replacement Block）同時遭遇 Program Fail 時，韌體無法恢復 PTE 狀態，導致設備進入不可恢復的錯誤狀態。預期結果為設備進入 Read-Only 模式或觸發 FW Assert (0x203)，且 PTE VB 號碼不再變化，證明韌體已強制鎖定以保護數據完整性，防止進一步的寫入損壞。

## Test Case (TC) Checkpoints

1. [Case01_L2_EraseFail_BBT_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 Open VB (`L2_vb`)，透過 VU 40DC 獲取下一個 L2 VB (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始 BB Count (`BB_count`)。
     3. 透過 VU 40D6 獲取預測的下一個備用區塊 (`next_replacement_block_1`, `next_replacement_block_2`)，並讀取 FW 內部變數 `bbt.max_revoke_cnt` 與 `bbt.revoke_cnt`。
     4. 若 `bbt_revoke_cnt` 未達上限且備用區塊充足，則透過 VU C012 對 `L2_vb_next` 注入 Erase Fail (`fail_type=1`)。
     5. 執行連續 Write10 操作，直到 L2 VB 發生切換（證明 L2 區塊已失效並切換至新區塊）。
     6. 透過 VU 4013 獲取 BE Fail 狀態，並再次透過 VU 405E 獲取新的 BB 資訊。
     7. 計算新的 BBT 數據，並檢查目標區塊 (`target_data_L2`) 是否已包含在 BBT 中。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - BBT 數據中必須能找到包含 `target_data_L2` (CE, Plane, Block) 的條目。
     - 代表韌體在 L2 區塊發生 Erase Fail 後，正確地將其標記為 Bad Block 並更新 BBT，且設備仍能繼續運作（切換至新 L2 VB）。

2. [Case02_PTE_DoubleFail_Assert_0x203_Check]：
   - 動作：
     1. 重置測試環境，透過 VU 40C1 獲取當前 PTE VB (`PTE_vb`)，透過 VU 40DC 獲取下一個 PTE VB (`PTE_vb_next`)。
     2. 透過 VU 40D6 獲取預測的下一個 PTE 備用區塊 (`next_replacement_block`)。
     3. 透過 VU C012 同時對 `PTE_vb_next` 和 `next_replacement_block` 注入 Program Fail (`fail_type=0`, `block_info_list_count=2`)，模擬 PTE 及其備用區塊雙重失效。
     4. 執行隨機 Write10 操作，觸發寫入失敗。
     5. 捕獲 `G_TIMEOUT_ALL` 異常，並檢查 FW Assert 號碼是否為 `0x203`。
     6. 若 Assert 為 0x203，執行 HW_RESET 並重新初始化設備。
     7. 在寫入過程中，持續監控 PTE VB 號碼 (`PTE_vb_new`) 是否發生變化。
   - 預期結果：
     - 設備在觸發 Program Fail 後應進入非響應狀態，並觸發 FW Assert `0x203`（代表設備初始化後仍無響應，確認未進入正常的 Read-Only 恢復流程，而是進入保護性鎖定狀態）。
     - 執行 HW_RESET 後，設備應能重新進入 Unit Ready 狀態。
     - 在整個測試過程中，`PTE_vb_new` 必須始終等於初始的 `PTE_vb`，不得發生切換。
     - 代表當 PTE 及其備用區塊均失效時，韌體無法執行 PTE Reconstruction，強制進入 Read-Only 或 Assert 狀態以保護系統穩定性，且 PTE 狀態被鎖定。