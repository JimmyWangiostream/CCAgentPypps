# Test Spec: UFS BE (Bad Erase) Fail Injection & BBT Update Verification

## Verification Criterion (VC)
驗證韌體在透過 Vendor Command (VU C012) 強制注入特定 Block 的 Erase Fail 後，系統能否正確識別該錯誤並觸發 Bad Block Table (BBT) 更新機制：
1. 確認 VU C012 成功將指定 L2 VB (Logical VB) 標記為 Erase Fail 狀態。
2. 確認透過 VU 4013 讀取的 BE Fail Status 中，Fail Type 必須為 2 (Erase Fail)，且 Fail Times 大於 0。
3. 確認 BE Fail Status 中的物理地址資訊 (Die, Plane, Block, Page, TG Bitmap) 與注入時指定的目標 Block 完全一致。
4. 確認在觸發 L2 VB 切換後，透過 VU 405E 讀取的 BBT 中，Bad Block Count 必須增加 1，且目標 Block 的 (CE, Plane, Block) 組合必須出現在新的 BBT 列表中，代表韌體已將該 Block 正式標記為 Bad Block 並排除使用。

## Test Case (TC) Checkpoints
1. [Case01_BE_Fail_Injection_and_Status_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 Open Logical VB (記為 `L2_vb`)。
     2. 透過 VU 40DC 獲取下一個 Open VB (記為 `L2_vb_next`)。
     3. 透過 VU 405E 獲取初始 Bad Block Count (`BB_count`) 及 BBT 數據 (`BB_data`)。
     4. 建構 `PhysicalAddressInformation`，指定 Die=0, Plane=0, Block=`L2_vb_next`, Page=0, TG Bitmap=0。
     5. 執行 Vendor Command VU C012，傳入上述資訊並設定 `fail_type=1` (代表 Erase Fail)，強制注入該 Block 的 Erase 錯誤。
     6. 執行連續 Write10 指令 (LUN 0, FUA=1)，從 LBA 0 開始寫入，每次寫入 `WRITE_10_MAX_BLOCK_LEN` 長度，並持續檢查 VU 40C1 返回的 L2 VB。
     7. 當 L2 VB 發生變化 (從 `L2_vb` 變為 `L2_vb_new`) 時停止寫入，確保韌體已處理完該 VB 的資料並觸發 VB 切換。
     8. 執行 VU 4013 獲取 BE Fail Status。
   - 預期結果：
     - VU 4013 返回的 `status.fail_type.value` 必須等於 2 (代表 Erase Fail)。
     - `status.fail_times.value` 必須大於 0。
     - `status.time_0_die.value` 必須等於 0。
     - `status.time_0_plane.value` 必須等於 0。
     - `status.time_0_block.value` 必須等於 `L2_vb_next`。
     - `status.time_0_page.value` 必須等於 0。
     - `status.time_0_tg_bitmap.value` 必須等於 0。
     - 以上所有欄位必須與步驟 4 中注入時指定的 `PhysicalAddressInformation` 完全匹配，證明韌體正確記錄了注入的 Erase Fail 事件及其物理位置。

2. [Case02_BBT_Update_Verification]：
   - 動作：
     1. 在 Case 01 確認 BE Fail Status 正確後，執行 VU 405E 再次獲取 Bad Block Information。
     2. 解析返回的 payload，提取新的 Bad Block Count (`BB_count_new`) 並重新計算 BBT 列表 (`BB_data_new`)。
     3. 在 `BB_data_new` 中搜尋是否存在包含目標 Block 資訊 (Block=`L2_vb_next`, CE=0, Plane=0) 的條目。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`，證明 Bad Block 計數器正確遞增。
     - 搜尋結果必須找到至少一個條目，其 Block 值等於 `L2_vb_next`，CE 等於 0，Plane 等於 0。這代表韌體在檢測到 Erase Fail 後，已將該物理 Block 正確寫入 BBT 並標記為不可用，符合 UFS 規範中對 Bad Block 管理的預期行為。