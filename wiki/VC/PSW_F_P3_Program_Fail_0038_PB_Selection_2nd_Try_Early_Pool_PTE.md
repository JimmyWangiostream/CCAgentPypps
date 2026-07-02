# Test Spec: VC-34 (13.f) Program Fail Injection & Early Replacement Pool Verification

## Verification Criterion (VC)
驗證韌體在遭遇程式化失敗（Program Fail, PF）時的錯誤處理與替換機制：
1. **BBT 更新驗證**：確認在透過 Vendor Command `0xC012` 強制注入 PTE VB 及其對應的 Early Replacement Pool (ERP) 替換區塊（Next Replacement Block）的 PF 狀態後，韌體能正確識別並更新 Bad Block Table (BBT)。具體指標為：透過 `VU 0x405E` 讀取的 BB Count 必須精確增加 2（分別對應 PTE 與替換區塊），且 BBT 資料中必須包含這兩個特定物理地址（CE/Plane/Block）。
2. **無 Assert 穩定性驗證**：確認在觸發上述雙重 PF 情境並完成 BBT 更新後，韌體不會觸發 Assert 錯誤或系統崩潰，證明韌體具備處理 PTE 層級 PF 並從 ERP 池獲取替換區塊的健壯性。
3. **PTE 遷移邏輯驗證**：透過持續寫入直到 PTE VB 號碼變更，確保測試環境處於正常的 PTE 輪替狀態，從而驗證在 PTE 發生 PF 時，韌體是否能正確切換至新的 PTE 並維持系統運作。

## Test Case (TC) Checkpoints
1. [Case01_BBT_Update_and_No_Assert_Check]：
   - 動作：
     1. 透過 `VU 0x40C1` 讀取當前 PTE VB 號碼 (`PTE_vb`)，並透過 `VU 0x40DC` 讀取下一個 PTE VB (`PTE_vb_next`)。
     2. 透過 `VU 0x405E` 記錄初始 Bad Block Count (`BB_count`)。
     3. 透過 `VU 0x40D6` (pool_type=1, 代表 Early Replacement Pool) 讀取預測的下一個替換區塊號碼 (`next_replacement_block`)。
     4. 建構 `PhysicalAddressInformation`，指定 CE=0, Plane=0，並同時設定 `BlockInfoList_0` 為 `PTE_vb_next`，`BlockInfoList_1` 為 `next_replacement_block`。
     5. 發送 Vendor Command `0xC012` (fail_type=0, 代表 Program Fail)，強制將上述兩個區塊標記為 PF。
     6. 執行迴圈寫入 (Write10, LUN=0, FUA=1)，直到透過 `VU 0x40C1` 確認 PTE VB 號碼發生變更 (`PTE_vb_new != PTE_vb`)，確保 PTE 已遷移。
     7. 發送 `VU 0x4013` 獲取 BE (Bad Endurance) Fail 狀態。
     8. 再次發送 `VU 0x405E` 獲取新的 Bad Block Count (`BB_count_new`) 及 BBT 資料 (`BB_data_new`)。
     9. 驗證 `BB_count_new` 是否等於 `BB_count + 2`。
     10. 在 `BB_data_new` 中搜尋是否包含目標 PTE 區塊 (`PTE_vb_next`) 與目標替換區塊 (`next_replacement_block`) 的物理地址資訊。
   - 預期結果：
     1. 程式執行過程中未發生 Assert 或異常中斷。
     2. `BB_count_new` 必須精確等於 `BB_count + 2`。
     3. `BB_data_new` 中必須存在一筆記錄，其 Block/CE/Plane 與 `PTE_vb_next` 完全匹配。
     4. `BB_data_new` 中必須存在另一筆記錄，其 Block/CE/Plane 與 `next_replacement_block` 完全匹配。
     5. 這代表韌體成功將注入的 PF 區塊納入 BBT，並正確處理了 PTE 層級的錯誤，未導致系統崩潰。