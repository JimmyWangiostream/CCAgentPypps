# Test Spec: VC-35 (13.g) Program Fail with Replacement Block Failure Recovery Test

## Verification Criterion (VC)
驗證韌體在「正常區域寫入」且「預測的替換區塊（Replacement Block）同時發生程式失敗」之極端情境下的錯誤處理機制：
1.  **預處理階段**：透過 Vendor Command (VU C012) 強制在 EM1 LUN 的當前 L2 VB 下一個 VB 注入 Erase Fail，並透過連續寫入觸發 L2 VB 切換，確認該目標區塊被正確標記為 Bad Block 並加入 BBT，且 BB Count 增加 1。此循環重複直到預測的替換區塊落入 Revoke Group（確保後續測試環境乾淨）。
2.  **主測試階段 (Step 1)**：針對 EM1 LUN 寫入資料，同時注入「當前 L2 VB」與「預測的下一個替換區塊」的 Program Fail。驗證韌體是否能正確識別雙重失敗，將這兩個區塊均標記為 Bad Block（BB Count 應增加 2），並確認 BBT 中同時包含這兩個目標區塊。
3.  **核心驗證點**：確認韌體在替換區塊也失效的情況下，仍能正確更新 BB Table，且不會觸發 Assert 或系統崩潰，證明韌體具備處理替換資源枯竭或連續失敗的魯棒性。

## Test Case (TC) Checkpoints

1.  [PreProcess_EraseFail_L2_VB_Switch_Check]：
    -   動作：
        1.  配置 LUN 0 為 Normal，LUN 1 (EM1) 為 EM1。
        2.  在 EM1 LUN (LUN 1) 寫入 4KB 資料以初始化狀態。
        3.  獲取當前 Revoke Group 列表。
        4.  進入循環：
            a. 透過 VU 40C1 獲取當前 L2 VB (`L2_vb`)，透過 VU 40DC 獲取下一個 L2 VB (`L2_vb_next`)。
            b. 透過 VU 405E 記錄當前 BB Count (`BB_count`)。
            c. 透過 VU 40D6 獲取預測的下一個替換區塊 (`next_replacement_block`)。
            d. 若 `next_replacement_block` 不在 Revoke Group 中，則透過 VU C012 對 `L2_vb_next` 注入 Erase Fail (`fail_type=1`)。
            e. 在 Normal LUN (LUN 0) 進行連續寫入，直到 L2 VB 發生切換 (`L2_vb_new != L2_vb`)。
            f. 透過 VU 4013 獲取 BE Fail 狀態。
            g. 透過 VU 405E 獲取新 BB Count (`BB_count_new`) 並計算 BBT。
            h. 驗證 `BB_count_new == BB_count + 1` 且 BBT 中包含被注入 Erase Fail 的 `L2_vb_next` 區塊。
        5.  重複上述循環直到 `next_replacement_block` 落在 Revoke Group 中為止。
    -   預期結果：
        -   每次循環中，BB Count 必須精確增加 1。
        -   BBT 中必須包含被注入 Erase Fail 的區塊。
        -   韌體無 Assert 或異常退出。
        -   最終狀態確保預測的替換區塊已失效（在 Revoke Group），為 Step 1 的雙重失敗測試做準備。

2.  [Step1_Dual_ProgramFail_BBTable_Update_Check]：
    -   動作：
        1.  透過 VU 40C1 獲取 EM1 LUN 的當前 L2 VB (`L2_vb`)。
        2.  透過 VU 405E 記錄當前 BB Count (`BB_count`)。
        3.  透過 VU 40D6 獲取預測的下一個替換區塊 (`next_replacement_block`)。
        4.  透過 VU C012 同時注入兩個 Program Fail (`fail_type=0`)：
            -   目標 1：當前 L2 VB (`L2_vb`)。
            -   目標 2：預測的替換區塊 (`next_replacement_block`)。
        5.  在 EM1 LUN (LUN 1) 寫入 4KB 資料，並設定 `skip_response_check=True` 以允許寫入失敗。
        6.  透過 VU 4013 獲取 BE Fail 狀態。
        7.  透過 VU 405E 獲取新 BB Count (`BB_count_new`) 並計算 BBT。
        8.  驗證 BB Count 變化及 BBT 內容。
    -   預期結果：
        -   BB Count 必須精確增加 2 (`BB_count_new == BB_count + 2`)。
        -   BBT 中必須同時包含「當前 L2 VB」與「預測的替換區塊」這兩個目標區塊。
        -   韌體未觸發 Assert，系統保持穩定，證明在替換區塊也失效的情況下，韌體仍能正確更新 BB Table 並處理錯誤。