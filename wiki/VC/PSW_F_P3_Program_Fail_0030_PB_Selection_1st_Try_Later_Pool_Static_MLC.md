# Test Spec: VC-54 (12.h) Program Fail on L2 VB First Empty Page Recovery Check

## Verification Criterion (VC)
驗證韌體在 MLC 頁面上針對 L2 VB 的第一個空閒物理頁（First Empty Physical Page）執行寫入操作時，若觸發 Program Fail (PF) 錯誤，系統應正確更新 Bad Block Table (BBT) 並將該區塊標記為唯讀（Read Only）。具體驗證邏輯為：透過 Vendor Command (VU C012) 在目標 L2 VB 的計算所得 Logical Page 注入 fail_type=3 (Program Fail)，隨後發起 Write10 命令。預期結果為設備進入非響應狀態並觸發韌體 Assert 0x203（代表設備初始化後卡住，確認未進入 Read-Only 模式前的異常狀態），同時驗證 BBT 中該目標區塊已被正確標記為壞塊，且 Bad Block Count 增加 1。

## Test Case (TC) Checkpoints
1. [Case01_L2_PF_Assert_and_BBT_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 VB 號碼 (`L2_vb`) 及下一個開放 VB 號碼 (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始 Bad Block Count (`BB_count`) 並解析 BBT 數據。
     3. 透過 VU 40D6 預測替換區塊，確保替換池中有足夠空間（若 `next_replacement_block_2 == 0xFFFF` 則跳過或處理，此測試聚焦於 L2 VB 本身）。
     4. 執行連續寫入（Write10, LBA 0, Length 4KB, FUA=1）直到 L2 VB 發生切換，確保目標 L2 VB 成為當前寫入目標。
     5. 透過 VU 4013 獲取 BE (Bad Endurance) Fail 狀態。
     6. 再次透過 VU 405E 獲取新的 BBT 數據，計算 `BB_count_new` 並驗證 `BB_count_new == BB_count + 1`。
     7. 驗證新的 BBT 數據中是否包含目標區塊資訊（`target_data_L2`，即 CE=0, Plane=0, Block=`L2_vb_next` 或當前寫入的 L2 VB，根據代碼邏輯 `target_data_L2` 在 Flow 6 設定為 `L2_vb_next`，但在 Step1 中操作的是 `logical_VB`，需確認代碼邏輯一致性：代碼中 `target_data_L2` 記錄的是 Flow 5 注入 EF 的區塊，而 Step1 操作的是 `logical_VB`。根據 VC 描述 "selection new PB succeed... searched in the latereplacement pool"，此測試主要驗證 L2 VB 寫入失敗後的處理。注意：代碼中 `target_data_L2` 是在 pre_process 中設定的 `L2_vb_next`，但 Step1 中操作的是 `logical_VB` (當前 L2 VB)。這暗示測試可能分為兩部分：Pre-process 處理替換池，Step1 處理當前 L2 VB。根據 VC 描述 "Program fail... in normal area"，Step1 是核心驗證點)。
     8. **核心動作 (Step1)**：獲取當前 L2 VB (`logical_VB`) 及其 First Empty Physical Page (`physical_page`)。根據 MLC 映射規則將 `physical_page` 轉換為 `logical_page`：
        - 若 `physical_page < 1620`: `logical_page = physical_page // 3`
        - 若 `1620 <= physical_page < 1652`: `logical_page = (physical_page - 1620) // 2 + 540`
        - 若 `1652 <= physical_page < 3308`: `logical_page = (physical_page - 1652) // 3 + 556`
        - 若 `3308 <= physical_page < 3312`: `logical_page = (physical_page - 3308) // 1 + 1108`
     9. 透過 VU C012 在 CE=0, Plane=0, Block=`logical_VB`, Page=`logical_page` 處注入 `fail_type=3` (Program Fail)。
     10. 發起 Write10 命令 (LBA 0, Length 4KB, FUA=1)。
     11. 捕獲 `G_TIMEOUT_ALL` 異常，並檢查韌體 Assert 號碼是否為 `0x203`。
   - 預期結果：
     1. BBT 驗證：`BB_count_new` 必須等於 `BB_count + 1`，且新的 BBT 數據中必須包含目標區塊（CE=0, Plane=0, Block=`logical_VB`）的壞塊標記。
     2. 異常處理：Write10 命令必須超時並拋出 `G_TIMEOUT_ALL`。
     3. 韌體狀態：`api.get_fw_assert_number()` 必須返回 `0x203`。這確認了設備在 Program Fail 後進入了一個特定的非響應狀態（Assert 0x203），且根據 VC 描述，此狀態確認設備「未」進入 Read-Only 模式（通常 Read-Only 模式會有不同的處理路徑或 Assert 碼，此處 0x203 代表設備卡住，需進一步確認韌體是否隨後恢復或需手動重置，但測試預期是捕捉此 Assert）。
     4. 邏輯一致性：驗證了當 L2 VB 的第一個空閒頁發生 Program Fail 時，韌體能正確識別並標記該頁/區塊為壞塊，並觸發預期的韌體異常處理機制。