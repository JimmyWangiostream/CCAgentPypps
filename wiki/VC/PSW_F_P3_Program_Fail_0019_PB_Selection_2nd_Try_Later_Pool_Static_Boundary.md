# Test Spec: VC-43 (15.h) Program Fail Boundary Case - Double Replacement Block Exhaustion & FW Assert

## Verification Criterion (VC)
驗證 UFS 韌體在正常區域（Normal Area）的壞塊管理機制，特別是當「預測的下一個替換區塊（Next Replacement Block）」也發生程式失敗（Program Fail）時的邊界行為：
1. **BBT 更新與只讀模式觸發**：確認當 L2 VB 區塊寫入失敗並被標記為壞塊後，韌體能正確更新 Bad Block Table (BBT)，並強制進入 Read-Only 模式（或準備進入），且該 L2 VB 的 Page_BB 必須小於或等於其對應的替換區塊 PB_BB。
2. **替換區塊耗尽與 Assert 機制**：確認當 L2 VB 寫入失敗，且其預先分配的「第一個替換區塊」也發生程式失敗時，韌體無法完成正常的區塊替換流程，導致設備進入非響應狀態並觸發特定的韌體 Assert (0x203)，此為驗證韌體在多重壞塊情境下的錯誤處理邊界。

## Test Case (TC) Checkpoints

1. [Case01_BBT_Update_and_Readonly_Mode_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 VB 號碼，並透過 VU 40D6 獲取預測的前兩個替換區塊號碼。
     2. 檢查 BBT 的 `max_revoke_cnt` 與 `revoke_cnt`，確保尚未達到最大撤銷計數，且第二個替換區塊有效（!= 0xFFFF）。
     3. 使用 VU C012 針對 L2 VB 的下一個區塊（L2_vb_next）注入 Erase Fail (fail_type=1)，模擬該區塊無法被使用。
     4. 執行連續 Write10 操作，直到 L2 VB 號碼發生改變（表示寫入觸發了區塊替換或遷移）。
     5. 使用 VU 4013 獲取 BE (Bad Erase) 失敗狀態。
     6. 使用 VU 405E 獲取最新的壞塊資訊，並計算 BBT。
   - 預期結果：
     - 新的壞塊計數 (BB_count_new) 必須等於舊計數加 1 (BB_count + 1)。
     - 目標 L2 區塊資訊必須存在於新的 BBT 數據中。
     - 韌體已正確更新 BBT，並確保該 L2 區塊的 Page_BB <= LWP of PB_BB，系統處於可預測的壞塊處理狀態。

2. [Case02_Double_PF_Assert_0x203_Check]：
   - 動作：
     1. 獲取當前 L2 VB 號碼及其對應的第一個空 SLC 物理頁面（first_empty_physical_page）。
     2. 將物理頁面轉換為邏輯頁面（根據 region_max_wl 映射規則：物理頁 <1620 則 /3；1620-1652 則 (頁-1620)/2 + 540 等）。
     3. 透過 VU 40D6 獲取預測的「下一個」替換區塊號碼。
     4. 使用 VU C012 同時針對兩個目標注入程式失敗 (fail_type=3, block_info_list_count=2)：
        - 目標 1：當前 L2 VB 的特定邏輯頁面（觸發寫入失敗）。
        - 目標 2：預測的替換區塊的第 0 頁（觸發替換區塊的程式失敗）。
     5. 執行 Write10 寫入操作，並設置 `skip_response_check=True` 以捕獲超時異常。
     6. 捕獲 `G_TIMEOUT_ALL` 異常後，檢查韌體 Assert 號碼。
   - 預期結果：
     - 寫入操作必須導致設備無響應並觸發 `G_TIMEOUT_ALL`。
     - 韌體 Assert 號碼必須精確等於 `0x203`。
     - 這代表當 L2 區塊及其預設替換區塊同時失效時，韌體無法恢復，進入 Assert 狀態（確認設備未進入正常的 Read-Only 模式，而是處於錯誤掛起狀態），驗證了雙重壞塊情境下的邊界錯誤處理。