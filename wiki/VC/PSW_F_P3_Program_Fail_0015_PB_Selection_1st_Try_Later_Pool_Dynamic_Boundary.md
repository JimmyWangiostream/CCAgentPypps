# Test Spec: VC-39 (14.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生 Program Fail 時的替換區塊（Replacement Block）選擇邏輯與 Bad Block Table (BBT) 更新機制：
1. **預處理階段**：確認韌體在選擇替換區塊時，會優先排除處於 Revoke Group 的區塊。若預測的下一個替換區塊位於 Revoke Group，則透過注入 Erase Fail 強制該區塊失效，並透過寫入操作觸發 L2 VB 切換，確保後續測試目標區塊不在 Revoke Group 內。
2. **主測試階段**：針對當前 L2 VB 的第一個空餘物理頁（First Empty Physical Page）注入 Program Fail (`fail_type=3`)，隨後執行寫入操作。
3. **驗證目標**：確認韌體正確識別 Program Fail，將目標 L2 VB 標記為 Bad Block，BB Count 增加 1，且 BBT 中正確記錄該 CE/Plane/Block 資訊；同時驗證韌體未因錯誤而 Assert，並成功選擇新的替換區塊（由 `40D6` 指令預測，且該區塊不在 Revoke Group 中）。

## Test Case (TC) Checkpoints

1. [PreProcess_RevokeGroup_Exclusion_Check]：
   - 動作：
     1. 透過 `issue_40C1` 與 `issue_40DC` 獲取當前 L2 VB (`L2_vb`) 與下一個 L2 VB (`L2_vb_next`)。
     2. 透過 `issue_405E` 記錄初始 BB Count。
     3. 透過 `issue_40D6` 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. 若 `next_replacement_block` 屬於 Revoke Group，則透過 `issue_C012` (fail_type=1, Erase Fail) 在 `L2_vb_next` 注入 Erase Fail。
     5. 執行連續 Write10 操作，直到 `issue_40C1` 返回的 L2 VB 發生改變（表示 L2 VB 已切換至新的區塊）。
     6. 重複上述流程，直到 `issue_40D6` 返回的預測替換區塊**不**在 Revoke Group 中為止。
     7. 在第二個 `while True` 循環中，執行連續 Write10 (16 Bytes) 直到 `first_empty_physical_page` >= 3308，確保測試環境處於特定的 SLC 頁面邊界狀態。
   - 預期結果：
     - 韌體成功排除 Revoke Group 中的區塊作為替換目標。
     - 透過 Erase Fail 強制失效區塊後，L2 VB 成功切換，確保後續測試的 `logical_VB` 是有效的、非 Revoke 的區塊。
     - 最終狀態滿足 `physical_page >= 3308` 的邊界條件，為後續 L2 Program Fail 測試準備環境。

2. [Step1_ProgramFail_L2_Replacement_Check]：
   - 動作：
     1. 獲取當前 L2 VB (`logical_VB`) 與 First Empty Physical Page。
     2. 根據物理頁碼範圍（<1620, <1652, <3308, <3312）及 `region_max_wl` 映射表，計算對應的 Logical Page。
     3. 透過 `issue_C012` (fail_type=3, Program Fail) 在目標 L2 VB 的計算出的 Logical Page 注入 Program Fail。
     4. 記錄目標區塊資訊 (`target_data_L2`: CE=0, Plane=0, Block=logical_VB)。
     5. 執行 Write10 (4KB) 操作，並設置 `skip_response_check=True` 以允許韌體處理 Fail 而不立即返回錯誤給 Host。
     6. 透過 `issue_4013` 獲取 BE (Block Error) Fail Status。
     7. 透過 `issue_405E` 獲取新的 BB Count 與 BBT 數據。
   - 預期結果：
     - **BB Count 驗證**：新的 BB Count (`BB_count_new`) 必須等於初始 BB Count + 1。
     - **BBT 驗證**：`program_fail_api.calculate_bbt` 解析出的 BBT 數據中，必須包含 `target_data_L2` 所指定的 CE/Plane/Block 組合，證明韌體已正確將該 L2 VB 標記為 Bad Block。
     - **無 Assert**：韌體在處理 Program Fail 並更新 BBT 的過程中未發生 Assert 或系統崩潰，測試流程順利進入 `post_process`。
     - **替換邏輯**：韌體內部已根據 Program Fail 觸發替換機制，選擇了新的替換區塊（此邏輯由 VC 描述保證，測試側重點在於 BBT 更新與 BB Count 的正確性）。