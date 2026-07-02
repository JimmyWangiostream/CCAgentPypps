# Test Spec: VC-35 (13.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生寫入失敗（Program Fail）時的替換區塊（Replacement Block）選擇邏輯與壞塊表（BBT）更新機制：
1. **Case 01 (L2 Replacement)**：確認當預測的下一個替換區塊位於 Revoke Group 時，韌體能透過強制產生 L2 區塊的 Erase Fail，觸發 L2 VB 切換，並驗證該 L2 區塊被正確標記為壞塊（BB Count +1 且 BBT 中存在）。
2. **Case 02 (LOG & Replacement PF)**：確認當預測的下一個替換區塊不在 Revoke Group 時，韌體在 LOG 區塊切換過程中，若同時對「當前 LOG 區塊」與「預測替換區塊」注入 Program Fail，系統應能正確處理雙重失敗，驗證 BB Count 增加 2，且 BBT 中同時包含這兩個區塊的記錄，代表韌體未因替換區塊失效而 Assert，並正確更新了 BB Table。

## Test Case (TC) Checkpoints

1. [Case01_L2_EraseFail_RevokeGroup_Check]：
   - 動作：
     1. 透過 VU 40C1 與 40DC 獲取當前 L2 VB 與下一個 L2 VB。
     2. 透過 VU 405E 記錄初始 BB Count。
     3. 透過 VU 40D6 獲取預測的下一個替換區塊（Next Replacement Block）。
     4. 檢查該替換區塊是否屬於 Revoke Group。若屬於，則透過 VU C012 對該 Next L2 VB 注入 Erase Fail (fail_type=1)。
     5. 執行連續 Write10 操作，直到 VU 40C1 顯示 L2 VB 發生切換。
     6. 透過 VU 4013 獲取 BE Fail 狀態，並透過 VU 405E 讀取新的 BB Count 與 BBT 數據。
   - 預期結果：
     - 新的 BB Count 必須等於初始 BB Count + 1。
     - BBT 數據中必須包含被注入 Erase Fail 的 L2 區塊資訊（Block, CE, Plane）。
     - 此流程驗證當替換區塊受限於 Revoke Group 時，系統透過 L2 層級的 Erase Fail 觸發替換機制，並正確更新壞塊表。

2. [Case02_LOG_Replacement_PF_DoubleFail_Check]：
   - 動作：
     1. 透過 VU 40C1 與 40DC 獲取當前 LOG VB 與下一個 LOG VB。
     2. 透過 VU 405E 記錄初始 BB Count。
     3. 透過 VU 40D6 獲取預測的下一個替換區塊（Next Replacement Block）。
     4. 確認該替換區塊**不**在 Revoke Group 中（進入 step1 邏輯）。
     5. 透過 VU C012 同時對「下一個 LOG VB」與「預測替換區塊」注入 Program Fail (fail_type=0, block_info_list_count=2)。
     6. 執行隨機 Write10 操作，直到 VU 40C1 顯示 LOG VB 發生切換。
     7. 透過 VU 4013 獲取 BE Fail 狀態，並透過 VU 405E 讀取新的 BB Count 與 BBT 數據。
   - 預期結果：
     - 新的 BB Count 必須等於初始 BB Count + 2。
     - BBT 數據中必須同時包含「下一個 LOG VB」與「預測替換區塊」的資訊。
     - 此流程驗證韌體在替換區塊也發生 Program Fail 的極端情境下，仍能正確識別並標記兩個失效區塊，更新 BB Table，且未觸發韌體 Assert 或崩潰。