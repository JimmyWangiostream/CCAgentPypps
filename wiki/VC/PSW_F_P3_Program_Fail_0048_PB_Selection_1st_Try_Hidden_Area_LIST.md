# Test Spec: UFS Program Fail Handling in Hidden Area (VC-29)

## Verification Criterion (VC)
驗證韌體在 Hidden Area（隱藏區）發生 Program Fail 時的錯誤處理與備用區塊替換機制：
1. **BBT 更新正確性**：確認當 LIST VB 與 BBT 對應的備用區塊同時遭遇 Program Fail 時，韌體能正確識別並標記這兩個區塊為 Bad Block，使 Bad Block Count (BB Count) 精確增加 2。
2. **替換邏輯有效性**：確認韌體在 LIST VB 失效後，能成功從預先預測的備用區塊池（Pool Type 2, Hidden Area）中選取新的 LIST VB，且該替換過程無需重複嘗試（First Try Succeed），並確保新的 LIST VB 與舊的 LIST VB 不同。
3. **系統穩定性**：確認在此異常流程中，韌體不會觸發 Assert 或崩潰，且能透過 Vendor Command 正確讀取並驗證更新後的 Bad Block Table (BBT) 數據。

## Test Case (TC) Checkpoints
1. [Case01_BBT_Update_and_List_Replacement_Check]：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 讀取當前 Open VB 資訊，提取初始 LIST VB 號碼 (`LIST_vb`)。
     2. 透過 Vendor Command `0x40DC` 讀取下一個 Open VB 資訊，提取目標 LIST VB (`LIST_vb_next`)。
     3. 透過 Vendor Command `0x405E` 讀取初始 Bad Block Count (`BB_count`)。
     4. 透過 Vendor Command `0x40D6` 預測下一個備用區塊 (`next_replacement_block`)，解析其 CE、Plane 與 Block 號碼。
     5. 透過 Vendor Command `0xC012` 注入 Program Fail 錯誤，指定兩個目標：
        - 目標 1：`LIST_vb_next` (對應 LIST 區域)。
        - 目標 2：`next_replacement_block` (對應 BBT 區域)。
        - 設定 `fail_type=0`。
     6. 進入迴圈執行隨機 Write10 指令（長度為 `WRITE_10_MAX_BLOCK_LEN`），每次寫入後透過 `0x40C1` 檢查 LIST VB 是否發生變化。
     7. 當 `LIST_vb_new != LIST_vb` 時跳出迴圈，代表 LIST 替換成功。
     8. 透過 Vendor Command `0x4013` 讀取 BE (Bad Event) Fail Status。
     9. 再次透過 Vendor Command `0x405E` 讀取新的 Bad Block Count (`BB_count_new`) 及 BBT 數據 (`BB_data_new`)。
     10. 驗證 `BB_count_new` 是否等於 `BB_count + 2`，並檢查 `BB_data_new` 中是否包含原目標 LIST 區塊與原目標 BBT 區塊的記錄。
   - 預期結果：
     - LIST VB 必須發生跳變（`LIST_vb_new` 不等於 `LIST_vb`），證明韌體成功選取了新的 LIST VB。
     - 新的 Bad Block Count (`BB_count_new`) 必須嚴格等於初始 Count 加 2，證明 LIST 區塊與 BBT 區塊均被正確標記為 Bad。
     - `BB_data_new` 中必須能找到原 `LIST_vb_next` 的 CE/Plane/Block 資訊，以及原 `next_replacement_block` 的 CE/Plane/Block 資訊，證明 BBT 表單已正確更新這兩個區塊的狀態。
     - 整個流程中無 Assert 或異常中斷，證明韌體在 Hidden Area 的 Program Fail 處理邏輯穩定且符合規範。