# Test Spec: VC-42 (15.g) Program Fail with Replacement Block Selection Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生寫入失敗（Program Fail）且預設替換區塊（Next Replacement Block）也同時失效的情境下，UFS 控制器的錯誤處理與壞塊管理機制：
1. **第一階段（Pre-process）**：確認當預設替換區塊位於 Revoke Group 時，透過注入 Erase Fail 強制將目標 L2 VB 標記為壞塊，並驗證 BBT 正確更新且無 Assert。
2. **第二階段（Step1 - 核心驗證）**：在正常區域寫入至空 SLC 頁面後，針對當前 L2 VB 及其預設替換區塊同時注入 Program Fail。驗證韌體能否正確識別雙重失敗，將 BB 計數增加 2，並將這兩個區塊（L2 VB 與 Replacement Block）均正確標記為壞塊進入 BBT，同時確保韌體未因多重錯誤而崩潰（No Assert）。

## Test Case (TC) Checkpoints

1. [PreProcess_EraseFail_RevokeGroup_Check]：
   - 動作：
     1. 透過 VU 40C1/40DC 獲取當前 L2 VB 與下一個 L2 VB。
     2. 透過 VU 40D6 獲取預測的下一個替換區塊（Next Replacement Block）。
     3. 若該替換區塊屬於 Revoke Group，則透過 VU C012 對該 Next L2 VB 的 Page 0 注入 Erase Fail (fail_type=1)。
     4. 執行連續 Write10 直到 L2 VB 切換，觸發實際的 Erase Fail。
     5. 透過 VU 405E 讀取壞塊資訊，計算 BBT。
   - 預期結果：
     - BB 計數必須等於注入前 + 1。
     - BBT 中必須包含被注入 Erase Fail 的目標 L2 VB 區塊資訊。
     - 韌體無 Assert，BB Table 更新正確。

2. [Step1_DualProgramFail_BBT_Update_Check]：
   - 動作：
     1. 執行連續 Write10 (16 Bytes) 直到 TLC L2 的 First Empty Physical Page 達到 3308，確保進入正常寫入區域。
     2. 獲取當前 L2 VB 號碼及對應的 First Empty Physical Page。
     3. 將 Physical Page 轉換為 Logical Page（根據 region_max_wl 規則：Page < 1620 為 /3, 1620-1652 為 /2+540, 1652-3308 為 /3+556）。
     4. 透過 VU 40D6 獲取當前 L2 VB 的預設替換區塊號碼。
     5. 透過 VU C012 同時注入兩個 Program Fail (fail_type=3)：
        - 目標 1：當前 L2 VB 的計算出的 Logical Page。
        - 目標 2：預設替換區塊的 Page 0。
     6. 執行 Write10 (4KB) 觸發寫入失敗。
     7. 透過 VU 4013 獲取 BE Fail Status。
     8. 透過 VU 405E 讀取壞塊資訊並計算 BBT。
   - 預期結果：
     - BB 計數必須等於注入前 + 2。
     - BBT 中必須同時包含「當前 L2 VB」與「預設替換區塊」這兩個區塊的資訊。
     - 韌體未發生 Assert，證明在替換區塊也失效的情況下，韌體能正確處理雙重 Program Fail 並更新壞塊表。