# Test Spec: VC-50 (13.h) Program Fail Double Replacement Exhaustion & FW Assert Check

## Verification Criterion (VC)
驗證在 TLC 區塊中，當 L2 開放區塊（Open VB）與下一個預測替換區塊（Next Replacement Block）同時遭遇 Program Fail 且替換池耗盡時，韌體的錯誤處理機制：
1.  **前置準備**：確認 BBT（Bad Block Table）的 revoke 計數器未達上限，並透過 VU C012 注入 Erase Fail 以消耗替換資源，確保後續測試情境為「替換池即將枯竭」。
2.  **雙重故障注入**：針對當前 L2 VB 及其對應的第一個預測替換區塊，同時注入 Program Fail（fail_type=3），模擬硬體寫入失敗。
3.  **異常行為驗證**：執行 Write10 命令觸發寫入，預期裝置進入非響應狀態（Unresponsive），並確認韌體觸發 Assert 0x203（代表 Device remains unresponsive after initialization），且**未**進入強制唯讀模式（Read-Only Mode），以此驗證在替換資源完全耗盡且雙重故障下的特定韌體崩潰路徑。

## Test Case (TC) Checkpoints

1.  [PreProcess_BBT_Exhaustion_Check]：
    -   動作：
        1.  透過 VU 40C1 讀取當前 L2 Open VB (`L2_vb`) 與透過 VU 40DC 讀取下一個 Open VB (`L2_vb_next`)。
        2.  透過 VU 405E 記錄初始 Bad Block 計數 (`BB_count`)。
        3.  透過 VU 40D6 預測接下來兩個替換區塊 (`next_replacement_block_1`, `next_replacement_block_2`)，並讀取 FW 內部變數 `gUfsApiStruct.ftl->bbt.max_revoke_cnt` 與 `revoke_cnt`。
        4.  若 `revoke_cnt` 等於 `max_revoke_cnt` 且第二個替換區塊不為 0xFFFF，則跳出循環；否則，透過 VU C012 對 `L2_vb_next` 注入 Erase Fail (`fail_type=1`)。
        5.  執行連續 Write10 直到 L2 VB 發生跳變，確認替換機制運作並消耗資源。
        6.  透過 VU 4013 讀取 BE Fail 狀態，並透過 VU 405E 再次讀取 BB 資訊，計算 BBT 數據。
        7.  驗證 `BB_count_new` 必須等於 `BB_count + 1`，且目標區塊資訊 (`target_data_L2`) 必須存在於新的 BBT 數據中。
        8.  重複上述流程，直到 VU 40D6 預測的下一個替換區塊僅剩兩個（即替換池接近枯竭）。
    -   預期結果：
        -   每次 Erase Fail 注入後，BB 計數必須精確增加 1。
        -   目標區塊必須被正確標記為 Bad Block 並記錄在 BBT 中。
        -   循環終止條件滿足時，系統處於替換資源極度緊張的狀態，為後續 Program Fail 測試做準備。

2.  [Step1_Double_PF_Assert_0x203_Check]：
    -   動作：
        1.  透過 `get_open_vb_info` 獲取當前 L2 VB (`logical_VB`) 與第一個空閒物理頁 (`physical_page`)。
        2.  根據 `physical_page` 的範圍（<1620, <1652, <3308, <3312）及 `region_max_wl` 參數，精確計算對應的邏輯頁 (`logical_page`)。
        3.  透過 VU 40D6 獲取下一個預測替換區塊 (`next_replacement_block`)。
        4.  透過 VU C012 同時對兩個區塊注入 Program Fail (`fail_type=3`)：
            -   Block 0: `logical_VB` 的 `logical_page`。
            -   Block 1: `next_replacement_block` 的 Page 0。
        5.  執行 Write10 命令（LBA 0, Length 4KB, FUA=1）。
        6.  捕獲 `G_TIMEOUT_ALL` 異常，並檢查 FW Assert 編號。
    -   預期結果：
        -   寫入命令必須超時並觸發 `G_TIMEOUT_ALL` 異常。
        -   `api.get_fw_assert_number()` 必須精確等於 `0x203`。
        -   此結果確認韌體在雙重 Program Fail 且無可用替換區塊時，進入未響應狀態並觸發特定的 Assert 0x203，而非進入 Read-Only 模式或恢復正常。