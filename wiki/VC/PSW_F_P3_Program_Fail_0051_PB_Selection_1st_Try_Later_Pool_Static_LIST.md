# Test Spec: VC-32 (12.h) Program Fail Replacement & Assert Behavior Test

## Verification Criterion (VC)
驗證韌體在快閃記憶體程式/擦除失敗（Program/Erase Fail, PF）情境下的區塊替換機制與錯誤處理邏輯：
1. **Normal Area (L2) Replacement**: 驗證當 L2 (Logical to Physical mapping area) 的下一個開放區塊（Next Open VB）被強制注入擦除失敗（Erase Fail, EF）時，韌體應能透過連續寫入觸發 L2 VB 切換，並正確將該失效區塊標記為 Bad Block。預期結果為 Bad Block Table (BBT) 計數增加 1，且失效區塊資訊正確記錄於 BBT 中，代表韌體成功執行區塊替換並更新 BB Table。
2. **LIST Area Replacement & Assert**: 驗證當 LIST (List-based mapping area) 的下一個開放區塊被強制注入程式失敗（Program Fail, PF）時，韌體應進入錯誤處理流程。預期結果為裝置進入非回應狀態並觸發韌體 Assert 0x203（代表 Device remains unresponsive after initialization），且 LIST VB 號碼不應發生改變，確認韌體未進入 Read-Only 模式，而是處於特定的 Assert 掛起狀態以進行後續診斷或恢復。

## Test Case (TC) Checkpoints

1. **[Case01_L2_EF_Replacement_Check]**：
   - 動作：
     1. 透過 Vendor Command (VU) 40C1 讀取當前 L2 Open VB (`L2_vb`)，並透過 VU 40DC 讀取下一個 L2 Open VB (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 VU 40D6 確認替換區塊池狀態。
     4. 使用 Vendor Command (VU) C012 針對 `L2_vb_next` (CE=0, Plane=0) 注入擦除失敗 (`fail_type=1`)。
     5. 執行連續 Write10 指令，直到 VU 40C1 返回的 L2 Open VB 發生變化（`L2_vb_new != L2_vb`），表示 L2 已切換至新區塊。
     6. 再次透過 VU 405E 讀取新的 Bad Block 計數 (`BB_count_new`) 及 BBT 資料。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - 新的 BBT 資料中必須包含目標區塊資訊 (`target_data_L2`: Block=`L2_vb_next`, CE=0, Plane=0)。
     - 這代表韌體在 L2 發生擦除失敗後，成功將該區塊標記為 Bad Block，並透過替換機制切換了 L2 VB，符合 "selection new PB succeed" 的驗證目標。

2. **[Case02_LIST_PF_Assert_Check]**：
   - 動作：
     1. 透過 VU 40C1 讀取當前 LIST VB (`LIST_vb`)，並透過 VU 40DC 讀取下一個 LIST VB (`LIST_vb_next`)。
     2. 使用 Vendor Command (VU) C012 針對 `LIST_vb_next` (CE=0, Plane=0) 注入程式失敗 (`fail_type=0`)。
     3. 執行隨機位置的 Write10 指令。
     4. 監控 Write10 的回應，預期會觸發 `G_TIMEOUT_ALL` 異常。
     5. 在異常發生後，檢查韌體 Assert 號碼 (`api.get_fw_assert_number()`)。
     6. 檢查 VU 40C1 返回的 LIST VB 號碼 (`LIST_vb_new`) 是否與初始值相同。
   - 預期結果：
     - 韌體 Assert 號碼必須等於 `0x203`。
     - `LIST_vb_new` 必須等於初始的 `LIST_vb`（即 LIST VB 號碼未改變）。
     - 這代表韌體在 LIST 區域發生程式失敗時，未嘗試自動替換或進入 Read-Only 模式，而是觸發了特定的 Assert 0x203 狀態，符合 "FW should be stuck" 且 "Confirmed not in read-only mode" 的驗證目標。