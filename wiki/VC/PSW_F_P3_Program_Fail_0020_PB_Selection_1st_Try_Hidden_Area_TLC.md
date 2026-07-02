# Test Spec: VC-44 (12.e) Program Fail in Hidden Area with New PB Selection

## Verification Criterion (VC)
驗證韌體在 Hidden Area (L2) 發生 Program Fail 時的錯誤處理與壞塊管理機制：
1. **BBT 更新正確性**：確認在注入 L2 區塊與 BBT 替換區塊的 Program Fail 後，韌體能正確識別並標記這兩個區塊為壞塊。
2. **BB Count 增量驗證**：確認 Bad Block Count (BB Count) 嚴格增加 2，分別對應 L2 目標區塊與 BBT 替換區塊。
3. **BBT 數據完整性**：確認 Bad Block Table (BBT) 中確實包含被標記為壞塊的 L2 區塊資訊以及 BBT 替換區塊資訊。
4. **韌體穩定性**：確認在此異常情境下，韌體執行流程正常結束，未觸發 Assert 或系統崩潰，且能透過 `open_card` 正常恢復。

## Test Case (TC) Checkpoints
1. [PreProcess_FillToFirstEmptyPage]：
   - 動作：執行迴圈寫入 16 Bytes 資料至 LBA 0，持續直到 `get_open_vb_info` 返回的 `TLC_L2.first_empty_physical_page` 大於等於 1652。此步驟旨在填充 Hidden Area 以確保後續測試在正確的物理頁面邊界進行。
   - 預期結果：迴圈終止時，`physical_page` 指標指向 Hidden Area 中第一個可用的空閒 TLC 頁面，為後續注入 Program Fail 提供精確的物理地址基礎。

2. [Step1_GetContextAndInjectPF]：
   - 動作：
     a. 呼叫 `get_open_vb_info` 獲取當前 `logical_VB` 與 `first_empty_physical_page`。
     b. 將物理頁面轉換為邏輯頁面 (`logical_page`)，根據頁面範圍 (<1620, <1652, <3308, <3312) 套用不同的映射公式。
     c. 呼叫 VU 0x405E 記錄初始 Bad Block Count (`BB_count`)。
     d. 呼叫 VU 0x40D6 獲取預測的下一個替換區塊 (`next_replacement_block`) 及其 CE/Plane 資訊。
     e. 構造 `PhysicalAddressInformation`，設定 `BlockInfoList_0` 為當前 L2 目標區塊 (CE=0, Plane=0, Block=`logical_VB`, Page=`logical_page`)，設定 `BlockInfoList_1` 為替換區塊 (CE/Plane/Block 來自 0x40D6 結果)。
     f. 呼叫 VU 0xC012 注入 Program Fail，`fail_type=3`，針對上述兩個區塊列表進行注入。
   - 預期結果：韌體內部狀態機接收到 Program Fail 事件，並準備處理 L2 區塊與替換區塊的壞塊標記邏輯。

3. [Step1_TriggerPFAndVerifyBBT]：
   - 動作：
     a. 執行 `Write10` 命令 (LBA 0, 長度 `WRITE_10_MAX_BLOCK_LEN`) 觸發實際的 Program Fail 硬體行為。
     b. 呼叫 VU 0x4013 獲取 BE (Block Error) Fail 狀態。
     c. 再次呼叫 VU 0x405E 獲取新的 Bad Block Count (`BB_count_new`) 及 BBT 數據 (`BB_data_new`)。
     d. 驗證 `BB_count_new` 是否等於 `BB_count + 2`。
     e. 在 `BB_data_new` 中搜尋是否存在包含 `target_data_L2` (原 L2 區塊資訊) 的條目。
     f. 在 `BB_data_new` 中搜尋是否存在包含 `target_data_BBT` (替換區塊資訊) 的條目。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 2`，證明韌體正確識別並記錄了兩個新的壞塊。
     - `find` 變數在 L2 檢查中必須為真，證明 L2 目標區塊已被正確標記為壞塊。
     - `find` 變數在 BBT 檢查中必須為真，證明替換區塊也已被正確標記為壞塊。
     - 整個測試流程無 Assert 異常，證明韌體在處理 Hidden Area Program Fail 時具備足夠的魯棒性。