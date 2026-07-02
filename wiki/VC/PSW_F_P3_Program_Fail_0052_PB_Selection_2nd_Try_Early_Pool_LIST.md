# Test Spec: VC-34 (13.f) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生 Program Fail 且初始替換區塊（Replacement Block）亦失效的情境下，硬體與韌體的錯誤處理機制：
1.  **替換邏輯驗證**：確認當 LIST VB 對應的實體區塊（LIST Block）與預判的下一個替換區塊（Next Replacement Block）同時被注入 Program Fail 時，韌體能正確識別 LIST Block 為失效，並從 Early Replacement Pool 中選取新的替換區塊，而非崩潰或錯誤地標記整個 LUN。
2.  **BB Table 更新驗證**：確認在觸發 Program Fail 並透過 Write10 寫入觸發 LIST VB 切換後，Bad Block Table (BBT) 必須精確記錄兩個失效區塊（原 LIST Block 與原 Next Replacement Block），且 Bad Block Count 必須嚴格增加 2。
3.  **韌體穩定性驗證**：確認在此異常流程中，韌體不會觸發 Assert 或 Hard Fault，且能透過 Vendor Command 正常讀取狀態，證明韌體具備處理多重替換失敗的魯棒性。

## Test Case (TC) Checkpoints
1.  **[Case01_Initial_State_Recording]**：
    -   動作：透過 Vendor Command `0x40C1` 讀取當前 Open VB 資訊，提取 `List_Block_VB_number_logical` 作為目標 LIST Block；透過 `0x40DC` 讀取下一個 Open VB 資訊，提取 `List` 作為目標 Next Replacement Block；透過 `0x405E` 讀取當前 Bad Block Count (`BB_count`)；透過 `0x40D6` (pool_type=1, next_n=1) 讀取 Early Replacement Pool 中的第一個預測替換區塊 (`next_replacement_block`)。
    -   預期結果：成功獲取 LIST Block、Next Replacement Block 及當前 BB Count；`next_replacement_block` 必須為有效實體區塊地址，且與 LIST Block 不同。

2.  **[Case02_Program_Fail_Injection]**：
    -   動作：建構 `PhysicalAddressInformation`，將 `BlockInfoList_0` 設定為 LIST Block，`BlockInfoList_1` 設定為 Next Replacement Block（CE=0, Plane=0, Page=0）。執行 Vendor Command `0xC012`，設定 `fail_type=0` (Program Fail)，並指定這兩個區塊為失效目標。
    -   預期結果：韌體成功接收並記錄這兩個區塊的 Program Fail 狀態，未發生 Assert 或系統崩潰。

3.  **[Case03_List_VB_Switch_Trigger]**：
    -   動作：在迴圈中持續發送 `Write10` 命令（長度 `WRITE_10_MAX_BLOCK_LEN`，LUN=0，隨機 LBA，FUA=1），每次寫入後透過 `0x40C1` 檢查 `List_Block_VB_number_logical`。當檢測到 `List_Block_VB_number_logical` 發生變化（即 LIST VB 切換，意味著原 LIST Block 被標記為失效並啟用新區塊）時，停止寫入。
    -   預期結果：寫入操作成功完成（或按預期處理），且 `List_Block_VB_number_logical` 確實發生變更，證明韌體已執行替換邏輯並切換至新的邏輯區塊。

4.  **[Case04_BBT_Verification]**：
    -   動作：執行 Vendor Command `0x4013` 獲取 BE (Bad Endurance) Fail Status；再次執行 `0x405E` 獲取新的 Bad Block Count (`BB_count_new`) 及 Bad Block Data (`BB_data_new`)。計算 `BB_data_new` 並檢查是否包含原 LIST Block 與原 Next Replacement Block 的實體地址資訊。
    -   預期結果：
        1.  `BB_count_new` 必須嚴格等於 `BB_count + 2`。
        2.  `BB_data_new` 中必須能找到與 `target_data_LIST` (原 LIST Block) 匹配的條目。
        3.  `BB_data_new` 中必須能找到與 `target_data_replace` (原 Next Replacement Block) 匹配的條目。
        4.  若上述任一條件不滿足，測試應報錯 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體未正確更新 BBT 或未正確標記替換區塊為失效。