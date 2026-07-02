# Test Spec: VC-38 (14.f) Program Fail Boundary Case - Early Replacement Pool Update Verification

## Verification Criterion (VC)
驗證在 UFS 韌體中，當透過 Vendor Command (VU C012) 強制在 L2 區域的 Early Replacement Pool 中注入 Program Fail 錯誤時，韌體能否正確識別該錯誤並執行 Bad Block Table (BBT) 更新機制。具體驗證目標為：
1. 確認在寫入觸發 Program Fail 後，BBT 中的 Bad Block 計數器 (BB Count) 必須精確增加 1。
2. 確認被標記為 Bad Block 的物理區塊資訊（包含 Logical VB、CE、Plane）必須準確反映在 VU 405E 回傳的 BBT 資料中。
3. 確認韌體在處理此異常時未觸發 Assert 或系統崩潰，證明韌體具備處理 Early Replacement Pool 中 Program Fail 的穩定性。

## Test Case (TC) Checkpoints
1. [PreProcess_FillSLC_Check]：
   - 動作：執行連續寫入操作（Write10, LBA=0, Length=16 bytes），直到 `get_open_vb_info` 回傳的 `TLC_L2.first_empty_physical_page` 數值大於或等於 3308。此步驟旨在填滿 SLC 區域，確保後續測試目標鎖定在 TLC L2 區域的 Early Replacement Pool。
   - 預期結果：寫入操作成功完成，且最終取得的 `physical_page` 指標進入預期的 TLC L2 範圍（>= 3308），為後續注入錯誤提供正確的物理地址基礎。

2. [Step1_InjectPF_EarlyReplacement_Check]：
   - 動作：
     a. 透過 VU 取得當前 Open VB 資訊，提取 `logical_VB` 與 `first_empty_physical_page`。
     b. 將 `physical_page` 轉換為對應的 `logical_page`，轉換邏輯嚴格依據硬體映射規則：若 `physical_page` < 1620 則除以 3；若 1620 <= `physical_page` < 1652 則 `(page-1620)//2 + 540`；若 1652 <= `physical_page` < 3308 則 `(page-1652)//3 + 1096`；若 3308 <= `physical_page` < 3312 則 `(page-3308)//1 + 1652`。
     c. 記錄注入前的 Bad Block 計數 (`BB_count`)。
     d. 透過 Vendor Command VU C012 注入 Program Fail 錯誤，設定參數為：`BlockInfoList_0_block` = `logical_VB`，`BlockInfoList_0_page` = 計算出的 `logical_page`，`fail_type=3` (Program Fail)。
     e. 執行一次大寫入操作 (`Write10`, LBA=0, Length=4096 bytes) 以觸發韌體對該頁面的寫入流程並捕捉錯誤。
     f. 透過 VU 4013 讀取 BE (Block Error) 狀態。
     g. 再次透過 VU 405E 讀取更新後的 Bad Block 資訊，並計算新的 `BB_count_new` 與解析 BBT 資料 (`BB_data_new`)。
   - 預期結果：
     a. `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明韌體正確識別並記錄了一個新的 Bad Block。
     b. 在 `BB_data_new` 中必須能找到一筆資料，其 `Block` 欄位等於注入時的 `logical_VB`，且 `CE` 為 0，`Plane` 為 0。
     c. 整個流程中韌體未發生 Assert 或系統重置，證明在 Early Replacement Pool 發生 Program Fail 時，韌體的錯誤處理路徑（Error Handling Path）是穩定且符合規範的。