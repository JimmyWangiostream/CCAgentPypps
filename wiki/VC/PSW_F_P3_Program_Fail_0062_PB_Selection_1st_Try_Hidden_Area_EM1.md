# Test Spec: VC-29 (12.e) Program Fail in Hidden Area with New PB Selection

## Verification Criterion (VC)
驗證在 Hidden Area (EM1 LUN) 發生 Program Fail 時，韌體能否正確識別並選擇新的替換區塊 (New PB) 於第一次嘗試中成功，同時確認 Bad Block Table (BBT) 的即時更新機制：
1.  **BBT 一致性驗證**：確認在注入 L2 (Host Data) 與 BBT 自身的 Program Fail 後，透過 Vendor Command 405E 讀取的 BB Count 必須精確增加 2，且 BBT 數據結構中必須包含被標記為失效的 L2 區塊與 BBT 替換區塊。
2.  **無 Assert 穩定性**：確認韌體在處理此類隱藏區 Program Fail 並更新 BB Table 的過程中，未觸發系統 Assert (Crash/Hang)，證明韌體具備完整的錯誤恢復與狀態機遷移邏輯。

## Test Case (TC) Checkpoints
1.  **[VC29_HiddenArea_PF_BBT_Update_Check]**：
    -   **動作**：
        1.  配置 LUN 0 為 Normal，LUN 1 為 EM1 (Hidden Area)。
        2.  在 EM1 LUN (LUN 1) 的 LBA 0 寫入 `WRITE_10_MAX_BLOCK_LEN` 的資料，建立初始數據。
        3.  透過 Vendor Command **40C1** 獲取 Open VB 資訊，提取 EM1 L2 的 VB 號碼 (`L2_vb`)。
        4.  透過 Vendor Command **405E** 獲取當前 Bad Block Count (`BB_count`) 作為基準。
        5.  透過 Vendor Command **40D6** 預測下一個替換區塊 (Next Replacement Block)，解析出目標 CE、Plane 與 Block 號碼 (`next_replacement_block`)。
        6.  透過 Vendor Command **C012** 強制注入 Program Fail：
            -   目標 1 (L2 PF)：指定 `L2_vb` 所在的 Block/Page。
            -   目標 2 (BBT PF)：指定預測出的 `next_replacement_block` 所在的 Block/Page。
            -   設定 `fail_type=0`。
        7.  在 EM1 LUN (LUN 1) 再次執行順序寫入 (`Write10`)，觸發韌體處理上述注入的 Fail 狀態。
        8.  透過 Vendor Command **4013** 讀取 BE (Bad Error) Fail Status。
        9.  再次透過 Vendor Command **405E** 獲取新的 Bad Block Count (`BB_count_new`) 及 BBT 詳細數據 (`BB_data_new`)。
        10. 比對 `BB_count_new` 與 `BB_count` 的差異，並檢查 `BB_data_new` 中是否包含被注入失效的 L2 區塊與 BBT 替換區塊。
    -   **預期結果**：
        1.  系統未發生 Assert 或崩潰，韌體穩定運行。
        2.  `BB_count_new` 必須嚴格等於 `BB_count + 2`，證明 L2 區塊與 BBT 替換區塊均被正確標記為 Bad Block。
        3.  `BB_data_new` 列表中必須能找到與 `target_data_L2` (原 L2 Block) 完全匹配的條目。
        4.  `BB_data_new` 列表中必須能找到與 `target_data_BBT` (原 BBT Replacement Block) 完全匹配的條目。
        5.  綜合驗證韌體在 Hidden Area 發生 Program Fail 時，能正確更新 BB Table 並選擇新的 PB，且無軟體異常。