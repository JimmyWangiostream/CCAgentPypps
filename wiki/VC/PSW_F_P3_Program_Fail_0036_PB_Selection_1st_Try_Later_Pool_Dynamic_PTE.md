# Test Spec: VC-31 (12.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在正常區域（Normal Area）與 PTE 區域發生 Program Fail 時的替換區塊（Replacement Block）選擇邏輯與 Bad Block Table (BBT) 更新機制：
1. **Normal Area 邏輯**：當目標替換區塊位於 Revoke Group 時，強制注入 Program Fail 以觸發 L2 VB 切換，驗證韌體能正確將該區塊標記為 Bad Block 並更新 BBT，且無 Assert 發生。
2. **PTE Area 邏輯**：針對 PTE 區塊注入 Program Fail，驗證韌體能正確選擇新的替換區塊（Selection New PB Succeed），確保 PTE VB 號碼發生變更，並確認 BBT 中正確記錄了失效區塊資訊，代表韌體內部狀態機已正確處理 PTE 替換流程。

## Test Case (TC) Checkpoints

1. [Normal_Area_Revoke_Block_Fail_Check]：
   - 動作：
     1. 透過 VU 40C1 與 40DC 獲取當前 L2 Open VB (`L2_vb`) 與下一個 L2 VB (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 VU 40D6 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. **循環檢查**：若 `next_replacement_block` 屬於 Revoke Group，則透過 VU C012 對該區塊（CE=0, Plane=0, Block=`L2_vb_next`）注入 Program Fail (`fail_type=1`)。
     5. 執行順序寫入（Sequential Writes, LBA 從 0 開始遞增），持續監控 VU 40C1 返回的 `L2_vb`，直到 `L2_vb` 發生跳變（代表替換生效）。
     6. 透過 VU 4013 獲取 BE Fail 狀態，並透過 VU 405E 獲取新的 BBT 數據。
   - 預期結果：
     - 新的 Bad Block 計數 (`BB_count_new`) 必須等於初始計數加 1 (`BB_count + 1`)。
     - 計算後的 BBT 數據 (`BB_data_new`) 中必須包含目標區塊資訊（Block=`L2_vb_next`, CE=0, Plane=0），代表該區塊已被正確標記為 Bad Block。
     - 整個流程中韌體不應觸發 Assert 或崩潰。

2. [PTE_Area_Replacement_Success_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 PTE VB (`PTE_vb`)。
     2. 透過 VU 40DC 獲取下一個 PTE VB (`PTE_vb_next`)。
     3. 透過 VU 405E 記錄初始 Bad Block 計數 (`BB_count`)。
     4. 透過 VU C012 對 PTE 下一個區塊（CE=0, Plane=0, Block=`PTE_vb_next`）注入 Program Fail (`fail_type=0`)。
     5. 執行隨機寫入（Random Writes, LBA 隨機分佈），持續監控 VU 40C1 返回的 `PTE_vb`，直到 `PTE_vb` 發生跳變（代表 PTE 替換成功）。
     6. 透過 VU 4013 獲取 BE Fail 狀態，並透過 VU 405E 獲取新的 BBT 數據。
   - 預期結果：
     - 新的 Bad Block 計數 (`BB_count_new`) 必須等於初始計數加 1 (`BB_count + 1`)。
     - 計算後的 BBT 數據 (`BB_data_new`) 中必須包含目標 PTE 區塊資訊（Block=`PTE_vb_next`, CE=0, Plane=0）。
     - `PTE_vb` 必須發生變更，代表韌體成功選擇了新的替換區塊並更新了 PTE 狀態，符合 "selection new PB succeed" 的驗證目標。