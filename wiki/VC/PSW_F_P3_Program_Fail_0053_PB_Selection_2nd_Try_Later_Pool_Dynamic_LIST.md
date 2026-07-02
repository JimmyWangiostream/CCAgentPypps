# Test Spec: VC-35 (13.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在正常區域（Normal Area）與列表區塊（LIST VB）發生 Program/Erase Fail 時的替換區塊（Replacement Block）選擇邏輯與 BBT（Bad Block Table）更新機制：
1. **Normal Area 情境**：當 L2 開放區塊（L2 Open VB）發生寫入失敗時，韌體應從動態替換池（Dynamic Replacement Pool）中選取一個新的替換區塊。驗證目標是確保該新選取的替換區塊**不屬於** Revoke Group（即為有效可用區塊），且 BBT 正確記錄該 L2 區塊為壞塊，BB Count 增加 1。
2. **LIST VB 情境**：當 LIST VB 發生寫入失敗時，韌體應嘗試選取替換區塊。驗證目標是模擬「首選替換區塊也失效」的情境，透過注入兩個 Program Fail（一個在 LIST VB，一個在預測的下一個替換區塊），確認韌體能正確將這兩個區塊都標記為壞塊，BB Count 增加 2，並驗證 BBT 中同時存在 LIST 區塊與替換區塊的壞塊記錄。

## Test Case (TC) Checkpoints

1. **[Case01_Normal_L2_Replacement_Valid_Check]**：
   - 動作：
     1. 透過 Vendor Command `VU 40C1` 獲取當前 L2 Open VB (`L2_vb`)，透過 `VU 40DC` 獲取下一個開放的 L2 VB (`L2_vb_next`)。
     2. 透過 `VU 405E` 記錄初始 Bad Block Count (`BB_count`)。
     3. 透過 `VU 40D6` 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. **循環檢查**：若 `next_replacement_block` 屬於 Revoke Group（透過 `VU 40C1` 獲取 Revoke Group 列表比對），則針對該 `L2_vb_next` 執行 `VU C012` 注入 Program/Erase Fail (`fail_type=1`)，強制該區塊變為壞塊，然後繼續寫入資料直到 L2 VB 切換，重複此過程直到獲取到的 `next_replacement_block` **不在** Revoke Group 中。
     5. 一旦獲得有效的替換區塊，執行連續寫入（Sequential Writes, LBA 0 開始）直到 L2 VB 切換至新的 `L2_vb_new`。
     6. 透過 `VU 4013` 獲取 BE Fail 狀態，並透過 `VU 405E` 獲取新的 BBT 數據。
   - 預期結果：
     - 最終獲取的 `next_replacement_block` 必須不在 Revoke Group 中。
     - 新的 `BB_count_new` 必須等於 `BB_count + 1`。
     - 計算後的 BBT (`BB_data_new`) 中必須包含目標 L2 區塊 (`target_data_L2`) 的壞塊記錄，代表韌體成功將失效的 L2 區塊標記為壞塊並更新了 BBT。

2. **[Case02_LIST_VB_Double_PF_Replacement_Check]**：
   - 動作：
     1. 透過 `VU 40C1` 獲取 LIST VB (`LIST_vb`)，透過 `VU 40DC` 獲取下一個 LIST VB (`LIST_vb_next`)。
     2. 透過 `VU 405E` 記錄初始 `BB_count`。
     3. 透過 `VU 40D6` 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. **雙重故障注入**：透過 `VU C012` 同時注入兩個 Program Fail (`fail_type=0`, `block_info_list_count=2`)：
        - 第一個目標：`LIST_vb_next` (CE=0, Plane=0)。
        - 第二個目標：`next_replacement_block` (CE=0, Plane=0)。
     5. 執行隨機寫入（Random Writes, LBA 隨機範圍）直到 LIST VB 切換至新的 `LIST_vb_new`。
     6. 透過 `VU 4013` 獲取 BE Fail 狀態，並透過 `VU 405E` 獲取新的 BBT 數據。
   - 預期結果：
     - 新的 `BB_count_new` 必須等於 `BB_count + 2`。
     - 計算後的 BBT (`BB_data_new`) 中必須同時包含兩個目標區塊的壞塊記錄：
       1. 目標 LIST 區塊 (`target_data_LIST`)。
       2. 目標替換區塊 (`target_data_replace`)。
     - 這代表當首選替換區塊也失效時，韌體能正確處理雙重失敗並更新 BBT，且未觸發 Assert 或異常崩潰。