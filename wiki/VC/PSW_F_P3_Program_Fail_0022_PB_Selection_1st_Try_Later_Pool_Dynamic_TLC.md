# Test Spec: VC-46 (12.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在正常區域（Normal Area）發生 Program Fail 時的壞塊替換機制：
1. **預處理階段**：確認韌體能正確識別並跳過已處於 Revoke 狀態的替換區塊，透過注入 Erase Fail 強制將目標 L2 VB 標記為壞塊，並驗證 Bad Block Table (BBT) 更新正確（BB Count +1 且目標區塊被標記）。
2. **主測試階段**：在 L2 VB 的第一個空閒物理頁面（First Empty Physical Page）注入 Program Fail (`fail_type=3`)，觸發韌體的替換流程。
3. **核心驗證點**：確認韌體在首次嘗試替換時即成功選取新的替換區塊（PB），且此過程未觸發韌體 Assert 或崩潰。具體驗證指標為：Bad Block Count 增加 1、目標 L2 VB 被正確加入 BBT、且韌體內部狀態機正常處理了此次 Program Fail 事件，證明動態替換池（Dynamic Replacement Pool）的共享機制運作正常。

## Test Case (TC) Checkpoints

1. [PreProcess_EraseFail_BBTable_Update_Check]：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 與 `0x40DC` 獲取當前 L2 Open VB 號碼 (`L2_vb`) 與下一個 L2 VB 號碼 (`L2_vb_next`)。
     2. 透過 `0x405E` 記錄初始 Bad Block Count (`BB_count`)。
     3. 透過 `0x40D6` 獲取預測的下一個替換區塊 (`next_replacement_block`)，若該區塊位於 Revoke Group 則重複上述流程直到找到非 Revoke 區塊。
     4. 針對 `L2_vb_next` 的 Block 0, Plane 0, Page 0，透過 Vendor Command `0xC012` 注入 Erase Fail (`fail_type=1`)。
     5. 執行連續 Write10 指令直到 L2 VB 發生切換（即 `L2_vb_new != L2_vb`），確保寫入操作觸發了區塊替換邏輯。
     6. 透過 `0x4013` 獲取 BE Fail 狀態，並再次透過 `0x405E` 獲取新的 Bad Block Information。
     7. 計算新的 BB Count (`BB_count_new`) 並解析 BBT 數據。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`。
     - 解析後的 BBT 數據中必須包含目標區塊資訊（CE=0, Plane=0, Block=`L2_vb_next`），代表韌體已正確將該區塊標記為壞塊並更新內部表格，無 Assert 發生。

2. [MainStep_ProgramFail_Replacement_Success_Check]：
   - 動作：
     1. 透過 `get_open_vb_info` 獲取當前 L2 VB (`logical_VB`) 與第一空閒物理頁面 (`physical_page`)。
     2. 根據韌體特定的 WL 區域映射規則（Region Max WL: [540, 556, 1108]），將 `physical_page` 轉換為對應的 Logical Page 索引。
        - 若 `physical_page < 1620`: `logical_page = physical_page // 3`
        - 若 `1620 <= physical_page < 1652`: `logical_page = (physical_page - 1620) // 2 + 540`
        - 若 `1652 <= physical_page < 3308`: `logical_page = (physical_page - 1652) // 3 + 1096` (540+556)
        - 若 `3308 <= physical_page < 3312`: `logical_page = (physical_page - 3308) // 1 + 1652` (540+556+1108)
     3. 針對該 L2 VB 的指定 Logical Page，透過 Vendor Command `0xC012` 注入 Program Fail (`fail_type=3`)。
     4. 執行單次 Write10 指令（長度 `api.WRITE_10_MAX_BLOCK_LEN`），並設定 `skip_response_check=True` 以允許韌體處理 Fail 而不立即回報 Host 錯誤。
     5. 透過 `0x4013` 獲取 BE Fail 狀態，並透過 `0x405E` 驗證 BBT 更新。
   - 預期結果：
     - 腳本執行過程中未拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，代表韌體未 Assert。
     - `BB_count_new` 必須等於注入前的 `BB_count + 1`。
     - BBT 數據中必須包含目標 L2 VB 區塊，代表韌體成功識別 Program Fail 並將其標記為壞塊。
     - 此結果驗證了韌體在 Normal Area 發生 Program Fail 時，能正確選擇新的替換區塊（PB）並完成壞塊管理，符合 VC-46 中 "selection new PB succeed on the first try" 的要求。