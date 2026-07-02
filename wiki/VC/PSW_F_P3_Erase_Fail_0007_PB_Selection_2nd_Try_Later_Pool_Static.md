# Test Spec: VC-13 (2.h) Erase Fail with Replacement Pool Exhaustion and FW Assert Check

## Verification Criterion (VC)
驗證當快閃記憶體控制器的備用區塊池（Replacement Pool）耗盡且連續發生 Erase Fail 時，韌體的錯誤處理機制：
1. **預備階段**：確認系統在備用區塊剩餘數量低於閾值（`bbt_revoke_cnt == bbtmax_revoke_cnt`）且預測的下一個備用區塊有效時，進入測試循環。
2. **故障注入與狀態檢查**：透過 Vendor Command `VU C012` 強制在當前 L2 VB 及其預測的下一個備用區塊（Next Replacement Block）注入 Erase Fail。執行連續寫入直到 L2 VB 切換，驗證 Bad Block Table (BBT) 正確更新（BB Count +1）並包含目標區塊。
3. **極端情境驗證**：在備用區塊池已耗盡的情境下，再次注入 Erase Fail 於當前 L2 VB 及其預測的下一個備用區塊。執行連續寫入時，預期裝置因韌體內部錯誤（FW Assert）而無回應（Unresponsive），並確認觸發的 Assert Code 為 `0x203`，代表裝置進入非唯讀模式的死鎖狀態，而非正常的 Read-Only 保護模式。

## Test Case (TC) Checkpoints

1. [PreProcess_BBTable_Update_Check]：
   - 動作：
     1. 透過 `VU 40C1` 讀取當前 L2 VB (`L2_vb`) 與透過 `VU 40DC` 讀取下一個 L2 VB (`L2_vb_next`)。
     2. 透過 `VU 405E` 記錄初始 Bad Block Count (`BB_count`)。
     3. 透過 `VU 40D6` (pool_type=1, next_n=2) 讀取預測的兩個備用區塊 (`next_replacement_block_1`, `next_replacement_block_2`)，並讀取 FW 變數 `gUfsApiStruct.ftl->bbt.max_revoke_cnt` 與 `revoke_cnt`。
     4. 若 `revoke_cnt == max_revoke_cnt` 且 `next_replacement_block_2 != 0xFFFF`，則透過 `VU C012` 在 `L2_vb_next` 注入 Erase Fail (fail_type=1)。
     5. 執行連續 `Write10` (LUN 0, LBA 起始, FUA=1) 直到 `VU 40C1` 回傳的 L2 VB 發生改變。
     6. 透過 `VU 4013` 讀取 BE Fail Status，並透過 `VU 405E` 再次讀取 BB 資訊。
     7. 計算 BBT 資料，驗證 `BB_count_new` 是否等於 `BB_count + 1`，並驗證 `target_data_L2` (即 `L2_vb_next` 的 CE/Plane/Block) 是否存在於新的 BBT 列表中。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`。
     - BBT 列表中必須包含 `target_data_L2` 指定的物理地址資訊，代表韌體正確將失效區塊標記為 Bad Block。

2. [Step1_ExhaustedPool_FWAssert_0x203_Check]：
   - 動作：
     1. 透過 `VU 40C1` 獲取當前 L2 VB (`L2_vb`)，透過 `VU 40DC` 獲取下一個 L2 VB (`L2_vb_next`)。
     2. 透過 `VU 40D6` (pool_type=1, next_n=1) 獲取預測的下一個備用區塊 (`next_replacement_block`)。
     3. 透過 `VU C012` 同時在 `L2_vb_next` 與 `next_replacement_block` 注入 Erase Fail (fail_type=1, block_info_list_count=2)。
     4. 執行連續 `Write10` (LUN 0, LBA 起始, FUA=1)。
     5. 在 `ExecuteCMD.send` 中設定 `skip_response_check=True` 以捕獲逾時異常。
     6. 若發生 `G_TIMEOUT_ALL` 異常，呼叫 `api.get_fw_assert_number()` 獲取韌體 Assert Code。
     7. 若未發生逾時，檢查 `VU 40C1` 回傳的 L2 VB 是否改變。
   - 預期結果：
     - 寫入操作必須觸發 `G_TIMEOUT_ALL` 異常，表示裝置無回應。
     - `api.get_fw_assert_number()` 回傳的值必須嚴格等於 `0x203`。
     - 此結果代表韌體在備用區塊耗盡且連續 Erase Fail 的情境下，觸發了特定的內部 Assert (0x203)，且裝置狀態為 "Device remains unresponsive after initialization"，確認未進入正常的 Read-Only 模式，而是處於韌體錯誤狀態。