# Test Spec: UFS Vendor Command C012 Program Fail Injection & BBT Update Verification

## Verification Criterion (VC)
驗證透過 Vendor Command (VC) `0xC012` 強制注入 Program Fail 後，韌體是否能正確觸發 Bad Block Table (BBT) 更新機制：Case 01 確認在指定 LUN 0 執行連續寫入並觸發注入後，狀態查詢 VC `0x4013` 回報的 Fail Type 必須為 1 (Program Fail)，且回報的 Die/Plane/Block/Page 資訊與注入時指定的物理地址完全一致；Case 02 確認注入後再次查詢 VC `0x405E` 取得的 BBT 中，壞塊計數器 (BB Count) 必須比注入前增加 1，且新增的壞塊資訊（Block, CE, Plane）必須精確對應到被標記為故障的物理區塊，證明韌體已將該區塊標記為 Bad Block 並更新至非揮發性儲存結構。

## Test Case (TC) Checkpoints
1. [Case01_ProgramFail_Status_Check]：
   - 動作：
     1. 透過 VC `0x405E` 讀取初始 Bad Block Count (`BB_count`) 並解析 BBT 資料。
     2. 透過 VC `0x405E` 獲取 Open VB 資訊，提取 `TLC_L2.logical_vb` 作為目標 Block ID，並根據 `first_empty_physical_page` 計算對應的 `logical_page`（依據代碼中的 region_max_wl 映射邏輯：若 page < 1620 則除以 3；1620-1651 則減 1620 除以 2 加 540；1652-3307 則減 1652 除以 3 加 556；3308-3311 則減 3308 加 1108）。
     3. 建構 `PhysicalAddressInformation`，設定 Die=0, Plane=0, Block=`logical_VB`, Page=`logical_page + 1`，並透過 VC `0xC012` 以 `fail_type=3` 注入 Program Fail。
     4. 在 LUN 0 從 LBA 0 開始寫入 `api.WRITE_10_MAX_BLOCK_LEN * 16` 長度的資料，並發送指令。
     5. 透過 VC `0x4013` 讀取 BE (Bad Error) Fail Status。
   - 預期結果：
     - `status.fail_type.value` 必須等於 `1`。
     - `status.fail_times.value` 必須大於 `0`。
     - `status.time_0_die.value` 必須等於 `0`。
     - `status.time_0_plane.value` 必須等於 `0`。
     - `status.time_0_block.value` 必須等於注入時的 `logical_VB`。
     - `status.time_0_page.value` 必須等於注入時的 `logical_page + 1`。
     - `status.time_0_tg_bitmap.value` 必須等於 `0`。
     - 以上所有欄位必須與步驟 3 中建構的 `info` 物件完全匹配，證明韌體正確記錄了由 VC 注入的特定物理位置故障。

2. [Case02_BBT_Update_Verification]：
   - 動作：
     1. 在 Case 01 完成後，再次透過 VC `0x405E` 讀取 Bad Block Information，獲取新的 `BB_count_new` 與 `BB_data_new`。
     2. 計算壞塊計數差異：`expected_count = BB_count + 1`。
     3. 解析 `BB_data_new`，尋找包含目標 Block (`info.BlockInfoList_0_block.value`)、CE (`0`) 與 Plane (`0`) 的條目。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明壞塊計數器已正確遞增。
     - 在 `BB_data_new` 列表中必須存在至少一個字典 `d`，滿足 `d['Block'] == info.BlockInfoList_0_block.value` 且 `d['CE'] == 0` 且 `d['Plane'] == 0`。
     - 這代表韌體在偵測到 Program Fail 後，已將該物理區塊標記為 Bad Block 並寫入 BBT，且該標記在後續的 VC 查詢中可見。