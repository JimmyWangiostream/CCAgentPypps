# Test Spec: UFS Program Fail Boundary Case (VC-41) - Early Replacement Pool Selection & BB Table Update

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生寫入失敗（Program Fail）時，若選擇的下一個替換區塊（Next Replacement Block）也同時發生寫入失敗，韌體是否能正確執行以下行為：
1. **BB Table 更新**：Bad Block Table (BBT) 必須正確記錄原始目標區塊（L2 Block）與第一個替換區塊（Replacement Block）為失效狀態，且 BB Count 必須精確增加 2。
2. **無 Assert 穩定性**：韌體在處理連續失敗情境下不得觸發 Assert 或崩潰，系統需保持穩定。
3. **替換邏輯正確性**：確認韌體在 Early Replacement Pool 中尋找替換區塊的邏輯符合預期，且能正確識別並標記多個連續失效區塊。

## Test Case (TC) Checkpoints
1. [PreProcess_FillSLC_Check]：
   - 動作：執行迴圈寫入 16 Bytes 資料至 LBA 0，直到 `get_open_vb_info` 返回的 `TLC_L2.first_empty_physical_page` 數值大於等於 3308。此步驟旨在填充 SLC 區域，確保後續測試在特定的物理頁面邊界條件下進行。
   - 預期結果：寫入操作成功完成，且當前空閒物理頁面指標達到或超過 3308，為後續的邊界測試建立基礎環境。

2. [Step1_GetContextAndInjectPF_Check]：
   - 動作：
     a. 呼叫 `get_open_vb_info` 獲取當前 `logical_VB` 與 `physical_page`，並透過區域映射邏輯（Region Mapping Logic）將物理頁面轉換為邏輯頁面 `logical_page`。
     b. 呼叫 VU 0x405E 記錄初始 Bad Block Count (`BB_count`)。
     c. 呼叫 VU 0x40D6 獲取預測的下一個替換區塊 `next_replacement_block` (CE=0, Plane=0, Pool Type=1)。
     d. 構造 `PhysicalAddressInformation`，指定兩個失效目標：
        - Target 0: 當前邏輯區塊 `logical_VB` 的 `logical_page`。
        - Target 1: 預測替換區塊 `next_replacement_block` 的 Page 0。
     e. 呼叫 VU 0xC012 注入 Program Fail，`fail_type=3`，同時對上述兩個區塊/頁面注入寫入失敗。
   - 預期結果：VU 0xC012 執行成功，韌體內部狀態機已記錄這兩個特定的物理位置為 Program Fail 狀態，且系統未發生 Assert。

3. [Step1_TriggerFailAndVerifyBBT_Check]：
   - 動作：
     a. 執行 `Write10` 命令寫入 `api.WRITE_10_MAX_BLOCK_LEN` 長度資料至 LBA 0，觸發實際的寫入操作並引發預先注入的 Program Fail。
     b. 呼叫 VU 0x4013 獲取 BE (Block Error) Fail Status。
     c. 再次呼叫 VU 0x405E 獲取新的 Bad Block Count (`BB_count_new`) 及詳細 BBT 數據。
     d. 計算並比對 BBT 數據，檢查是否包含 `target_data_L2` (原始目標) 與 `target_data_replace` (替換目標)。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 2`，證明兩個注入的失效區塊均被正確計入 Bad Block Table。
     - BBT 數據中必須能找到與 `target_data_L2` (Block, CE, Plane) 完全匹配的條目。
     - BBT 數據中必須能找到與 `target_data_replace` (Block, CE, Plane) 完全匹配的條目。
     - 整個流程中無異常中斷，驗證韌體在 Early Replacement Pool 選擇失敗後，能正確更新 BB Table 並維持系統穩定。