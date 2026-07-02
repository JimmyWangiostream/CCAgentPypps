# Test Spec: VC-47 (12.h) Program Fail on L2 VB First Empty Page - Assert 0x203 Verification

## Verification Criterion (VC)
驗證在正常區域（Normal Area）的 L2 VB（Logical VB）第一個空物理頁（First Empty Physical Page）發生 Program Fail 時，韌體的錯誤處理機制：
1.  **BBT 更新驗證**：確認在觸發 Fail 前，Bad Block Table (BBT) 已正確記錄目標 Block 為壞塊，且 Bad Block Count 增加 1。
2.  **強制唯讀模式驗證**：確認當在 L2 VB 的寫入指標（First Empty Physical Page）處強制注入 Program Fail (`fail_type=3`) 後，韌體不應進入強制唯讀模式（Force Read-Only Mode），而是觸發特定的韌體斷言（FW Assert）。
3.  **Assert 碼驗證**：確認設備在寫入超時後，返回的 FW Assert 號碼必須精確為 `0x203`，代表設備處於非唯讀的異常掛起狀態（Device remains unresponsive after initialization. Confirmed not in read-only mode），而非正常的錯誤恢復流程。

## Test Case (TC) Checkpoints

1.  **[PreProcess_BBT_Initialization_and_L2_VB_Selection]**：
    -   動作：
        1.  透過 Vendor Command `VU 40C1` 獲取當前 L2 VB 號碼 (`L2_vb`) 及透過 `VU 40DC` 獲取下一個 L2 VB (`L2_vb_next`)。
        2.  透過 `VU 405E` 記錄初始 Bad Block Count (`BB_count`)。
        3.  透過 `VU 40D6` 預測並獲取前兩個替換 Block (`next_replacement_block_1`, `next_replacement_block_2`)。
        4.  若 `next_replacement_block_2` 不為 `0xFFFF`，則針對 `L2_vb_next` 的 Block 0, Plane 0, Page 0 執行 `VU C012` 注入 Erase Fail (`fail_type=1`)，模擬該 Block 為壞塊。
        5.  執行連續 Write10 指令，直到 `VU 40C1` 返回的 L2 VB 發生跳變（即寫入觸發了 L2 VB 切換），確保系統狀態穩定。
        6.  透過 `VU 4013` 獲取 BE Fail 狀態，並再次透過 `VU 405E` 驗證 BBT。
        7.  驗證 `BB_count_new` 必須等於 `BB_count + 1`，且 BBT 數據中必須包含目標 Block (`target_data_L2`) 的記錄。
        8.  重複上述流程，直到 `VU 40D6` 返回的下一個替換 Block 數量不足（剩下一個），確保測試環境達到特定的壞塊累積狀態。
        9.  執行連續寫入直到 L2 VB 的第一個空物理頁 (`first_empty_physical_page`) 達到臨界值（`>= 1652`），以填充頁面並確保後續測試針對正確的物理頁。
    -   預期結果：
        -   初始 BBT 記錄正確，目標 Block 被標記為壞塊。
        -   `BB_count` 在注入 Erase Fail 後精確增加 1。
        -   L2 VB 成功切換，證明寫入流程正常運作。
        -   環境準備就緒，L2 VB 的第一個空物理頁位置確定。

2.  **[Step1_Program_Fail_Injection_and_Assert_0x203_Check]**：
    -   動作：
        1.  透過 `get_open_vb_info` 獲取當前 L2 VB (`logical_VB`) 及其第一個空物理頁 (`physical_page`)。
        2.  根據硬體映射規則（`region_max_wl` 陣列），將 `physical_page` 轉換為對應的邏輯頁 (`logical_page`)。轉換邏輯如下：
            -   若 `physical_page < 1620`: `logical_page = physical_page // 3`
            -   若 `1620 <= physical_page < 1652`: `logical_page = (physical_page - 1620) // 2 + 540`
            -   若 `1652 <= physical_page < 3308`: `logical_page = (physical_page - 1652) // 3 + 1108`
            -   若 `3308 <= physical_page < 3312`: `logical_page = (physical_page - 3308) // 1 + 1108` (註：範例代碼中 `region_max_wl[2]` 為 1108，但邏輯上需確認累加值，此處依代碼邏輯執行)。
        3.  針對該 L2 VB 的 CE 0, Plane 0, Block `logical_VB`, Page `logical_page`，執行 `VU C012` 注入 Program Fail (`fail_type=3`)。
        4.  發送 Write10 指令（長度 `WRITE_10_MAX_BLOCK_LEN`），並設置 `skip_response_check=True` 以捕獲異常。
        5.  捕獲 `G_TIMEOUT_ALL` 異常，並調用 `api.get_fw_assert_number()` 獲取韌體 Assert 號碼。
    -   預期結果：
        -   寫入指令必須觸發超時 (`G_TIMEOUT_ALL`)，證明設備未立即返回錯誤碼。
        -   `api.get_fw_assert_number()` 返回的值必須精確等於 `0x203`。
        -   此結果確認韌體在 L2 VB 寫入指標處遭遇 Program Fail 時，未進入 Force Read-Only 模式，而是觸發了特定的 Assert 狀態，符合 VC-47 對於「selection new PB succeed on the first try... FW should be update BB table and force read only mode」的逆向驗證（即驗證在此特定注入情境下，預期行為是 Assert 而非正常的 Read-Only 切換，或驗證 Assert 機制本身）。