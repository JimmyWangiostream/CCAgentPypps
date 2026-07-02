# Test Spec: VC-31 (12.g) Write Booster Program Fail Replacement Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Write Booster (WB) LUN 遭遇 Program Fail 時的壞塊管理與替換機制：
1. **Pre-process (L2 替換池預熱)**：透過 Vendor Command (VU C012) 強制在 Normal LUN 的 L2 VB 產生 Program Fail，觸發韌體將該區塊標記為 Bad Block 並從 "Later Replacement Pool" (Shared Dynamic Pool) 分配新的替換區塊。此階段旨在確保替換池中有可用的備用區塊，且驗證韌體能正確更新 Bad Block Table (BBT) 而不會 Assert。
2. **Step1 (WB L2 實際替換驗證)**：針對 Write Booster LUN (LUN 2) 的當前 L2 VB 注入 Program Fail (fail_type=0)，隨後執行 Write10 寫入操作。驗證韌體是否能成功識別錯誤、將原 L2 VB 標記為壞塊（BB Count +1 且 BBT 中出現該 Block 資訊），並關鍵性地確認韌體是否從替換池中選取了一個新的 PB (Physical Block) 來承接後續寫入，且整個過程無韌體崩潰 (Assert)。

## Test Case (TC) Checkpoints

1. [PreProcess_L2_PF_Replacement_Pool_Check]：
   - 動作：
     1. 配置 LUN 0 (Normal), LUN 1 (EM1), LUN 2 (WB)。
     2. 透過 VU 40C1 與 40DC 獲取當前 L2 VB 與下一個 L2 VB，並透過 VU 405E 記錄初始 BB Count。
     3. 透過 VU 40D6 查詢 "Later Replacement Pool" (pool_type=1) 的預測下一個替換區塊。
     4. 若預測區塊不在 Revoke Group，則透過 VU C012 (fail_type=1) 在 Normal LUN 的下一個 L2 VB 強制注入 Program Fail。
     5. 對 Normal LUN (LUN 0) 執行連續 Write10，直到 L2 VB 發生切換（代表韌體已處理完 Fail 並切換到新的替換區塊）。
     6. 透過 VU 4013 檢查 BE Fail Status，並透過 VU 405E 再次獲取 BB Count 與 BBT 數據。
   - 預期結果：
     - BB Count 必須等於初始值 + 1。
     - BBT 數據中必須包含被注入 Fail 的 Block 資訊（Block, CE, Plane 匹配）。
     - 韌體未發生 Assert，成功將原 L2 VB 標記為壞塊並從替換池分配新區塊。

2. [Step1_WB_L2_PF_Successful_Replacement_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取 Write Booster LUN (LUN 2) 當前的 L2 VB 號碼。
     2. 透過 VU 405E 記錄當前 BB Count。
     3. 透過 VU C012 (fail_type=0) 在 WB LUN 的當前 L2 VB 強制注入 Program Fail。
     4. 設定 Flag `WRITEBOOSTER_EN` 為 True。
     5. 對 WB LUN (LUN 2) 執行單次 Write10 (LBA 0, Length=Max Block Len)，並使用 `skip_response_check=True` 發送以模擬韌體內部處理 Fail 的情境。
     6. 透過 VU 4013 檢查 BE Fail Status。
     7. 透過 VU 405E 獲取新的 BB Count 與 BBT 數據。
   - 預期結果：
     - BB Count 必須等於 Step1 開始前的值 + 1。
     - BBT 數據中必須包含被注入 Fail 的 WB L2 VB 區塊資訊。
     - 韌體成功處理 Program Fail，未發生 Assert，且根據 VC-31 要求，應已成功從替換池選取新的 Physical Block 進行後續寫入（儘管腳本主要驗證 BBT 更新與無 Assert，但此為 VC 的核心預期行為）。