# Test Spec: VC-31 (12.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇 Program Fail (PF) 時的 Bad Block Table (BBT) 更新機制與替換區塊（Replacement Block）選擇邏輯：
1. **Pre-process 階段**：確認韌體在動態替換池（Dynamic Replacement Pool）中預測的下一個替換區塊（Next Replacement Block）若屬於 Revoke Group（已撤銷區塊），則透過 Vendor Command `C012` 強制在該預測區塊注入 Program Fail，並透過寫入操作觸發 L2 VB 切換，驗證韌體能正確識別該區塊失效並將其標記為 Bad Block。
2. **Step1 階段**：針對 EM1 LUN 的當前 L2 VB 區塊，透過 Vendor Command `C012` 注入 Program Fail，隨後執行寫入操作，驗證韌體能立即捕捉錯誤狀態，正確更新 BBT 計數器（BB Count +1），並將該失效區塊精確記錄在 BBT 中，同時確認無 Assert 發生。

## Test Case (TC) Checkpoints
1. [PreProcess_PredictedBlock_Fail_Check]：
   - 動作：
     1. 配置 LUN 0 為 Normal，LUN 1 為 EM1。
     2. 在 EM1 LUN (LUN 1) 寫入 4KB 資料以初始化狀態。
     3. 獲取當前 Revoke Group 列表。
     4. 循環執行以下檢查：
        - 透過 Vendor Command `40C1` 獲取當前 L2 Open Logical VB (`L2_vb`)。
        - 透過 Vendor Command `40DC` 獲取下一個 L2 Open VB (`L2_vb_next`)。
        - 透過 Vendor Command `405E` 記錄當前 Bad Block 計數 (`BB_count`)。
        - 透過 Vendor Command `40D6` 獲取預測的下一個替換區塊 (`next_replacement_block`)，參數設定為 `pool_type=1` (Dynamic Pool)。
        - **判斷邏輯**：若 `next_replacement_block` **不在** Revoke Group 中，則跳出循環；若在 Revoke Group 中，則執行以下故障注入：
          - 透過 Vendor Command `C012` 在 `next_replacement_block` (CE=0, Plane=0) 注入 Program Fail (`fail_type=1`)。
          - 在 Normal LUN (LUN 0) 從 LBA 0 開始連續寫入，直到讀取到的 `L2_vb` 發生改變（證明寫入觸發了區塊替換或狀態變更）。
          - 透過 Vendor Command `4013` 獲取 BE (Bad Error) 狀態。
          - 透過 Vendor Command `405E` 獲取新的 BBT 數據，驗證 `BB_count_new` 是否等於 `BB_count + 1`，並驗證 BBT 中是否包含剛才注入故障的區塊資訊。
   - 預期結果：
     - 當 `next_replacement_block` 首次不在 Revoke Group 時，循環終止。
     - 在循環內，每次注入故障後，BB Count 必須精確增加 1。
     - BBT 數據中必須包含被注入故障的區塊資訊（Block, CE, Plane 匹配）。
     - 此階段驗證韌體在預測替換區塊無效時，能透過強制故障觸發正確的 BBT 更新流程。

2. [Step1_EM1_L2_PF_BBT_Update_Check]：
   - 動作：
     1. 透過 Vendor Command `40C1` 獲取 EM1 LUN (LUN 1) 當前的 L2 VB (`L2_vb`)。
     2. 透過 Vendor Command `405E` 記錄當前 Bad Block 計數 (`BB_count`)。
     3. 透過 Vendor Command `C012` 在該 `L2_vb` (CE=0, Plane=0) 注入 Program Fail (`fail_type=0`)。
     4. 在 EM1 LUN (LUN 1) 從 LBA 0 開始寫入 4KB 資料，並設定 `skip_response_check=True` 以允許錯誤響應。
     5. 透過 Vendor Command `4013` 獲取 BE Fail 狀態。
     6. 透過 Vendor Command `405E` 獲取新的 BBT 數據。
     7. 驗證 `BB_count_new` 是否等於 `BB_count + 1`。
     8. 驗證 BBT 數據中是否包含剛才注入故障的 `L2_vb` 區塊資訊。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`。
     - BBT 數據中必須找到與 `L2_vb` (CE=0, Plane=0) 完全匹配的條目。
     - 韌體應成功處理 Program Fail 事件，更新 BBT，且未觸發 Assert 或系統崩潰，符合 VC-31 中 "FW should be update BB table and no assert" 的要求。