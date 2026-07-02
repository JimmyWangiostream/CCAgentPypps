# Test Spec: VC-35 (13.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在快閃記憶體發生 Program/Erase Fail (PF) 時的 Bad Block Table (BBT) 更新機制與 Replacement Pool 選擇邏輯：
1. **Case 01 (L2 Dynamic Replacement)**：確認當 L2 (Dynamic) 區塊發生 PF 且其預測的 Replacement Block 位於 Revoke Group 時，韌體能正確跳過該無效 Replacement，並透過後續寫入觸發 L2 VB 切換，最終將 L2 區塊標記為 Bad Block，且 BBT 計數正確增加 1。
2. **Case 02 (L1 Static Replacement)**：確認當 L1 (Static) 區塊發生 PF 時，韌體能正確將 L1 區塊及其預測的 Replacement Block 同時標記為 Bad Block，驗證 BBT 計數正確增加 2，且兩個區塊均出現在 BBT 列表中，證明韌體能處理 L1 層級的多重 Block 失效情境。

## Test Case (TC) Checkpoints

1. [Case01_L2_PF_RevokeGroup_Skip_Check]：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 取得當前 L2 Open VB，透過 `0x40DC` 取得下一個 L2 VB (`L2_vb_next`)，並透過 `0x405E` 記錄初始 Bad Block 計數 (`BB_count`)。
     2. 透過 Vendor Command `0x40D6` (pool_type=1, next_n=1) 取得預測的下一個 Replacement Block ID。
     3. 檢查該 Replacement Block 是否屬於 Revoke Group (透過 `0x40C1` 獲取的重啟 VB 列表比對)。若屬於 Revoke Group，則透過 Vendor Command `0xC012` (fail_type=1) 對 `L2_vb_next` 注入 Program/Erase Fail。
     4. 執行連續 Write10 指令 (LBA 從 0 開始，長度 4KB)，直到透過 `0x40C1` 確認 L2 VB 發生切換 (`L2_vb_new != L2_vb`)，此時觸發韌體處理 PF。
     5. 透過 `0x4013` 讀取 BE Fail Status，並透過 `0x405E` 重新讀取 BBT 資料。
   - 預期結果：
     - 新的 Bad Block 計數 (`BB_count_new`) 必須等於 `BB_count + 1`。
     - 解析後的 BBT 資料中，必須包含目標 L2 區塊 (`L2_vb_next`) 的資訊 (CE, Plane, Block)。
     - 韌體未因 Replacement Block 在 Revoke Group 而崩潰或 Assert，成功將 L2 區塊標記為 Bad。

2. [Case02_L1_PF_MultiBlock_BBT_Update_Check]：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 取得當前 L1 Open VB，透過 `0x40DC` 取得下一個 L1 VB (`L1_vb_next`)，並透過 `0x405E` 記錄初始 Bad Block 計數 (`BB_count`)。
     2. 透過 Vendor Command `0x40D6` (pool_type=1, next_n=1) 取得預測的下一個 Replacement Block ID。
     3. 透過 Vendor Command `0xC012` (fail_type=0, block_info_list_count=2) 同時對 `L1_vb_next` (L1 區塊) 與 `next_replacement_block` (Replacement 區塊) 注入 Program Fail。
     4. 執行隨機 Write10 指令 (長度 16 Bytes)，直到透過 `0x40C1` 確認 L1 VB 發生切換 (`L1_vb_new != L1_vb`)，觸發韌體處理 PF。
     5. 透過 `0x4013` 讀取 BE Fail Status，並透過 `0x405E` 重新讀取 BBT 資料。
   - 預期結果：
     - 新的 Bad Block 計數 (`BB_count_new`) 必須等於 `BB_count + 2`。
     - 解析後的 BBT 資料中，必須同時包含目標 L1 區塊 (`L1_vb_next`) 與目標 Replacement 區塊 (`next_replacement_block`) 的資訊。
     - 證明韌體在 L1 層級 PF 時，能正確將主區塊與替換區塊均列入 Bad Block 管理。