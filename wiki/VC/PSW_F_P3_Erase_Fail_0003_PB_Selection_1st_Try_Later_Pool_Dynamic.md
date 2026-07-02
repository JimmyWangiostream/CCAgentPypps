# Test Spec: VC-8 (1.g) Erase Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證韌體在遭遇 Erase Fail (EF) 時的壞塊管理與替換邏輯：
1. **正常替換流程**：當目標 L2 VB 區塊發生 Erase Fail 時，韌體必須正確更新 Bad Block Table (BBT)，將該區塊標記為壞塊，並確保 Bad Block Count (BB Count) 精確增加 1。
2. **替換區塊有效性**：透過 Vendor Command (VU 40D6) 查詢的「預測下一個替換區塊」必須位於正常的替換池（即不在 Revoke Block Group 中），代表韌體成功從動態替換池中選取了新的物理區塊作為 L2 VB 的載體。
3. **狀態一致性**：在 L2 VB 切換後，系統不應發生 Assert 或崩潰，且 BBT 數據必須與實際的壞塊狀態完全一致。

## Test Case (TC) Checkpoints

1. [Pre_Process_Loop_Validation]：
   - 動作：
     1. 透過 `get_VB_group` 獲取當前 Revoke Block Group 列表。
     2. 進入循環，首先透過 VU 40C1 獲取當前 L2 VB，透過 VU 40DC 獲取下一個預期的 L2 VB (`L2_vb_next`)。
     3. 透過 VU 405E 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 VU 40D6 (pool_type=1, next_n=1) 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     5. **判斷條件**：若 `next_replacement_block` 位於 Revoke Group 中，則執行 VU C012 在 `L2_vb_next` 注入 Erase Fail (fail_type=1)。
     6. 執行連續 Write10 操作 (LUN 0, FUA=1)，直到 VU 40C1 返回的 L2 VB 發生改變，確認韌體已觸發替換機制。
     7. 透過 VU 4013 檢查 BE Fail 狀態，並再次透過 VU 405E 驗證 BBT 更新：確認新的 `BB_count_new` 等於 `BB_count + 1`，且 `target_data_L2` (CE/Plane/Block) 存在於新的 BBT 數據中。
     8. 重複上述循環，直到 VU 40D6 返回的替換區塊**不**在 Revoke Group 中為止。
   - 預期結果：
     - 在循環過程中，每次注入 EF 後，BB Count 必須嚴格遞增 1。
     - 注入 EF 後的 L2 VB 必須發生跳變，證明替換機制生效。
     - 最終退出循環時，VU 40D6 返回的替換區塊必須是有效的（非 Revoke Block），證明韌體在多次壞塊替換後仍能從共享替換池中正確分配資源。

2. [Step1_EraseFail_BBT_Update_Check]：
   - 動作：
     1. 重置環境，獲取當前 L2 VB (`L2_vb`) 與下一個 L2 VB (`L2_vb_next`)。
     2. 記錄初始 BB Count (`BB_count`)。
     3. 透過 VU C012 在 `L2_vb_next` (CE=0, Plane=0) 強制注入 Erase Fail (fail_type=1)。
     4. 執行連續 Write10 操作 (LUN 0, FUA=1, `skip_response_check=True`)，直到 VU 40C1 返回的 L2 VB 改變 (`L2_vb_new != L2_vb`)。
     5. 透過 VU 4013 獲取 BE Fail 狀態。
     6. 透過 VU 405E 獲取更新後的 Bad Block Information，並使用 `program_fail_api.calculate_bbt` 解析 BBT 數據。
     7. 驗證 `BB_count_new` 是否等於 `BB_count + 1`。
     8. 在解析後的 BBT 數據中搜尋是否存在包含 `target_data_L2` (Block, CE, Plane) 的條目。
   - 預期結果：
     - 無 Assert 或系統崩潰。
     - `BB_count_new` 必須精確等於 `BB_count + 1`。
     - BBT 數據中必須能找到對應 `target_data_L2` 的壞塊記錄，證明韌體正確將發生 Erase Fail 的物理區塊標記為壞塊並更新內部表。

3. [Post_Process_CleanUp]：
   - 動作：執行 `open_card()` 恢復卡片狀態。
   - 預期結果：卡片成功恢復至可操作狀態，無殘留錯誤狀態。