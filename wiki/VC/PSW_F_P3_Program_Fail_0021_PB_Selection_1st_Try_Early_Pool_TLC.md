# Test Spec: VC-45 (12.f) Program Fail Injection & BBT Update Verification

## Verification Criterion (VC)
驗證韌體在遭遇特定 L2 VB 的 Program Fail (PF) 時，能否正確執行 Bad Block Table (BBT) 更新機制：透過 Vendor Command (VC) C012 在指定的 L2 Logical VB 與計算出的 Logical Page 注入 Fail Type 3 (Program Fail)，隨後執行標準 Write10 觸發硬體寫入流程並確認 BE (Block Error) 狀態，最終驗證 BB Count 是否精確增加 1，且新的 BBT 數據中必須包含被標記為失效的特定 Block/CE/Plane 組合，同時確認韌體無 Assert 崩潰。

## Test Case (TC) Checkpoints
1. [PreProcess_FillToEmptyPage_Check]：
   - 動作：進入 `pre_process` 階段，透過迴圈持續發送 LBA 0 起始、長度 16 的 Write10 指令，並透過 `get_open_vb_info` 監控 `TLC_L2.first_empty_physical_page`。當該物理頁位號大於或等於 1652 時停止寫入，確保系統進入待測狀態。
   - 預期結果：寫入流程順利完成，系統狀態穩定，且當前空閒物理頁位指標已推進至 1652 以上，為後續注入 PF 提供足夠的寫入空間與目標頁位。

2. [Step1_GetBaseline_InjectPF_Check]：
   - 動作：
     1. 呼叫 `get_open_vb_info` 取得當前 `TLC_L2` 的 `logical_vb` 與 `first_empty_physical_page`。
     2. 根據物理頁位範圍（<1620, <1652, <3308, <3312）套用對應的映射公式（如 `physical_page < 1652` 時使用 `(physical_page - 1620) // 2 + 556`）計算出對應的 `logical_page`。
     3. 記錄當前 BB Count (`BB_count`)。
     4. 建構 `PhysicalAddressInformation`，設定 `BlockInfoList_0_block` 為上述 `logical_VB`，`BlockInfoList_0_page` 為計算出的 `logical_page`，`CE=0`, `Plane=0`。
     5. 發送 Vendor Command `C012`，傳入上述資訊並指定 `fail_type=3` (Program Fail)，強制在韌體層面標記該 L2 Page 為 Program Fail。
   - 預期結果：VC C012 執行成功，韌體內部將目標 L2 Page 標記為失效狀態，但尚未觸發硬體寫入，BB Count 保持不變。

3. [Step1_TriggerPF_VerifyBBT_Check]：
   - 動作：
     1. 發送長度為 `api.WRITE_10_MAX_BLOCK_LEN` 的 Write10 指令至 LBA 0，觸發實際的 Flash 寫入操作。
     2. 由於目標頁位已透過 VC C012 注入 PF，硬體寫入應失敗，韌體應捕捉此錯誤。
     3. 發送 Vendor Command `4013` 讀取 BE (Block Error) Fail Status，確認錯誤狀態已被記錄。
     4. 再次發送 Vendor Command `405E` 獲取最新的 Bad Block Information，解析出新的 `BB_count_new` 與 `BB_data_new`。
     5. 比對 `BB_count_new` 與 `BB_count`，並檢查 `BB_data_new` 中是否存在包含目標 `Block` (即 `logical_VB`)、`CE=0`、`Plane=0` 的條目。
   - 預期結果：
     1. `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明韌體正確識別並記錄了一個新的 Bad Block。
     2. `BB_data_new` 中必須能找到與目標 `target_data_L2` (Block: `logical_VB`, CE: 0, Plane: 0) 完全匹配的條目，證明 BBT 已正確更新並包含該失效區塊。
     3. 整個流程中韌體未發生 Assert 或崩潰，測試腳本順利執行至 `post_process`。