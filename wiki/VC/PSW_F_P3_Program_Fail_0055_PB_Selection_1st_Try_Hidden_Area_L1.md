# Test Spec: VC-29 (12.e) Program Fail in Hidden Area with New PB Selection

## Verification Criterion (VC)
驗證在 Hidden Area（隱藏區）發生 Program Fail 時，韌體是否能正確識別並選擇新的替換區塊（New PB），同時更新 Bad Block Table (BBT) 且不觸發 Assert 異常：
1. **BBT 更新驗證**：確認在注入 Program Fail 後，透過 Vendor Command 405E 讀取的 Bad Block Count 增加 2（分別為 L1 目標區塊與 BBT 替換區塊），且 BBT 數據中明確包含這兩個物理區塊的 CE/Plane/Block 資訊。
2. **New PB 選擇驗證**：確認韌體在處理 L1 區塊的 Program Fail 時，成功從替換池（Pool Type 2）中預測並選擇了一個新的替換區塊（Next Replacement Block），且該區塊被正確標記為 Bad Block 以備後續使用。
3. **系統穩定性驗證**：確認整個流程中韌體未發生 Assert 或崩潰，且 VB 號碼在寫入觸發 Fail 後發生跳變（L1_vb_new != L1_vb），代表韌體已處理完該次異常並推進狀態。

## Test Case (TC) Checkpoints
1. [Case01_BBT_Update_and_New_PB_Selection_Check]：
   - 動作：
     1. 透過 Vendor Command 40C1 獲取當前 L1 Open VB 號碼 (`L1_vb`)。
     2. 透過 Vendor Command 40DC 獲取下一個 L1 Open VB 號碼 (`L1_vb_next`)。
     3. 透過 Vendor Command 405E 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 Vendor Command 40D6 獲取 Hidden Area 的預測替換區塊資訊 (`next_replacement_block`, `next_replacement_plane`, `next_replacement_ce`)，並解析出物理地址。
     5. 透過 Vendor Command C012 注入 Program Fail：
        - 目標 1 (L1 PF)：針對 `L1_vb_next` 所在的 CE/Plane 注入 Fail。
        - 目標 2 (BBT PF)：針對步驟 4 獲取的新替換區塊 (`next_replacement_block`) 注入 Fail。
     6. 執行隨機 Write10 命令（長度 16 LBA，LUN 0），直到讀取到的 L1 Open VB 號碼 (`L1_vb_new`) 與初始值不同，確保寫入操作觸發了韌體的 Fail 處理機制。
     7. 透過 Vendor Command 4013 獲取 BE Fail 狀態。
     8. 再次透過 Vendor Command 405E 獲取新的 Bad Block Count (`BB_count_new`) 及 BBT 詳細數據 (`BB_data_new`)。
     9. 驗證 `BB_count_new` 是否等於 `BB_count + 2`。
     10. 在 `BB_data_new` 中搜尋是否包含目標 L1 區塊 (`target_data_L1`) 和目標 BBT 替換區塊 (`target_data_BBT`) 的 CE/Plane/Block 組合。
   - 預期結果：
     - `BB_count_new` 必須精確等於 `BB_count + 2`，代表兩個注入的 Fail 區塊均被正確計入 Bad Block。
     - `BB_data_new` 中必須存在一筆數據，其 CE、Plane、Block 欄位分別等於 `target_data_L1` 的對應值，代表 L1 目標區塊已被標記為 Bad。
     - `BB_data_new` 中必須存在一筆數據，其 CE、Plane、Block 欄位分別等於 `target_data_BBT` 的對應值，代表新選擇的替換區塊（New PB）已被標記為 Bad。
     - 整個過程無 Assert 發生，且 `L1_vb_new != L1_vb`，代表韌體成功處理了 Program Fail 並更新了 VB 狀態。