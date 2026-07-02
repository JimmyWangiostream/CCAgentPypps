# Test Spec: VC-29 (12.e) Program Fail in Hidden Area with New PB Selection

## Verification Criterion (VC)
驗證在 Hidden Area 情境下，當 PTE (Program Target Entry) 與 BBT (Bad Block Table) 目標區塊同時遭遇 Program Fail 時，韌體能否正確識別並選擇新的替換區塊 (New PB)：
1. **BB Table 更新驗證**：確認韌體在遭遇 Program Fail 後，能正確將原始的 PTE 區塊與 BBT 區塊標記為 Bad Block，且 Bad Block 總計數 (BB Count) 嚴格增加 2。
2. **BBT 內容完整性驗證**：確認透過 Vendor Command 讀取的 BBT 資料中，確實包含了被標記為失效的 PTE 區塊與 BBT 區塊的物理地址資訊 (CE, Plane, Block)。
3. **無 Assert 穩定性驗證**：確認在觸發 Program Fail 並執行隨機寫入直到 PTE VB 號碼變更的過程中，韌體未觸發 Assert 錯誤，且能順利完成狀態遷移。

## Test Case (TC) Checkpoints
1. [Case01_BBTable_Update_and_BBT_Integrity_Check]：
   - 動作：
     1. 透過 Vendor Command `VU 40C1` 讀取當前 PTE VB 號碼 (`PTE_vb`)，並透過 `VU 40DC` 讀取下一個 PTE VB 號碼 (`PTE_vb_next`)。
     2. 透過 `VU 405E` 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 `VU 40D6` (pool_type=2, is_CIS=0, pf_on_open_data=0) 預測並獲取下一個可用的替換區塊 (`next_replacement_block`) 及其 CE/Plane 資訊。
     4. 建構 `PhysicalAddressInformation`，設定 `BlockInfoList_0` 為 `PTE_vb_next` (CE=0, Plane=0)，`BlockInfoList_1` 為預測的替換區塊。
     5. 發送 Vendor Command `VU C012` (fail_type=0) 強制在 `PTE_vb_next` 與替換區塊上注入 Program Fail。
     6. 執行無限迴圈的 `Write10` 隨機寫入 (LUN 0, 長度 `WRITE_10_MAX_BLOCK_LEN`)，每次寫入後透過 `VU 40C1` 檢查 PTE VB 號碼。當 `PTE_vb_new` 不等於初始 `PTE_vb` 時停止迴圈，代表韌體已選擇新的 PTE。
     7. 發送 `VU 4013` 獲取 BE (Bad Entry) Fail 狀態。
     8. 再次發送 `VU 405E` 獲取新的 Bad Block 資訊，計算新的 BB 計數 (`BB_count_new`) 並解析 BBT 資料 (`BB_data_new`)。
   - 預期結果：
     1. **BB Count 驗證**：`BB_count_new` 必須嚴格等於 `BB_count + 2`。這代表韌體正確識別了兩個失效區塊 (PTE 目標與替換目標) 並將其加入 Bad Block 列表。
     2. **PTE BBT 條目驗證**：在 `BB_data_new` 中必須能找到一筆資料，其 CE、Plane、Block 欄位完全匹配 `target_data_PTE` (即注入 Fail 的 `PTE_vb_next`)。
     3. **BBT BBT 條目驗證**：在 `BB_data_new` 中必須能找到一筆資料，其 CE、Plane、Block 欄位完全匹配 `target_data_BBT` (即注入 Fail 的替換區塊)。
     4. **系統穩定性**：整個流程中未觸發 Assert，且 PTE VB 號碼成功發生變更，證明韌體在 Hidden Area Program Fail 情境下能正確更新 BB Table 並選擇新的 PB，無邏輯錯誤。