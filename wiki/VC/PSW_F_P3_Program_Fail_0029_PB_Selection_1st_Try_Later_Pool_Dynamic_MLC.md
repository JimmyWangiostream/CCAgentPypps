# Test Spec: VC-53 (12.g) Program Fail on L2 MLC Page with Dynamic Replacement Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）的 L2 VB 中，當針對 MLC 頁面的第一個空閒物理頁（First Empty Physical Page）注入 Program Fail (PF) 錯誤時，控制器的硬體行為與韌體恢復機制：
1.  **錯誤注入與觸發**：透過 Vendor Command `0xC012` 在指定的 L2 VB 及計算出的 Logical Page 注入 `fail_type=3` (Program Fail)，隨後執行 Write10 命令觸發該頁面的寫入操作。
2.  **狀態檢查**：確認 Write10 命令返回錯誤狀態，且透過 Vendor Command `0x4013` 讀取到的 BE (Bad Entry) Fail Status 正確反映此次 Program Fail。
3.  **BBT 更新驗證**：確認 Bad Block Table (BBT) 中的 Bad Block Count 增加 1，且被標記為壞塊的 L2 VB 確實存在於 BBT 數據結構中。
4.  **動態替換機制驗證**：確認韌體自動將該 L2 VB 標記為壞塊後，成功從替換池（Replacement Pool）中選取一個新的 PB（Physical Block）作為新的 L2 VB，且此過程無需 Assert 或系統崩潰，證明動態替換邏輯在 MLC 頁面級別運作正常。

## Test Case (TC) Checkpoints
1.  [PreProcess_Loop_Ensure_Dynamic_Replacement_Availability]：
    -   動作：
        1.  透過 `get_VB_group` 獲取當前屬於 `REVOKE_BLK` 組的 VB 列表。
        2.  進入循環：透過 Vendor Command `0x40C1` 獲取當前 L2 VB (`L2_vb`)，透過 `0x40DC` 獲取下一個預期的 L2 VB (`L2_vb_next`)，透過 `0x405E` 記錄當前 BB Count，透過 `0x40D6` 獲取預測的下一個替換塊 (`next_replacement_block`)。
        3.  檢查條件：若 `next_replacement_block` 不在 `revoke_group` 中，則跳出循環；否則，透過 `0xC012` 在 `L2_vb_next` 的 Page 0 注入 Erase Fail (`fail_type=1`)，強制該塊成為壞塊。
        4.  執行連續寫入（Write10, LBA 0, Length `WRITE_10_MAX_BLOCK_LEN`），直到 `0x40C1` 返回的 L2 VB 發生改變（表示舊 L2 VB 已壞並切換）。
        5.  透過 `0x4013` 檢查 BE Fail Status，透過 `0x405E` 驗證 BB Count 增加且 BBT 中包含目標塊。
        6.  重複上述循環，直到 `0x40D6` 返回的替換塊位於 `revoke_group` 中（確保替換池中有可用資源）。
        7.  最後，透過連續寫入（Length 16）填充 MLC 頁面，直到 `open_vb.TLC_L2.first_empty_physical_page.value` 大於等於 1620，確保測試目標頁位於 MLC 區域且為第一個空閒頁。
    -   預期結果：循環終止時，系統處於一個穩定的狀態，其中 L2 VB 指向一個有效的物理塊，且該塊的第一個空閒物理頁位於 MLC 區域（Page >= 1620），替換池準備就緒。

2.  [Step1_L2_MLC_PF_Injection_and_BBT_Update]：
    -   動作：
        1.  透過 `get_open_vb_info` 獲取當前 L2 VB (`logical_VB`) 及第一個空閒物理頁 (`physical_page`)。
        2.  透過 `0x405E` 記錄當前 BB Count (`BB_count`)。
        3.  將 `physical_page` 轉換為 `logical_page`：若 `1620 <= physical_page < 1652`，則 `logical_page = (physical_page - 1620) // 2 + 540`；若 `1652 <= physical_page < 3308`，則 `logical_page = (physical_page - 1652) // 3 + 556`；若 `3308 <= physical_page < 3312`，則 `logical_page = (physical_page - 3308) // 1 + 1108`。
        4.  透過 Vendor Command `0xC012` 在 CE=0, Plane=0, Block=`logical_VB`, Page=`logical_page` 注入 Program Fail (`fail_type=3`)。
        5.  執行 Write10 命令（LUN 0, LBA 0, Length `WRITE_10_MAX_BLOCK_LEN`, FUA=1），並設置 `skip_response_check=True` 以允許錯誤返回。
        6.  透過 Vendor Command `0x4013` 讀取 BE Fail Status。
        7.  透過 `0x405E` 獲取新的 BB Count (`BB_count_new`) 及 BBT 數據 (`BB_data_new`)。
        8.  驗證 `BB_count_new` 是否等於 `BB_count + 1`。
        9.  在 `BB_data_new` 中搜索包含目標 Block, CE, Plane 的條目。
    -   預期結果：
        1.  Write10 命令執行完畢（儘管內部失敗，但命令流程完成）。
        2.  `BB_count_new` 必須嚴格等於 `BB_count + 1`。
        3.  搜索結果 `find` 必須非空，證明目標 L2 VB 已被正確標記為壞塊並記錄在 BBT 中。
        4.  韌體未發生 Assert 或崩潰，系統保持穩定，證明動態替換機制在 MLC 頁面 Program Fail 情境下觸發成功且無異常。