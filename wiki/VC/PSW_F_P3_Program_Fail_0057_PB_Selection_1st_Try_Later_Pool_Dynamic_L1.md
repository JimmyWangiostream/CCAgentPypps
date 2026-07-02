# Test Spec: UFS Program Fail Replacement Logic Verification (VC-31)

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇 Program/Erase Fail (PF) 時的 Bad Block (BB) 處理與 Replacement 機制：
1. **L2 VB 層級驗證**：確認當 L2 Open VB 被標記為 Fail 後，韌體能正確更新 BB Table (BBT)，將該 Block 加入壞塊列表，並確保下一次寫入操作能成功切換至新的 L2 VB（即 Replacement 成功），且過程中無 Assert 發生。
2. **L1 VB 層級驗證**：確認當 L1 Open VB 被標記為 Fail 後，韌體能正確更新 BBT，將該 Block 標記為壞塊，並確保後續隨機寫入觸發 L1 VB 切換時，BBT 狀態與 BB Count 一致，驗證 L1 層級的 Replacement 邏輯正確性。
3. **控制群組邏輯**：透過 `pre_process` 中的循環，確保測試目標 Block 並非處於 Revoke Group（已撤銷區塊），以排除干擾，專注於 Normal Area 的 Replacement 行為。

## Test Case (TC) Checkpoints

1. [PreProcess_L2_Replacement_Validation]：
   - 動作：
     1. 透過 `get_VB_group` 獲取當前 Revoke Group 列表。
     2. 進入循環，透過 Vendor Command `VU 40C1` 獲取當前 L2 Open VB (`L2_vb`)，透過 `VU 40DC` 獲取下一個 L2 Open VB (`L2_vb_next`)。
     3. 透過 `VU 405E` 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 `VU 40D6` 獲取預測的下一個 Replacement Block (`next_replacement_block`)。
     5. **條件判斷**：若 `next_replacement_block` 屬於 Revoke Group，則透過 `VU C012` (fail_type=1) 對 `L2_vb_next` 注入 Program/Erase Fail，隨後執行連續寫入 (`Write10`, `fua=1`) 直到 `L2_vb` 發生切換，並透過 `VU 4013` 檢查 BE Fail Status，最後透過 `VU 405E` 驗證 BB Count 增加 1 且 BBT 中已包含該 Target Block。重複此流程直到 `next_replacement_block` 不在 Revoke Group 中。
   - 預期結果：
     - 當注入 Fail 後，韌體應正確識別該 Block 為壞塊。
     - 連續寫入後，`L2_vb` 必須發生改變，證明韌體成功跳過壞塊並切換至新的 L2 VB。
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - `BB_data_new` 中必須能找到與 `target_data_L2` (Block, CE, Plane) 完全匹配的條目。
     - 此步驟旨在確保測試環境中的 Replacement Pool 狀態正確，並為後續 L2 測試準備一個非 Revoke 狀態的 Target Block。

2. [Case01_L2_ProgramFail_Replacement_Check]：
   - 動作：
     1. 透過 `VU 40C1` 獲取當前 L2 Open VB (`L2_vb`)。
     2. 透過 `VU 40DC` 獲取下一個 L2 Open VB (`L2_vb_next`)。
     3. 透過 `VU 405E` 記錄初始 BB Count (`BB_count`)。
     4. 透過 `VU C012` (fail_type=1) 對 `L2_vb_next` 注入 Program Fail。
     5. 記錄 Target Block 資訊 (`target_data_L2`)。
     6. 執行連續寫入 (`Write10`, `length=api.WRITE_10_MAX_BLOCK_LEN`, `fua=1`)，起始 LBA 為 0，持續增加 LBA 直到透過 `VU 40C1` 讀取的 `L2_vb_new` 不等於初始 `L2_vb`。
     7. 透過 `VU 4013` 獲取 BE Fail Status。
     8. 透過 `VU 405E` 獲取新的 BB Count (`BB_count_new`) 並計算 BBT (`BB_data_new`)。
     9. 驗證 `BB_count_new == BB_count + 1` 且 `target_data_L2` 存在於 `BB_data_new` 中。
   - 預期結果：
     - 韌體在檢測到 L2 VB 的 Program Fail 後，應自動將該 Block 標記為 Bad Block。
     - 連續寫入操作成功觸發 L2 VB 切換，證明 Replacement 機制在 Normal Area 生效。
     - BB Count 精確增加 1。
     - BBT 中正確記錄了被注入 Fail 的 Block 資訊，無 Assert 或系統崩潰。

3. [Case02_L1_ProgramFail_Replacement_Check]：
   - 動作：
     1. 透過 `VU 40C1` 獲取當前 L1 Open VB (`L1_vb`)。
     2. 透過 `VU 40DC` 獲取下一個 L1 Open VB (`L1_vb_next`)。
     3. 透過 `VU 405E` 記錄初始 BB Count (`BB_count`)。
     4. 透過 `VU C012` (fail_type=0) 對 `L1_vb_next` 注入 Program Fail。
     5. 記錄 Target Block 資訊 (`target_data_L1`)。
     6. 執行隨機寫入 (`Write10`, `length=16`, `fua=1`)，LBA 隨機生成，持續直到透過 `VU 40C1` 讀取的 `L1_vb_new` 不等於初始 `L1_vb`。
     7. 透過 `VU 4013` 獲取 BE Fail Status。
     8. 透過 `VU 405E` 獲取新的 BB Count (`BB_count_new`) 並計算 BBT (`BB_data_new`)。
     9. 驗證 `BB_count_new == BB_count + 1` 且 `target_data_L1` 存在於 `BB_data_new` 中。
   - 預期結果：
     - 韌體在檢測到 L1 VB 的 Program Fail 後，應自動將該 Block 標記為 Bad Block。
     - 隨機寫入操作成功觸發 L1 VB 切換，證明 L1 層級的 Replacement 機制在 Normal Area 生效。
     - BB Count 精確增加 1。
     - BBT 中正確記錄了被注入 Fail 的 Block 資訊，無 Assert 或系統崩潰。