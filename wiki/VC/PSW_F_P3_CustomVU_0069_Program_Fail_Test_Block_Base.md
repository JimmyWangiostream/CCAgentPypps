# Test Spec: UFS Vendor Command C012 Program Fail Injection & BBT Update Verification

## Verification Criterion (VC)
驗證韌體在接收到 Vendor Command `0xC012` 並指定特定物理區塊（L2 VB）進行模擬寫入失敗（Program Fail）後，系統內部狀態機與硬體管理表的同步行為：Case 01 確認寫入指令觸發模擬錯誤後，透過 Vendor Command `0x4013` 讀取的 BE (Bad Entry) 狀態寄存器中，`fail_type` 必須為 1，且 `time_0` 系列欄位（Die, Plane, Block, Page, TG Bitmap）必須精確匹配注入時的物理地址資訊；Case 02 確認該模擬失敗事件已正確觸發壞塊管理機制，導致 Bad Block Table (BBT) 中的壞塊計數器（BB Count）增加 1，且新的 BBT 數據中必須包含注入的特定 CE/Plane/Block 組合，證明韌體已將該 L2 VB 標記為不可用。

## Test Case (TC) Checkpoints
1. [Case01_BE_Status_Sync_Check]：
   - 動作：首先透過 Vendor Command `0x40C1` 獲取當前 L2 Open Logical VB 號碼（L2_vb）；接著透過 Vendor Command `0x405E` 讀取初始壞塊資訊並計算初始壞塊計數器（BB_count）與壞塊表（BB_data）；然後構造 `PhysicalAddressInformation`，將 Block 欄位設為 L2_vb，Die/Plane/Page/TG Bitmap 設為 0，透過 Vendor Command `0xC012` 注入 `fail_type=0` 的模擬寫入失敗；隨後發送標準 `WRITE10` 指令至 LUN 0 的 LBA 0（長度為 `WRITE_10_MAX_BLOCK_LEN`，FUA=1）以觸發該模擬錯誤；最後透過 Vendor Command `0x4013` 讀取 BE Fail Status，並比對返回的 `status` 結構體。
   - 預期結果：`status.fail_type.value` 必須等於 1；`status.fail_times.value` 必須大於 0；`status.time_0_die.value` 必須等於 0；`status.time_0_plane.value` 必須等於 0；`status.time_0_block.value` 必須等於 L2_vb；`status.time_0_page.value` 必須等於 0；`status.time_0_tg_bitmap.value` 必須等於 0。此結果證明韌體正確捕捉了由 `0xC012` 觸發的特定物理地址寫入失敗，並更新了內部 BE 狀態寄存器。

2. [Case02_BBT_Update_Verification]：
   - 動作：在 Case 01 成功觸發模擬失敗後，再次透過 Vendor Command `0x405E` 讀取最新的壞塊資訊（`VU_DATA_405E_new`），解析其前 4 位元組得到新的壞塊計數器（`BB_count_new`），並解析後續 payload 從 index 4 開始、步長為 8 的區塊資訊（每 8 位元組包含 Block[2B], CE[1B], Plane[1B] 等）；構造目標區塊資訊字典 `target_data`，包含注入時的 Block (L2_vb), CE (0), Plane (0)；檢查 `BB_count_new` 是否等於 `BB_count + 1`；檢查解析後的壞塊表列表中是否存在與 `target_data` 完全匹配的條目。
   - 預期結果：`BB_count_new` 必須精確等於 `BB_count + 1`，證明壞塊計數器已正確遞增；`find` 查詢結果必須為真（即列表中能找到該條目），證明注入的 L2 VB 已作為壞塊被記錄在 BBT 中，且其 CE 與 Plane 資訊解析正確（注意：Plane 欄位在解析時需右移 3 位，即 `>> 3`），驗證了韌體壞塊管理邏輯的完整性。