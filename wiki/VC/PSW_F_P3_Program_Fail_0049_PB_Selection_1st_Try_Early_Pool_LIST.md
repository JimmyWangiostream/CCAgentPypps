# Test Spec: VC-30 (12.f) Program Fail Replacement Verification

## Verification Criterion (VC)
驗證韌體在「早期替換池 (Early Replacement Pool)」中選取新替換區塊 (PB) 並成功完成程式化 (Program) 後的硬體狀態一致性：
1. **替換機制觸發**：確認透過 Vendor Command `0xC012` 強制注入 Program Fail 錯誤後，韌體能正確識別該 LUN 的 LIST VB 區塊失效，並從早期替換池中選取下一個可用的 LIST VB (Next LIST VB) 作為新的替換目標。
2. **BBT 更新驗證**：確認在執行隨機寫入觸發替換流程後，Bad Block Table (BBT) 中的壞塊計數 (BB Count) 必須精確增加 1，且原失效區塊的物理地址 (CE/Plane/Block) 必須被正確標記為壞塊並記錄在 BBT 中。
3. **無 Assert 穩定性**：確認整個替換與寫入過程中，韌體未觸發 Assert 錯誤，系統保持正常運作。

## Test Case (TC) Checkpoints
1. [Case01_ListVB_Replacement_and_BBT_Update_Check]：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 讀取當前開機資訊，提取現有的 LIST VB 號碼 (`LIST_vb`)。
     2. 透過 Vendor Command `0x40DC` 讀取下一個可用的 LIST VB 號碼 (`LIST_vb_next`)，此為預期中的替換目標。
     3. 透過 Vendor Command `0x405E` 讀取初始壞塊計數 (`BB_count`) 並記錄。
     4. 建構 `PhysicalAddressInformation`，指定目標為 `LIST_vb_next` 所在的 Block/Page，並透過 Vendor Command `0xC012` 注入 `fail_type=0` (Program Fail) 錯誤，強制該區塊進入失效狀態。
     5. 進入迴圈執行隨機 Write10 指令 (長度為 `WRITE_10_MAX_BLOCK_LEN`)，每次寫入後透過 `0x40C1` 檢查 LIST VB 號碼是否發生變化。
     6. 當偵測到 LIST VB 號碼改變 (`LIST_vb_new != LIST_vb`) 時，停止寫入，代表替換成功。
     7. 透過 Vendor Command `0x4013` 讀取 BE (Block Error) 失敗狀態。
     8. 再次透過 Vendor Command `0x405E` 讀取新的壞塊資訊，計算新的壞塊計數 (`BB_count_new`) 並解析 BBT 資料 (`BB_data_new`)。
     9. 驗證 `BB_count_new` 是否等於 `BB_count + 1`，並搜尋 `BB_data_new` 中是否包含原注入失效區塊的物理地址資訊 (`target_data_LIST`)。
   - 預期結果：
     1. LIST VB 號碼必須發生改變，且新號碼應對應於步驟 2 中取得的 `LIST_vb_next`，證明韌體成功從早期替換池選取新 PB。
     2. 新的壞塊計數 `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明壞塊計數器正確更新。
     3. `BB_data_new` 中必須能找到與 `target_data_LIST` (原注入失效區塊的 CE, Plane, Block) 完全匹配的條目，證明該區塊已被正確標記為壞塊並記錄在 BBT 中。
     4. 整個流程未拋出 Assert 異常，測試正常結束。