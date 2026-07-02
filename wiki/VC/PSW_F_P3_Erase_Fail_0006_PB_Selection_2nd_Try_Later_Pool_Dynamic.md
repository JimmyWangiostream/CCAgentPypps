# Test Spec: VC-12 (2.g) Erase Fail with Replacement Pool Exhaustion Test

## Verification Criterion (VC)
驗證 UFS 韌體在快閃記憶體區塊管理與替換機制中的異常處理邏輯：
1. **預處理階段 (Pre-process)**：確認當預測的下一個替換區塊 (Next Replacement Block) 位於 Revoke Group (被撤銷/不可用區塊群組) 時，韌體能透過強制製造 L2 VB 的 Erase Fail (EF)，觸發 L2 VB 的切換，並驗證 Bad Block Table (BBT) 正確更新（BB Count +1 且目標區塊標記為 Bad）。此階段為循環邏輯，旨在消耗掉非 Revoke Group 的替換資源或確保測試環境處於特定狀態。
2. **主測試階段 (Step1)**：在 L2 VB 已切換的情境下，同時對「當前 L2 VB」與「預測的下一個替換區塊」注入 Erase Fail。驗證韌體在選擇新替換區塊失敗（因為預測區塊在 Revoke Group 或已失效）後，能否成功選擇新的替換區塊（或處理失敗），並嚴格驗證 BBT 中同時包含 L2 VB 與替換區塊的錯誤標記，且 BB Count 增加 2。此測試核心在於驗證當替換池資源受限或預測失效時，韌體對多重 Erase Fail 的容錯與 BBT 維護能力，且過程中不應發生 Assert 導致韌體崩潰。

## Test Case (TC) Checkpoints

1. [PreProcess_L2_EF_BBT_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 讀取當前 L2 Open VB (`L2_vb`)，透過 VU 40DC 讀取下一個 Open VB (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始 Bad Block Count (`BB_count`)。
     3. 透過 VU 40D6 讀取預測的下一個替換區塊 (`next_replacement_block`)。
     4. 若 `next_replacement_block` 不在 Revoke Group 中，則透過 VU C012 對 `L2_vb_next` 注入 Erase Fail (fail_type=1)。
     5. 執行連續 Write10 指令 (LUN 0, FUA=1)，直到 VU 40C1 回傳的 `L2_vb` 發生改變，確認 L2 VB 已切換。
     6. 透過 VU 4013 讀取 BE Fail Status，並透過 VU 405E 再次讀取 BBT 資訊。
     7. 計算新的 BB Count (`BB_count_new`) 並解析 BBT 資料。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - BBT 資料中必須包含目標區塊 (`L2_vb_next`) 的記錄，且其 CE/Plane/Block 資訊與注入時一致。
     - 若 `next_replacement_block` 在 Revoke Group 中，則跳過注入步驟，直接進入下一輪循環檢查，直到找到不在 Revoke Group 的替換區塊並完成上述驗證。

2. [Step1_Multi_EF_BBT_Integrity_Check]：
   - 動作：
     1. 獲取當前 L2 VB (`L2_vb`) 與下一個 Open VB (`L2_vb_next`)。
     2. 記錄初始 BB Count (`BB_count`)。
     3. 透過 VU 40D6 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. 透過 VU C012 同時對兩個區塊注入 Erase Fail (fail_type=1)：
        - Block 0: `L2_vb_next` (當前 L2 的下一個區塊)
        - Block 1: `next_replacement_block` (預測的替換區塊)
     5. 執行連續 Write10 指令 (LUN 0, FUA=1, skip_response_check=True)，直到 VU 40C1 回傳的 `L2_vb` 發生改變。
     6. 透過 VU 4013 讀取 BE Fail Status，並透過 VU 405E 讀取最終 BBT 資訊。
     7. 計算最終 BB Count (`BB_count_new`) 並解析 BBT 資料。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 2`。
     - BBT 資料中必須同時存在兩個目標區塊的記錄：
       1. `target_data_L2` (對應 `L2_vb_next`)
       2. `target_data_replace` (對應 `next_replacement_block`)
     - 韌體未發生 Assert 或崩潰，成功處理了雙重 Erase Fail 情境下的區塊標記與替換邏輯。