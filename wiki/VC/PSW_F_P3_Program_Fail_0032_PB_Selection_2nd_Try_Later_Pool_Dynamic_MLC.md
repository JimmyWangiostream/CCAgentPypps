# Test Spec: VC-56 (13.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生寫入失敗（Program Fail）時的替換區塊（Replacement Block）選擇邏輯與壞塊表（BBT）更新行為：
1. **Case 01 (Erase Fail / L2 EF)**：當目標 L2 VB 的 Erase 失敗時，韌體應從動態共享替換池（Dynamic Shared Pool）中選擇下一個預測區塊。驗證 BBT 中僅增加 1 個壞塊計數，且該 L2 VB 被標記為壞塊，韌體無 Assert 並正常更新 BBT。
2. **Case 02 (Program Fail / L2 PF & Replacement PF)**：當目標 L2 VB 的 Program 失敗，且其預測的下一個替換區塊（Next Replacement Block）也同時被注入 Program 失敗時，韌體應強制進入唯讀模式（Force Read Only Mode）。驗證 BBT 中增加 2 個壞塊計數（原 L2 VB + 替換區塊），且這兩個區塊均被正確標記為壞塊。

## Test Case (TC) Checkpoints

1. **[Case01_EraseFail_DynamicPool_Check]**：
   - 動作：
     1. 透過 Vendor Command `VU 40C1` 獲取當前 L2 VB (`L2_vb`)，透過 `VU 40DC` 獲取下一個 L2 VB (`L2_vb_next`)。
     2. 透過 `VU 405E` 記錄初始壞塊計數 (`BB_count`)。
     3. 透過 `VU 40D6` (pool_type=1, is_CIS=0) 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. 若 `next_replacement_block` 不在 Revoke Group 中，則透過 Vendor Command `VU C012` (fail_type=1) 對 `L2_vb_next` 的 Page 0 注入 **Erase Fail**。
     5. 執行連續 Write10 操作，直到 L2 VB 發生切換（即寫入觸發了 L2 VB 的遷移或替換）。
     6. 透過 `VU 4013` 獲取 BE 失敗狀態，並透過 `VU 405E` 獲取新的壞塊資訊。
   - 預期結果：
     - 新的壞塊計數 (`BB_count_new`) 必須等於 `BB_count + 1`。
     - 計算後的 BBT (`BB_data_new`) 中必須包含目標 L2 VB (`target_data_L2`) 的壞塊標記。
     - 韌體未發生 Assert，證明在 Erase Fail 情境下，韌體能正確處理動態替換池的區塊並更新 BBT。

2. **[Case02_ProgramFail_ForcedReadOnly_Check]**：
   - 動作：
     1. 透過 `get_open_vb_info` 獲取當前 L2 VB (`logical_VB`) 及第一個空物理頁 (`physical_page`)。
     2. 將物理頁轉換為邏輯頁 (`logical_page`)，計算邏輯依據：若 `physical_page < 1620`，則 `logical_page = physical_page // 3`；若 `1620 <= physical_page < 1652`，則 `logical_page = (physical_page - 1620) // 2 + 540`；若 `1652 <= physical_page < 3308`，則 `logical_page = (physical_page - 1652) // 3 + 556`；若 `3308 <= physical_page < 3312`，則 `logical_page = (physical_page - 3308) // 1 + 1108`。
     3. 透過 `VU 40D6` (pool_type=1, is_CIS=0) 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. 透過 Vendor Command `VU C012` (fail_type=3, block_info_list_count=2) 同時注入兩個 Program Fail：
        - 目標 1：當前 L2 VB (`logical_VB`) 的 `logical_page`。
        - 目標 2：預測的替換區塊 (`next_replacement_block`) 的 Page 0。
     5. 執行 Write10 操作（長度為 `api.WRITE_10_MAX_BLOCK_LEN`），觸發寫入失敗。
     6. 透過 `VU 4013` 獲取 BE 失敗狀態，並透過 `VU 405E` 獲取新的壞塊資訊。
   - 預期結果：
     - 新的壞塊計數 (`BB_count_new`) 必須等於 `BB_count + 2`。
     - 計算後的 BBT (`BB_data_new`) 中必須同時包含目標 L2 VB (`target_data_L2`) 與目標替換區塊 (`target_data_replace`) 的壞塊標記。
     - 此情境驗證當主區塊與替換區塊均失效時，韌體應強制進入唯讀模式（Force Read Only Mode），並正確記錄雙重壞塊。