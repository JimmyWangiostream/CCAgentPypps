# Test Spec: VC-31 (12.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在正常區域（Normal Area）發生 Program Fail 時的壞塊替換機制與狀態一致性：
1. **預處理階段 (Pre-process)**：透過 Vendor Command (VU C012) 強制在 L2 VB 的下一個候選區塊 (Next L2 VB) 注入 Erase Fail，迫使韌體將其標記為壞塊並從替換池 (Replacement Pool) 分配新的 L2 VB。此階段需確認 BB Table (BBT) 正確更新，且韌體未因錯誤而 Assert 崩潰。
2. **主測試階段 (Step1)**：針對當前已分配的 L2 VB 注入 Program Fail (fail_type=0)，執行寫入操作後，驗證韌體是否能正確識別該 L2 VB 為壞塊，並將其加入 BBT。
3. **核心驗證點**：
   - 壞塊計數器 (BB Count) 必須精確增加 1。
   - 被注入故障的 L2 VB (Block/CE/Plane) 必須出現在更新後的 BBT 資料結構中。
   - 韌體在處理此異常流程時，必須保持系統穩定，無 Assert 發生，且能正確維護 Bad Block Table 的完整性。

## Test Case (TC) Checkpoints

1. [Preprocess_L2_VB_Force_Replacement_Check]：
   - 動作：
     1. 透過 VU 40C1 讀取當前 L2 Open Logical VB (`L2_vb`)，並透過 VU 40DC 讀取下一個候選 L2 VB (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始壞塊計數 (`BB_count`)。
     3. 透過 VU 40D6 查詢替換池預測的下一個替換區塊 (`next_replacement_block`)。
     4. 若 `next_replacement_block` 不在 Revoke Group 中，則透過 VU C012 針對 `L2_vb_next` (CE=0, Plane=0) 注入 Erase Fail (`fail_type=1`)。
     5. 執行連續 Write10 指令，直到 VU 40C1 回傳的 L2 VB 發生改變 (`L2_vb_new != L2_vb`)，確認韌體已觸發替換機制。
     6. 透過 VU 4013 檢查 BE Fail 狀態，並透過 VU 405E 再次讀取 BBT。
     7. 驗證新的 `BB_count_new` 是否等於 `BB_count + 1`，並確認被注入故障的 `L2_vb_next` 資訊存在於計算後的 BBT 資料 (`BB_data_new`) 中。
     8. 重複上述流程，直到 VU 40D6 預測的替換區塊落入 Revoke Group 為止。
   - 預期結果：
     - 韌體在處理 Erase Fail 後，L2 VB 成功切換至替換池中的新區塊。
     - BBT 中的壞塊計數精確增加 1。
     - 被標記為壞塊的區塊資訊 (Block, CE, Plane) 準確記錄在 BBT 中。
     - 整個過程中韌體未發生 Assert 或系統崩潰，證明韌體能穩定處理替換池的壞塊替換邏輯。

2. [Step1_L2_Program_Fail_BBT_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 VB (`L2_vb`)。
     2. 透過 VU 405E 記錄當前壞塊計數 (`BB_count`)。
     3. 透過 VU C012 針對當前 `L2_vb` (CE=0, Plane=0, Page=0) 注入 Program Fail (`fail_type=0`)。
     4. 執行單次 Write10 指令 (LBA=0, Length=Max, FUA=1)，並設定 `skip_response_check=True` 以允許韌體內部處理錯誤而不立即回報 Host 錯誤。
     5. 透過 VU 4013 讀取 BE Fail 狀態。
     6. 透過 VU 405E 讀取更新後的 BBT 資料，並計算新的壞塊計數 (`BB_count_new`) 及 BBT 列表 (`BB_data_new`)。
     7. 驗證 `BB_count_new` 是否等於 `BB_count + 1`。
     8. 搜尋 `BB_data_new`，確認包含目標區塊資訊 (`target_data_L2`: Block=`L2_vb`, CE=0, Plane=0) 的條目存在。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明壞塊計數器正確遞增。
     - `BB_data_new` 中必須能找到與 `target_data_L2` 完全匹配的條目，證明當前 L2 VB 已被正確標記為壞塊並記錄在 BBT 中。
     - 韌體在處理 Program Fail 後保持穩定，無 Assert 發生，符合 VC-31 對於 "selection new PB succeed on the first try" 且 "no assert" 的驗證要求。