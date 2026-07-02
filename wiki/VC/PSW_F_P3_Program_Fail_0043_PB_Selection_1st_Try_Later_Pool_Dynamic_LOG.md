# Test Spec: VC-31 (12.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇 Program/Erase Fail (PF) 時的 Bad Block Table (BBT) 更新機制與替換區塊（Replacement Block）選擇邏輯：
1. **動態替換區 (Dynamic Replacement Pool) 驗證**：確認當目標 L2 VB 區塊位於非 Revoke Group 時，韌體能正確識別並標記該區塊為 Bad Block，且 BBT 計數器準確增加；同時驗證 `VU 40D6` 預測的下一個替換區塊邏輯符合預期（即跳過 Revoke Group 區塊）。
2. **LOG 區塊 (LOG VB) 驗證**：確認當目標 LOG VB 區塊發生 PF 時，韌體能正確將其標記為 Bad Block，BBT 計數器準確增加，且 LOG 狀態機能正確切換至新的 LOG VB，確保系統元數據的完整性與恢復能力。

## Test Case (TC) Checkpoints

1. [Case01_Dynamic_Replacement_Pool_PF_Check]：
   - 動作：
     1. 透過 `VU 40C1` 獲取當前 L2 Open VB (`L2_vb`)，透過 `VU 40DC` 獲取下一個 L2 VB (`L2_vb_next`)。
     2. 透過 `VU 405E` 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 `VU 40D6` 獲取預測的下一個替換區塊 (`next_replacement_block`)。
     4. **循環檢查**：若 `next_replacement_block` 屬於 Revoke Group (`revoke_group`)，則透過 `VU C012` (fail_type=1) 對 `L2_vb_next` 注入 Program/Erase Fail，隨後執行連續 Write10 操作直到 `L2_vb` 發生切換（觸發 L2 VB 遷移），並確認 PF 生效。重複此過程直到 `VU 40D6` 返回的 `next_replacement_block` **不在** Revoke Group 中。
     5. 當條件滿足時，記錄目標區塊資訊 (`target_data_L2`)。
     6. 執行連續 Write10 直到 `L2_vb` 切換，觸發該區塊的 PF 處理流程。
     7. 透過 `VU 4013` 讀取 BE (Bad Endurance) Fail 狀態。
     8. 透過 `VU 405E` 獲取新的 BBT 數據，計算 `BB_count_new` 並解析 BBT 列表。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明 Bad Block 計數器正確遞增。
     - 解析後的 BBT 數據 (`BB_data_new`) 中必須包含 `target_data_L2` (Block, CE, Plane)，證明該 L2 VB 區塊已被正確標記為 Bad Block 並進入替換池。
     - 韌體未發生 Assert 或崩潰，系統狀態穩定。

2. [Case02_LOG_VB_PF_Check]：
   - 動作：
     1. 透過 `VU 40C1` 獲取當前 LOG VB (`LOG_vb`)，透過 `VU 40DC` 獲取下一個 LOG VB (`LOG_vb_next`)。
     2. 透過 `VU 405E` 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 `VU C012` (fail_type=0) 對 `LOG_vb_next` (CE=0, Plane=0) 注入 Program/Erase Fail。
     4. 記錄目標區塊資訊 (`target_data_LOG`)。
     5. 執行隨機 Write10 操作（LBA 隨機範圍），直到 `LOG_vb` 發生切換（觸發 LOG 區塊遷移），確保 PF 被韌體檢測並處理。
     6. 透過 `VU 4013` 讀取 BE Fail 狀態。
     7. 透過 `VU 405E` 獲取新的 BBT 數據，計算 `BB_count_new` 並解析 BBT 列表。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明 LOG 區塊的 PF 也被正確計入 Bad Block 總數。
     - 解析後的 BBT 數據 (`BB_data_new`) 中必須包含 `target_data_LOG` (Block, CE, Plane)，證明 LOG VB 區塊已被正確標記為 Bad Block。
     - LOG 狀態機成功切換至新的 LOG VB，系統元數據結構完整，無數據損壞或邏輯錯誤。