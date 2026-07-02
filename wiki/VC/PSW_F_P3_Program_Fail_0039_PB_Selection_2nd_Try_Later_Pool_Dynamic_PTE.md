# Test Spec: VC-35 (13.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在快閃記憶體發生 Program/Erase Fail (PF) 時的 Bad Block Table (BBT) 更新機制與 Replacement Pool 選擇邏輯：
1. **Normal Area (Dynamic Replacement)**：當 L2 Open VB 區塊發生 PF 且其預設的 Next Replacement Block 位於 Revoke Group 時，韌體應能正確識別並跳過該無效區塊，從 Latereplacement Pool (Shared for Dynamic) 中選取新的替換區塊。驗證 BBT 中新增的 Bad Block 數量增加 1，且該新替換區塊被正確標記為 Bad Block。
2. **PTE Area (Static Replacement)**：當 PTE Open VB 區塊發生 PF 時，韌體應同時將 PTE 區塊及其預設的 Next Replacement Block 標記為 Bad Block。驗證 BBT 中新增的 Bad Block 數量增加 2，且 PTE 區塊與替換區塊均被正確記錄在 BBT 中，確保 PTE 數據完整性與替換機制正常運作。

## Test Case (TC) Checkpoints

1. **[Case01_Normal_L2_PF_Replacement_Check]**：
   - 動作：
     1. 透過 VU 40C1 與 40DC 獲取當前 L2 Open VB (`L2_vb`) 與下一個 L2 VB (`L2_vb_next`)。
     2. 透過 VU 405E 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 VU 40D6 獲取預設的下一個替換區塊 (`next_replacement_block`)。
     4. **循環檢查**：若 `next_replacement_block` 屬於 Revoke Group，則透過 VU C012 (fail_type=1) 對 `L2_vb_next` 注入 Erase Fail，強制 L2 VB 切換，重複步驟 1-3 直到獲取到一個不在 Revoke Group 的有效替換區塊。
     5. 對 Normal LUN (LUN 0) 執行連續 Write10 操作，直到 L2 Open VB 發生切換（即寫入觸發了 L2 VB 的遷移）。
     6. 透過 VU 4013 獲取 BE Fail 狀態，並透過 VU 405E 獲取新的 BBT 數據。
   - 預期結果：
     - 新的 Bad Block 計數 (`BB_count_new`) 必須等於 `BB_count + 1`。
     - 解析後的 BBT 數據 (`BB_data_new`) 中，必須包含目標 L2 區塊 (`target_data_L2`) 的記錄，證明韌體已將發生 PF 的 L2 區塊標記為 Bad Block。
     - 此步驟驗證韌體在動態替換池 (Dynamic Replacement Pool) 中，能正確處理 Revoke Block 並選取有效的 Latereplacement Block。

2. **[Case02_PTE_PF_Dual_Block_Marking_Check]**：
   - 動作：
     1. 透過 VU 40C1 與 40DC 獲取當前 PTE Open VB (`PTE_vb`) 與下一個 PTE VB (`PTE_vb_next`)。
     2. 透過 VU 405E 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 VU 40D6 獲取預設的下一個替換區塊 (`next_replacement_block`)。
     4. 透過 VU C012 (fail_type=0, block_info_list_count=2) 同時對 `PTE_vb_next` (Block 0) 與 `next_replacement_block` (Block 1) 注入 Program Fail。
     5. 對 Normal LUN (LUN 0) 執行隨機 Write10 操作，直到 PTE Open VB 發生切換。
     6. 透過 VU 4013 獲取 BE Fail 狀態，並透過 VU 405E 獲取新的 BBT 數據。
   - 預期結果：
     - 新的 Bad Block 計數 (`BB_count_new`) 必須等於 `BB_count + 2`。
     - 解析後的 BBT 數據 (`BB_data_new`) 中，必須同時包含目標 PTE 區塊 (`target_data_PTE`) 與目標替換區塊 (`target_data_replace`) 的記錄。
     - 此步驟驗證韌體在 PTE 區域發生 PF 時，能正確將 PTE 區塊及其預設替換區塊雙雙標記為 Bad Block，確保 PTE 結構的完整性與替換機制的正確性。