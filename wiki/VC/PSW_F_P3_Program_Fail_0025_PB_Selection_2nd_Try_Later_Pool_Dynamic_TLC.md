# Test Spec: VC-49 (13.g) Program Fail with Replacement Block Injection & Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在正常區域（Normal Area）發生 Program Fail 且透過 Vendor Command 強制標記「當前 L2 VB」與「預測替換區塊（Next Replacement Block）」為失效時，硬體與韌體的錯誤處理機制：
1. **BBT 更新驗證**：確認 Bad Block Table (BBT) 正確記錄了被注入失效的 L2 VB 區塊與替換區塊，且 Bad Block Count (BB Count) 精確增加 2。
2. **替換機制驗證**：確認韌體在遭遇 Program Fail 後，能正確識別替換區塊並成功完成寫入操作，證明替換邏輯運作正常。
3. **系統穩定性驗證**：確認在此複雜錯誤注入情境下，韌體未觸發 Assert 或 Crash，且能透過後續的寫入操作恢復正常狀態。

## Test Case (TC) Checkpoints

1. [PreProcess_CycleUntilRevokeGroup]：
   - 動作：
     1. 透過 VU 40C1 與 40DC 獲取當前 L2 VB (`L2_vb`) 與下一個 L2 VB (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始 BB Count。
     3. 透過 VU 40D6 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. 若 `next_replacement_block` 屬於 Revoke Group，則透過 VU C012 (fail_type=1) 對 `L2_vb_next` 注入 Erase Fail，並執行連續 Write10 直到 L2 VB 切換，重複此循環直到預測的替換區塊不在 Revoke Group 中。
     5. 進入第二階段循環：透過連續 Write10 (length=16) 填充資料，直到 `first_empty_physical_page` 達到臨界值 1652，確保後續測試在特定的 TLC 頁面區域進行。
   - 預期結果：
     - 循環終止條件滿足：預測的替換區塊不在 Revoke Group 中，且當前物理頁面已填充至接近 1652 的位置，為後續的 Program Fail 測試準備好特定的 TLC 頁面環境。

2. [Step1_L2_PF_With_Replacement_PF_Verification]：
   - 動作：
     1. 獲取當前 L2 VB (`logical_VB`) 與 `first_empty_physical_page`，並根據頁面範圍公式（如 `<1620` 或 `<1652` 等）計算對應的 `logical_page`。
     2. 透過 VU 40D6 獲取下一個替換區塊 (`next_replacement_block`)。
     3. 透過 VU C012 (fail_type=3, block_info_list_count=2) 同時注入兩個失效：
        - 目標 1：當前 L2 VB 的計算出的 `logical_page` (Program Fail)。
        - 目標 2：`next_replacement_block` 的 Page 0 (Program Fail)。
     4. 執行一次 Write10 (length=WRITE_10_MAX_BLOCK_LEN, fua=1) 觸發寫入操作。
     5. 透過 VU 4013 檢查 BE (Block Error) Fail 狀態。
     6. 透過 VU 405E 獲取新的 BB Count 與 BBT 數據。
   - 預期結果：
     - **BB Count 驗證**：新的 BB Count (`BB_count_new`) 必須等於初始 BB Count 加 2 (`BB_count + 2`)。
     - **BBT 數據驗證**：
       - BBT 中必須包含被標記失效的 L2 VB 區塊 (`target_data_L2`)。
       - BBT 中必須包含被標記失效的替換區塊 (`target_data_replace`)。
     - **寫入行為驗證**：儘管寫入目標 L2 VB 被標記為 Program Fail，且其預設替換區塊也被標記為 Program Fail，韌體應能處理此異常（例如尋找其他替換區塊或報告特定錯誤碼），且系統未崩潰（No Assert）。

3. [PostProcess_SystemRecovery]：
   - 動作：執行 `open_card()` 重新初始化卡片連接。
   - 預期結果：
     - 卡片連接成功恢復，證明韌體在經歷複雜的 Program Fail 與 BBT 更新後，系統狀態穩定，無殘留的硬體鎖定或韌體錯誤狀態。