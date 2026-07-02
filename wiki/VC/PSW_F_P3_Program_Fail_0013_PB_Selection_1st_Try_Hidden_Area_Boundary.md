# Test Spec: UFS Program Fail Hidden Area Replacement Logic (VC-37)

## Verification Criterion (VC)
驗證韌體在「隱藏區域 (Hidden Area)」發生 Program Fail 時，Bad Block Table (BBT) 的更新機制與 Vendor Command 的具體行為：
1. **預處理階段**：確認系統能透過連續寫入填滿 SLC 區域，直到觸發第一個空白的 SLC Page (Physical Page >= 3308)，確保後續測試在正確的 L2 邏輯區塊進行。
2. **故障注入與替換預測**：透過 VU 40D6 獲取隱藏區域下一個可用的替換區塊 (Next Replacement Block) 資訊，並透過 VU C012 針對「當前 L2 邏輯區塊」與「預測的替換區塊」同時注入 Program Fail (Fail Type 3)。
3. **BBT 一致性驗證**：執行 Write10 觸發實際寫入失敗後，透過 VU 4013 確認 BE (Block Error) 狀態，並透過 VU 405E 讀取更新後的 BBT。預期 Bad Block Count 必須精確增加 2 (原 L2 區塊與替換區塊均標記為 Bad)，且 BBT 資料中必須包含這兩個特定物理區塊的詳細資訊 (Block, CE, Plane)，證明韌體正確處理了隱藏區域的替換邏輯且未發生 Assert。

## Test Case (TC) Checkpoints
1. [PreProcess_SLC_Fill_Check]：
   - 動作：在 `pre_process` 中執行迴圈，針對 LUN 0 從 LBA 0 開始連續寫入 16 Bytes 資料，每次寫入後透過 `get_open_vb_info` 檢查 `TLC_L2.first_empty_physical_page`。當該物理頁號小於 3308 時繼續寫入，直到物理頁號 >= 3308 時停止。
   - 預期結果：系統成功填滿 SLC 區域，`first_empty_physical_page` 的值必須大於或等於 3308，確保後續測試針對的是 TLC 區域或特定的隱藏區域邊界，為後續的 L2 邏輯區塊操作奠定基礎。

2. [TC01_VU_40D6_Replacement_Prediction]：
   - 動作：在 `step1` 中，首先透過 VU 獲取當前 Open VB 資訊，提取 `logical_VB` 與 `first_empty_physical_page`。接著將物理頁號轉換為邏輯頁號 (Logical Page)，轉換邏輯依據代碼中的 `region_max_wl` 閾值 (如 <1620, <1652, <3308 等區間)。隨後，呼叫 `issue_40D6_to_get_predicted_next_n_replacement_block`，參數設定為 `ce=0`, `plane=0`, `next_n=1`, `pool_type=2` (Hidden Area), `is_CIS=0`, `pf_on_open_data=0`。解析回傳的 `VU_DATA_40D6`，提取 `next_replacement_block` (Bits 5-27), `next_replacement_plane` (Bits 2-4), `next_replacement_ce` (Bits 0-1)。
   - 預期結果：成功獲取隱藏區域下一個可用的替換區塊資訊。`next_replacement_block` 必須是一個有效的邏輯區塊號碼，且與當前 `logical_VB` 不同，代表韌體已正確預測並準備好替換資源。

3. [TC02_VU_C012_Dual_PF_Injection]：
   - 動作：建構 `PhysicalAddressInformation` 結構體。
     - `BlockInfoList_0` (Target L2): 設定 `die=0`, `plane=0`, `block=logical_VB` (當前 L2 區塊), `page=logical_page`。
     - `BlockInfoList_1` (Replacement Target): 設定 `die=next_replacement_ce`, `plane=next_replacement_plane`, `block=next_replacement_block`, `page=0`。
     - 呼叫 `issue_C012_to_create_program_erase_fail`，傳入上述資訊，設定 `fail_type=3` (Program Fail)，`block_info_list_count=2`。
   - 預期結果：韌體成功接收雙重故障注入指令。`BlockInfoList_0` 對應的 L2 邏輯區塊與 `BlockInfoList_1` 對應的替換區塊均被標記為 Program Fail 狀態，模擬真實硬體寫入失敗情境。

4. [TC03_Write10_Trigger_BE_Fail]：
   - 動作：執行 `ExecuteCMD.Write10`，針對 LUN 0，LBA 0，長度為 `api.WRITE_10_MAX_BLOCK_LEN` (最大區塊長度)，設定 `fua=1`。發送命令後，呼叫 `issue_4013_to_get_BE_fail_status` 檢查 Block Error 狀態。
   - 預期結果：由於目標區塊已被 VU C012 注入 Program Fail，此次 Write10 操作應觸發硬體寫入錯誤。`issue_4013` 應返回確認存在 Block Error 的狀態碼，證明故障注入已生效且被韌體偵測到。

5. [TC04_BBT_Update_Verification]：
   - 動作：呼叫 `issue_405E_to_get_bad_block_information` 獲取更新後的 BBT 資料。解析前 4 Bytes 得到 `BB_count_new`。呼叫 `program_fail_api.calculate_bbt` 解析詳細的 BBT 列表 `BB_data_new`。
     - 檢查 `BB_count_new` 是否等於 `BB_count + 2` (初始 BB 數 + 注入的 L2 區塊 + 替換區塊)。
     - 在 `BB_data_new` 中搜尋是否存在包含 `target_data_L2` (Block=`logical_VB`, CE=0, Plane=0) 的項目。
     - 在 `BB_data_new` 中搜尋是否存在包含 `target_data_BBT` (Block=`next_replacement_block`, CE=`next_replacement_ce`, Plane=`next_replacement_plane`) 的項目。
   - 預期結果：
     1. `BB_count_new` 必須精確等於 `BB_count + 2`，證明韌體正確更新了 Bad Block 計數器。
     2. `BB_data_new` 中必須同時包含當前 L2 區塊與替換區塊的詳細資訊，證明韌體在隱藏區域 Program Fail 情境下，正確將替換區塊標記為 Bad Block 並更新 BBT，且未發生韌體 Assert 或崩潰。