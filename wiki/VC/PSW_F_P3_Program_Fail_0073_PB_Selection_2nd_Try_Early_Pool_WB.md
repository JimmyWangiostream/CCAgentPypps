# Test Spec: VC-34 (13.f) Program Fail Replacement & BB Table Update Verification

## Verification Criterion (VC)
驗證韌體在 Write Booster (WB) LUN 遭遇連續寫入失敗（Program Fail）時的替換區塊（Replacement Block）選擇邏輯與 Bad Block Table (BBT) 更新機制：
1. **替換邏輯驗證**：確認當 L2 VB 區塊（Write Booster 邏輯區塊）發生 Program Fail 時，韌體能正確從 Early Replacement Pool 中預測並選定下一個替換區塊（Next Replacement Block），且該區塊隨後也必須被標記為失效。
2. **BBT 一致性驗證**：確認在兩次 Program Fail 事件後，透過 Vendor Command 0x405E 讀取的 Bad Block Count 必須精確增加 2，且 BBT 數據中必須包含原始的 L2 VB 區塊與預測的替換區塊，證明韌體無 Assert 且正確更新了內部結構。

## Test Case (TC) Checkpoints
1. [Case01_BBT_Update_and_Replacement_Check]：
   - 動作：
     1. 配置 LUN 0 (Normal), LUN 1 (EM1), LUN 2 (WB) 並啟用 Write Booster。
     2. 透過 Vendor Command 0x40C1 讀取 Open VB 資訊，提取 `open_logical_VB_number_for_Write_Booster_WB_L2` 作為目標 L2 VB 區塊。
     3. 透過 Vendor Command 0x405E 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 Vendor Command 0x40D6 查詢 CE=0, Plane=0, Pool Type=1 (Early Replacement Pool) 的下一個預測替換區塊 (`next_replacement_block`)。
     5. 透過 Vendor Command 0xC012 注入 Program Fail 錯誤，同時標記 L2 VB 區塊與 `next_replacement_block` 為失效（Fail Type 0）。
     6. 對 LUN 2 (WB LUN) 的 LBA 0 執行 Write10 寫入操作（長度為 `WRITE_10_MAX_BLOCK_LEN`），觸發硬體寫入失敗流程。
     7. 透過 Vendor Command 0x4013 讀取 BE (Bad Event) Fail Status。
     8. 再次透過 Vendor Command 0x405E 讀取新的 Bad Block Count (`BB_count_new`) 及 BBT 數據 (`BB_data_new`)。
     9. 驗證 `BB_count_new` 是否等於 `BB_count + 2`，並檢查 `BB_data_new` 中是否包含 L2 VB 區塊與替換區塊的詳細資訊（Block, CE, Plane）。
   - 預期結果：
     1. `BB_count_new` 必須嚴格等於 `BB_count + 2`，代表兩個區塊（L2 VB 與替換區塊）均被正確計入 Bad Block。
     2. `BB_data_new` 列表中必須能找到與 `target_data_L2`（原始 L2 VB 區塊）完全匹配的條目。
     3. `BB_data_new` 列表中必須能找到與 `target_data_replace`（預測替換區塊）完全匹配的條目。
     4. 測試過程中韌體不得發生 Assert 或崩潰，證明在 WB LUN 發生 Program Fail 並觸發替換機制時，BBT 更新邏輯正確且系統穩定。