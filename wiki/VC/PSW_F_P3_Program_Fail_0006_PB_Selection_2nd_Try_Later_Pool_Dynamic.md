# Test Spec: VC-35 (13.g) Program Fail with Replacement Block Selection Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生寫入失敗（Program Fail）且初始預測的替換區塊（Replacement Block）位於撤銷群組（Revoke Group）時，硬體行為與韌體恢復機制：
1. **預處理階段**：確認當 `VU 40D6` 預測的下一個替換區塊屬於 `REVOKE_BLK` 時，透過 `VU C012` 強制在該 L2 VB 觸發 Erase Fail，迫使韌體跳過該區塊並尋找新的替換區塊，直到預測區塊不再屬於撤銷群組為止。
2. **主測試階段**：針對當前 L2 VB 及其預測的替換區塊同時注入 Program Fail (`fail_type=0`)，執行寫入指令後，驗證：
   - 寫入指令返回非成功狀態（隱含於 `skip_response_check` 與後續檢查）。
   - Bad Block Table (BBT) 正確更新，Bad Block (BB) 計數增加 2（L2 VB 與替換區塊均標記為壞塊）。
   - BBT 數據中明確包含 L2 VB 與替換區塊的物理地址資訊。
   - 韌體未發生 Assert 崩潰，系統保持穩定。

## Test Case (TC) Checkpoints

1. [PreProcess_RevokeBlock_Skip_Check]：
   - 動作：
     1. 透過 `VU 40C1` 獲取當前 L2 Open VB (`L2_vb`)，透過 `VU 40DC` 獲取下一個 L2 VB (`L2_vb_next`)。
     2. 記錄當前 BB 計數 (`BB_count`) 與 `VU 40D6` 預測的下一個替換區塊 (`next_replacement_block`)。
     3. 檢查 `next_replacement_block` 是否屬於 `REVOKE_BLK` 群組。若是，則透過 `VU C012` 在 `L2_vb_next` 注入 Erase Fail (`fail_type=1`)。
     4. 執行連續寫入 (`Write10`) 直到 L2 VB 發生切換，確認該 Erase Fail 生效。
     5. 透過 `VU 4013` 獲取 BE Fail 狀態，並透過 `VU 405E` 驗證 BB 計數增加 1 且 BBT 中新增該目標區塊。
     6. 重複上述流程（Flow 1-8），直到 `VU 40D6` 預測的替換區塊**不**在 `REVOKE_BLK` 群組中為止。
   - 預期結果：
     - 當替換區塊屬於撤銷群組時，韌體應能識別並跳過，透過強制 Erase Fail 觸發重新選擇機制。
     - 每次循環後，`BB_count` 應精確增加 1。
     - BBT 數據中必須包含被標記為壞塊的 `L2_vb_next` 資訊。
     - 最終狀態為：`next_replacement_block` 不在撤銷群組，且系統未 Assert。

2. [MainTest_Double_PF_BBT_Update_Check]：
   - 動作：
     1. 獲取當前 L2 VB (`L2_vb`) 與 `VU 40D6` 預測的替換區塊 (`next_replacement_block`)。
     2. 記錄當前 BB 計數 (`BB_count`)。
     3. 透過 `VU C012` 同時對 L2 VB 與替換區塊注入 Program Fail (`fail_type=0`, `block_info_list_count=2`)。
     4. 執行單次 `Write10` 寫入 (`lun=0`, `lba=0`, `length=WRITE_10_MAX_BLOCK_LEN`)，設定 `skip_response_check=True` 以允許失敗返回。
     5. 透過 `VU 4013` 獲取 BE Fail 狀態。
     6. 透過 `VU 405E` 獲取新的 BB 資訊，計算 BBT 數據。
   - 預期結果：
     - 新的 BB 計數 (`BB_count_new`) 必須等於 `BB_count + 2`。
     - BBT 數據中必須同時找到 L2 VB (`target_data_L2`) 與替換區塊 (`target_data_replace`) 的物理地址資訊（CE, Plane, Block）。
     - 若任一區塊未出現在 BBT 中，測試應報錯 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 韌體處理完雙重 Program Fail 後，BBT 更新正確，無 Assert 發生。