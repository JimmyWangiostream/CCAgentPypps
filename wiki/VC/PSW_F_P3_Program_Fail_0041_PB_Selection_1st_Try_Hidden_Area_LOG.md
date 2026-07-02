# Test Spec: VC-29 (12.e) Hidden Area Program Fail with New PB Selection

## Verification Criterion (VC)
驗證在 Hidden Area 情境下，當韌體預測並選擇新的替換區塊（New PB）後，若該 New PB 發生 Program Fail，韌體應能正確更新 Bad Block Table (BBT) 且不觸發 Assert 異常。具體驗證邏輯為：透過 Vendor Command 強制在 LOG VB 的下一個區塊（Next LOG VB）與預測的 New PB 上注入 Program Fail，隨後執行隨機寫入觸發 LOG VB 切換，確認 BBT 中同時標記原 LOG 區塊與 New PB 為 Bad Block，且 Bad Block Count 精確增加 2，證明韌體在處理隱藏區替換區塊失敗時，BBT 更新機制運作正常且系統穩定。

## Test Case (TC) Checkpoints
1. [Case01_Hidden_Area_Program_Fail_BBT_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 讀取當前 LOG VB 號碼（LOG_vb），並透過 VU 40DC 讀取下一個預期的 LOG VB 號碼（LOG_vb_next）。
     2. 透過 VU 405E 記錄初始 Bad Block Count（BB_count）。
     3. 透過 VU 40D6 查詢 Hidden Area 的預測替換區塊（Next Replacement Block），解析出對應的 CE、Plane 與 Block 號碼（next_replacement_ce/plane/block）。
     4. 透過 VU C012 建立 Program Fail 情境：
        - 目標 1：將 LOG_vb_next 設定為 Fail 目標（模擬 LOG 切換時的 Program Fail）。
        - 目標 2：將預測的 New PB（next_replacement_ce/plane/block）設定為 Fail 目標（模擬替換區塊的 Program Fail）。
        - 設定 fail_type=0，block_info_list_count=2。
     5. 執行無限迴圈的 Write10 隨機寫入（長度為 WRITE_10_MAX_BLOCK_LEN），直到 VU 40C1 回傳的 LOG_vb 發生改變（LOG_vb_new != LOG_vb），強制觸發 LOG 切換流程。
     6. 透過 VU 4013 讀取 BE Fail Status。
     7. 透過 VU 405E 再次讀取 Bad Block Count（BB_count_new）並解析 BBT 資料。
     8. 驗證 BB_count_new 是否等於 BB_count + 2，並檢查 BBT 中是否包含原 LOG_vb_next 與 New PB 的物理地址資訊。
   - 預期結果：
     1. Bad Block Count 必須精確增加 2（BB_count_new == BB_count + 2），代表 LOG 區塊與 New PB 均被正確標記為 Bad Block。
     2. BBT 資料中必須能找到 target_data_LOG（即 LOG_vb_next 的 CE/Plane/Block）與 target_data_BBT（即 New PB 的 CE/Plane/Block），確認兩者均已進入 Bad Block 列表。
     3. 測試過程未觸發 Assert 或系統崩潰，證明韌體在 Hidden Area 替換區塊失敗時能穩定處理並更新 BBT。