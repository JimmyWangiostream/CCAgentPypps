# Test Spec: UFS Bad Block Management & Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇強制 Erase Fail 情境下的壞塊標記機制與替換區塊（Replacement Block）分配邏輯：
1. **壞塊計數一致性**：確認在觸發特定 L2 VB 的 Erase Fail 後，透過 Vendor Command 405E 讀取的 Bad Block Count 必須精確增加 1，證明韌體正確識別並標記該區塊為 Bad。
2. **替換區塊映射正確性**：確認在 Erase Fail 發生前，韌體預測的下一個替換區塊（Predicted Next Replacement Block）在邏輯上對應的 L2 VB 號碼，必須與故障發生後該替換區塊實際持有的 L2 VB 號碼完全一致，證明替換區塊的邏輯映射（Logical Mapping）未被破壞且正確指向預期的備用區塊。

## Test Case (TC) Checkpoints
1. [Case01_BadBlockCount_Increment_Check]：
   - 動作：
     1. 透過 Vendor Command 40C1 讀取當前 L2 Open VB (`L2_vb`)，並透過 40DC 讀取下一個預期的 L2 VB (`L2_vb_next`)。
     2. 透過 Vendor Command 405E 記錄初始壞塊計數 (`BB_count`)。
     3. 建構 `PhysicalAddressInformation`，指定目標區塊為 `L2_vb_next` (Die 0, Plane 0)，並透過 Vendor Command C012 注入 `fail_type=1` (Erase Fail) 至該區塊。
     4. 執行連續 Write10 操作，直到 L2 Open VB 發生跳變（表示寫入進度超過故障區塊），確保故障狀態已寫入並觸發韌體處理流程。
     5. 再次透過 Vendor Command 405E 讀取新的壞塊計數 (`BB_count_new`)。
   - 預期結果：`BB_count_new` 必須嚴格等於 `BB_count + 1`。若不相等，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體未正確將受 C012 注入 Erase Fail 的區塊標記為壞塊。

2. [Case02_ReplacementBlock_Mapping_Integrity_Check]：
   - 動作：
     1. 在注入 C012 Erase Fail 後，透過 Vendor Command 40D6 查詢指定 Die/Plane 的下一個替換區塊物理地址 (`next_replacement_block`)。
     2. 透過 Vendor Command 40C9 查詢該 `next_replacement_block` 當前所對應的邏輯 VB 號碼 (`vb`)。
     3. 在寫入觸發 L2 VB 跳變後，再次透過 Vendor Command 40C9 查詢同一個 `next_replacement_block` 的邏輯 VB 號碼 (`vb_new`)。
   - 預期結果：`vb_new` 必須嚴格等於步驟 1 中讀取的 `L2_vb_next`。這證明儘管目標區塊 (`L2_vb_next`) 因 Erase Fail 被標記為壞塊，韌體所選定的替換區塊 (`next_replacement_block`) 仍然正確地持有該邏輯 VB 的數據或映射關係，未發生邏輯映射錯亂。若 `vb_new != L2_vb_next`，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。