# Test Spec: VC-51 (12.e) Program Fail in Hidden Area with New PB Selection

## Verification Criterion (VC)
驗證在 Hidden Area 情境下，當寫入操作觸發 Program Fail 時，韌體是否能正確識別故障區塊並選擇新的替換區塊（New PB）：Case 01 確認在預先注入 L2 區塊與 BBT 替換區塊的 Program Fail 後，執行連續寫入觸發失敗，韌體應自動更新 Bad Block Table (BBT)，將原 L2 區塊標記為 Bad，並將預先指定的 Next Replacement Block 納入 BBT 管理，且總 Bad Block 計數器應精確增加 2，同時韌體不應發生 Assert 崩潰。

## Test Case (TC) Checkpoints
1. [Case01_HiddenArea_PF_BBT_Update_Check]：
   - 動作：
     1. 執行 `pre_process` 進行連續寫入（Write10, LBA 0, Length 16），直到 TLC_L2 的第一個空閒物理頁面（first_empty_physical_page）達到或超過 1620，確保進入 Hidden Area 區域。
     2. 透過 VU 指令獲取當前 Open VB 資訊，提取 `logical_VB` 與 `physical_page`，並根據頁面範圍邏輯（<1620, <1652, <3308, <3312）計算對應的 `logical_page`。
     3. 記錄當前 Bad Block 計數器（BB_count）於 VU 405E 回應的前 4 位元組（Little Endian）。
     4. 透過 VU 40D6 查詢 CE=0, Plane=0, Pool Type=2 (Hidden Area) 的下一個預測替換區塊，解析出 `next_replacement_block`、`next_replacement_plane` 與 `next_replacement_ce`。
     5. 透過 VU C012 注入 Program Fail 錯誤，設定 `fail_type=3`，並指定兩個目標區塊資訊：
        - Block 0 (L2 Target): Die=0, Plane=0, Block=`logical_VB`, Page=`logical_page`。
        - Block 1 (BBT Target): Die=`next_replacement_ce`, Plane=`next_replacement_plane`, Block=`next_replacement_block`, Page=0。
     6. 執行 Write10 寫入（LUN 0, LBA 0, Length `api.WRITE_10_MAX_BLOCK_LEN`），觸發硬體 Program Fail。
     7. 透過 VU 4013 讀取 BE (Block Error) Fail 狀態。
     8. 再次透過 VU 405E 獲取新的 Bad Block 資訊，解析新的 BB 計數器（BB_count_new）與 BBT 列表（BB_data_new）。
   - 預期結果：
     1. 新的 Bad Block 計數器必須嚴格等於 `BB_count + 2`。
     2. BBT 列表中必須包含原 L2 目標區塊資訊（Block=`logical_VB`, CE=0, Plane=0）。
     3. BBT 列表中必須包含新的替換區塊資訊（Block=`next_replacement_block`, CE=`next_replacement_ce`, Plane=`next_replacement_plane`）。
     4. 整個流程中韌體未發生 Assert 或系統崩潰，證明韌體在 Hidden Area 發生 Program Fail 時，能正確執行 Bad Block 替換邏輯並更新內部 BBT 結構。