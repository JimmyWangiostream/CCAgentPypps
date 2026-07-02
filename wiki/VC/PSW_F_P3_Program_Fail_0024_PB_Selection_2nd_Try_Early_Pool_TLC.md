# Test Spec: VC-48 (13.f) Program Fail Recovery with Early Replacement Pool Update

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生寫入失敗（Program Fail）時，若透過 Vendor Command 強制注入 L2 VB 及其預測的下一個替換區塊（Next Replacement Block）為故障狀態，韌體應能正確執行 Bad Block Table (BBT) 更新機制。具體驗證點包括：1. 寫入指令返回失敗狀態；2. 韌體自動將 L2 VB 與替換區塊標記為 Bad Block；3. BBT 計數器精確增加 2；4. 韌體無 Assert 崩潰，系統保持穩定並可透過後續操作恢復。

## Test Case (TC) Checkpoints
1. [PreProcess_FillToFirstEmptyPage]：
   - 動作：執行連續寫入循環，每次寫入 16 LBA 資料至 LUN 0，直到 `get_open_vb_info` 返回的 `TLC_L2.first_empty_physical_page` 物理頁碼大於或等於 1652 為止，確保後續測試目標區塊位於特定的 Wear Leveling 區域邊界附近。
   - 預期結果：寫入操作成功完成，系統進入預設的滿載狀態，為後續注入特定物理頁面的 Program Fail 做準備。

2. [Step1_GetContextAndInjectPF]：
   - 動作：
     a. 呼叫 `get_open_vb_info` 取得當前 `TLC_L2` 的邏輯 VB (`logical_VB`) 與第一個空閒物理頁 (`physical_page`)。
     b. 呼叫 VU 0x405E 讀取當前 Bad Block 計數 (`BB_count`)。
     c. 根據 `physical_page` 的數值範圍（<1620, <1652, <3308, <3312）及對應的 `region_max_wl` 閾值，計算出對應的邏輯頁 (`logical_page`)。
     d. 呼叫 VU 0x40D6 查詢 CE 0, Plane 0 的下一個替換區塊 (`next_replacement_block`)。
     e. 構造 `PhysicalAddressInformation`，設定 Block 0 為當前 L2 VB 與計算出的 `logical_page`，Block 1 為 `next_replacement_block` 與 Page 0。
     f. 呼叫 VU 0xC012 並傳入上述資訊與 `fail_type=3`，強制注入這兩個區塊的 Program Fail 狀態。
   - 預期結果：Vendor Command 執行成功，韌體內部狀態機已將指定的 L2 VB 頁面與替換區塊標記為 Program Fail，但尚未觸發自動替換或 BBT 更新（等待寫入觸發）。

3. [Step1_TriggerFailAndVerifyBBT]：
   - 動作：
     a. 執行 `Write10` 指令，寫入最大長度 (`api.WRITE_10_MAX_BLOCK_LEN`) 至 LUN 0 的 LBA 0，並設定 `skip_response_check=True` 以忽略返回的錯誤碼。
     b. 呼叫 VU 0x4013 讀取 BE (Block Error) 失敗狀態。
     c. 再次呼叫 VU 0x405E 獲取新的 Bad Block 計數 (`BB_count_new`) 及完整的 BBT 數據 (`BB_data_new`)。
     d. 驗證 `BB_count_new` 是否等於 `BB_count + 2`。
     e. 在 `BB_data_new` 中搜尋是否包含目標 L2 VB 資訊 (`target_data_L2`) 與目標替換區塊資訊 (`target_data_replace`)。
   - 預期結果：
     - 寫入指令應返回失敗（因已注入 PF）。
     - `BB_count_new` 必須嚴格等於 `BB_count + 2`，證明韌體正確識別並標記了兩個新的 Bad Block。
     - `BB_data_new` 中必須能找到與 `target_data_L2` 完全匹配的條目，證明 L2 VB 被正確加入 BBT。
     - `BB_data_new` 中必須能找到與 `target_data_replace` 完全匹配的條目，證明預測的替換區塊也被正確加入 BBT。
     - 整個過程中韌體未發生 Assert 或系統崩潰，驗證了韌體在處理多重 Program Fail 時的 BBT 更新邏輯正確性。