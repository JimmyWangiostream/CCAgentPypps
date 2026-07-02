# Test Spec: UFS Program/Erase Fail Handling with Early Replacement Pool Update

## Verification Criterion (VC)
驗證韌體在遭遇 Erase Fail (EF) 情境下的 Bad Block Table (BBT) 更新機制與 Early Replacement Pool 管理邏輯：
1. **錯誤注入與狀態確認**：透過 Vendor Command (VU C012) 強制在 L2 Open VB 及其對應的 Next Replacement Block 上產生 Erase Fail，確認韌體能正確識別並標記這兩個實體區塊為失效。
2. **BBT 一致性驗證**：在寫入觸發 VB 切換後，檢查 Bad Block Information (VU 405E) 中的 BB Count 是否精確增加 2，且 BBT 資料中必須包含被注入失效的 L2 VB 與 Next Replacement Block 的完整物理地址資訊 (CE/Plane/Block)。
3. **無 Assert 穩定性**：確認在上述異常處理流程中，韌體未觸發 Assert 錯誤，系統保持穩定運作。

## Test Case (TC) Checkpoints
1. [Case01_EF_Injection_and_BBT_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 讀取當前 L2 Open VB (`L2_vb`)，並透過 VU 40DC 讀取下一個預期的 L2 VB (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始 Bad Block Count (`BB_count`)。
     3. 透過 VU 40D6 查詢 Early Replacement Pool 中的下一個替換區塊 (`next_replacement_block`)。
     4. 呼叫 `issue_C012_to_create_program_erase_fail`，設定 `fail_type=1` (Erase Fail)，並同時針對 `L2_vb_next` (作為目標 L2) 與 `next_replacement_block` (作為其替換塊) 注入 Erase Fail 錯誤。
     5. 執行連續 Write10 指令，直到 VU 40C1 回傳的 `L2_vb_new` 發生變化（表示 VB 已切換，觸發了相關的韌體狀態機更新）。
     6. 再次呼叫 VU 405E 獲取新的 Bad Block Count (`BB_count_new`) 及 BBT 詳細資料 (`BB_data_new`)。
     7. 驗證 `BB_count_new` 是否等於 `BB_count + 2`。
     8. 在 `BB_data_new` 中搜尋是否包含被注入失效的 `L2_vb_next` (CE:0, Plane:0) 與 `next_replacement_block` (CE:0, Plane:0) 的實體地址。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 2`，代表韌體正確識別並記錄了兩個新的失效區塊。
     - `BB_data_new` 中必須存在兩筆記錄，分別對應 `L2_vb_next` 與 `next_replacement_block` 的物理地址，代表 BBT 已正確更新以反映這些區塊的失效狀態。
     - 整個流程執行完畢後未拋出 Assert 異常，代表韌體在處理 Erase Fail 及替換區塊標記時邏輯正確且穩定。