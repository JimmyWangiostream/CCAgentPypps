# Test Spec: VC-52 (12.f) Program Fail Injection & BB Table Update Verification

## Verification Criterion (VC)
驗證韌體在 MLC 正常區域發生程式化失敗（Program Fail）時的錯誤處理與壞塊管理機制：
1. **壞塊標記更新**：透過 Vendor Command (VU) C012 在指定的 L2 Logical VB 的特定 Logical Page 注入程式化失敗（fail_type=3），確認韌體能正確識別該物理區塊為壞塊，並將其加入 Bad Block Table (BBT)。
2. **BBT 一致性檢查**：比較注入前後的 Bad Block Count，確認計數器精確增加 1，且 BBT 數據中確實包含被注入失敗的 Target Block (CE=0, Plane=0, Block=Logical_VB)。
3. **系統穩定性**：確認在觸發程式化失敗並更新 BBT 後，韌體未發生 Assert 或崩潰，且能繼續正常處理後續的 Write10 指令（儘管該次寫入可能失敗或重定向，但腳本重點在於 BBT 的更新驗證）。

## Test Case (TC) Checkpoints
1. [PreProcess_FillToFirstEmptyMLCPage]：
   - 動作：執行迴圈寫入 16 字節資料（LBA 0, Length 16）至 LUN 0，持續直到 `get_open_vb_info` 返回的 `TLC_L2.first_empty_physical_page` 大於等於 1620。此步驟旨在填充快閃記憶體，確保後續測試目標位於已使用的 MLC 區域而非未初始化的空閒區。
   - 預期結果：系統持續接受寫入指令，無錯誤回報，直到達到預設的物理頁面閾值，確保測試環境處於「正常區域且已填充」的狀態。

2. [Step1_GetBaselineInfo]：
   - 動作：
     1. 呼叫 `get_open_vb_info` 取得當前 `logical_VB` 與 `first_empty_physical_page`。
     2. 呼叫 VU 405E 取得初始壞塊計數 `BB_count`。
     3. 根據 `physical_page` 的範圍（<1620, <1652, <3308, <3312）及對應的 `region_max_wl` 參數，將物理頁面轉換為邏輯頁面 `logical_page`。
     4. 設定目標區塊資訊：CE=0, Plane=0, Block=`logical_VB`, Page=`logical_page`。
   - 預期結果：成功解析出目標測試區塊的邏輯地址，並記錄初始壞塊數量作為基準值。

3. [Step1_InjectProgramFail]：
   - 動作：
     1. 構造 `PhysicalAddressInformation` 結構體，填入上述計算出的邏輯區塊與頁面資訊。
     2. 呼叫 `issue_C012_to_create_program_erase_fail`，設定 `fail_type=3`（代表 Program Fail），針對目標 L2 Logical VB 的特定頁面注入程式化失敗。
     3. 記錄目標區塊資訊 `target_data_L2` 以供後續比對。
   - 預期結果：韌體接收 VU C012 指令，並在內部模擬或觸發該頁面的程式化失敗狀態，準備進行壞塊標記流程。

4. [Step1_TriggerWriteAndCheckBEStatus]：
   - 動作：
     1. 發送標準 Write10 指令（LUN 0, LBA 0, Length=Max Block Len, FUA=1）。
     2. 呼叫 `issue_4013_to_get_BE_fail_status` 查詢 Backend 失敗狀態。
   - 預期結果：Write10 指令執行完畢（無論成功或失敗，腳本未檢查寫入結果碼，僅關注後續 BBT 狀態）；VU 4013 成功返回，確認系統處於可查詢錯誤狀態的穩定階段。

5. [Step1_VerifyBBTUpdate]：
   - 動作：
     1. 再次呼叫 VU 405E 取得新的壞塊計數 `BB_count_new` 及壞塊數據 `BB_data_new`。
     2. 計算 `BB_data_new` 中的壞塊列表。
     3. 驗證條件 A：`BB_count_new` 必須等於 `BB_count + 1`。
     4. 驗證條件 B：在 `BB_data_new` 中搜尋是否存在包含 `target_data_L2` (Block=`logical_VB`, CE=0, Plane=0) 的項目。
   - 預期結果：
     - 壞塊計數精確增加 1，證明韌體正確識別並標記了一個新的壞塊。
     - BBT 數據中確實包含被注入失敗的目標區塊，證明壞塊表更新機制運作正常，且目標區塊已被正確標記為 Bad Block。
     - 若任一條件失敗，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。