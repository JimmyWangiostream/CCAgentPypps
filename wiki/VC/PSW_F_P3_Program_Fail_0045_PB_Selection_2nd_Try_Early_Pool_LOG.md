# Test Spec: VC-34 (13.f) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生寫入失敗（Program Fail）且透過 Vendor Command 強制注入失敗情境後，系統能否正確執行替換機制：
1. **替換邏輯驗證**：確認當目標邏輯區塊（LOG VB, `LOG_vb_next`）及其預期的早期替換池（Early Replacement Pool）區塊（`next_replacement_block`）同時被標記為 Program Fail 時，韌體能正確識別並處理此雙重失敗。
2. **BB Table 更新驗證**：確認在觸發寫入操作導致 LOG VB 切換後，Bad Block Table (BBT) 必須精確反映這兩個區塊（原 LOG 區塊與替換區塊）已被標記為 Bad Block。
3. **狀態碼與計數驗證**：確認 Bad Block Count 必須嚴格增加 2（代表兩個區塊失效），且透過 Vendor Command `4013` 查詢 BE (Bad Block Entry) 狀態時，系統無 Assert 或崩潰，證明韌體在處理複雜替換失敗時的穩定性。

## Test Case (TC) Checkpoints
1. [Case01_Initial_State_Recording]：
   - 動作：透過 Vendor Command `40C1` 讀取當前 Open VB 資訊，提取 `LOG_block_VB_number_logical` 作為基準 LOG VB；透過 `40DC` 讀取下一個 Open VB 資訊，提取 `LOG` 欄位作為目標寫入區塊 (`LOG_vb_next`)；透過 `405E` 讀取當前 Bad Block 總數 (`BB_count`)；透過 `40D6` 查詢 CE=0, Plane=0, Pool Type=1 (Early Replacement Pool) 的下一個預測替換區塊 (`next_replacement_block`)。
   - 預期結果：成功獲取 `LOG_vb_next` 與 `next_replacement_block` 的物理地址資訊，並記錄初始 `BB_count` 作為比對基準。

2. [Case02_Fail_Injection]：
   - 動作：建構 `PhysicalAddressInformation`，指定兩個失敗目標：
     1. `BlockInfoList_0`: 目標為 `LOG_vb_next` (CE=0, Plane=0, Page=0)。
     2. `BlockInfoList_1`: 目標為 `next_replacement_block` (CE=0, Plane=0, Page=0)。
     透過 Vendor Command `C012` 執行 `issue_C012_to_create_program_erase_fail`，設定 `fail_type=0` (Program Fail)，強制將這兩個區塊標記為寫入失敗狀態。
   - 預期結果：韌體內部狀態機將這兩個區塊標記為 Program Fail，但尚未觸發替換或標記為 Bad Block（因為尚未進行實際寫入觸發），系統保持穩定無 Assert。

3. [Case03_Log_VB_Switch_Trigger]：
   - 動作：在迴圈中隨機發送 `Write10` 命令（長度 `WRITE_10_MAX_BLOCK_LEN`），持續監控透過 `40C1` 讀取的 `LOG_block_VB_number_logical`。一旦偵測到 `LOG_vb_new` 不等於初始的 `LOG_vb`，即停止寫入。
   - 預期結果：寫入操作成功觸發韌體進行 LOG VB 切換，確保後續的寫入失敗情境發生在新的邏輯區塊上下文中，且系統未因隨機寫入而崩潰。

4. [Case04_BBT_Update_Verification]：
   - 動作：
     1. 透過 Vendor Command `4013` 查詢 BE (Bad Block Entry) 狀態，確認無 Assert。
     2. 再次透過 `405E` 讀取 Bad Block 資訊，獲取新的 `BB_count_new` 與 `BB_data_new`。
     3. 計算 `BB_data_new` 並檢查是否包含之前注入失敗的兩個目標區塊：
        - 檢查 `target_data_LOG` (原 `LOG_vb_next`) 是否存在於 BBT 中。
        - 檢查 `target_data_replace` (原 `next_replacement_block`) 是否存在於 BBT 中。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 2`。
     - `BB_data_new` 中必須同時找到 `target_data_LOG` 與 `target_data_replace` 的記錄。
     - 這證明韌體在處理 Program Fail 時，正確地將目標區塊及其替換區塊標記為 Bad Block，並更新了 BBT，符合 VC-34 規範中 "FW should be update BB table" 的要求。