# Test Spec: VC-35 (13.g) Program Fail with WB LUN Replacement Pool Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Write Booster (WB) LUN 遭遇連續 Program Fail 情境下的硬體行為與韌體恢復機制：
1. **Pre-process (L2 EF Handling)**：確認當 L2 VB 區塊因 Erase Fail (EF) 被標記為 Bad Block 後，韌體能正確更新 BB Table (BBT)，且未觸發 Assert 錯誤；同時驗證系統能預測並選擇新的 Replacement Block 進入 Revoke Group 以進行隔離。
2. **Step1 (L2 PF & Replacement PF Handling)**：在 WB LUN (LUN 2) 啟用狀態下，針對當前 L2 VB 及其預測的下一個 Replacement Block 同時注入 Program Fail (PF) 錯誤；驗證韌體能正確識別兩次寫入失敗，將 L2 VB 與 Replacement Block 均標記為 Bad Block (BB Count 增加 2)，並確認 BBT 中正確記錄了這兩個物理區塊的失效狀態，證明韌體在雙重 Fail 情境下仍能正確管理 Replacement Pool 並維持系統穩定。

## Test Case (TC) Checkpoints

1. [PreProcess_L2_EF_Revoke_Check]：
   - 動作：
     1. 配置 LUN 0 (Normal), LUN 1 (EM1), LUN 2 (WB)。
     2. 透過 Vendor Command (VC) 40C1 取得當前 L2 Open VB (`L2_vb`)，透過 VC 40DC 取得下一個 Open VB (`L2_vb_next`)。
     3. 透過 VC 405E 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 VC 40D6 預測下一個 Replacement Block (`next_replacement_block`)。
     5. 若 `next_replacement_block` 不在 Revoke Group 中，則透過 VC C012 對 `L2_vb_next` 注入 Erase Fail (fail_type=1)。
     6. 對 LUN 0 執行連續 Write10 寫入，直到 L2 VB 切換至新的 `L2_vb`。
     7. 透過 VC 4013 檢查 BE Fail Status，並透過 VC 405E 再次讀取 BB Count (`BB_count_new`) 及 BBT 資料。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - BBT 資料中必須包含被注入 EF 的 `L2_vb_next` 區塊資訊（Block, CE, Plane 匹配）。
     - 韌體未發生 Assert 崩潰，成功將該區塊標記為 Bad Block 並處理 Revoke 邏輯。

2. [Step1_WB_L2_PF_Replacement_PF_Check]：
   - 動作：
     1. 透過 VC 40C1 取得當前 WB LUN (LUN 2) 的 L2 VB (`L2_vb`)。
     2. 透過 VC 405E 記錄當前 BB Count (`BB_count`)。
     3. 透過 VC 40D6 取得下一個預測的 Replacement Block (`next_replacement_block`)。
     4. 透過 VC C012 同時對 `L2_vb` (Block 0) 與 `next_replacement_block` (Block 1) 注入 Program Fail (fail_type=0, block_info_list_count=2)。
     5. 啟用 Write Booster Flag (`api.FlagIDN.WRITEBOOSTER_EN`)。
     6. 對 LUN 2 (WB LUN) 執行一次 Write10 寫入 (LBA 0, Length 4KB)，並透過 `skip_response_check=True` 忽略 Host 端錯誤回應。
     7. 透過 VC 4013 檢查 BE Fail Status。
     8. 透過 VC 405E 讀取新的 BB Count (`BB_count_new`) 及 BBT 資料。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 2`。
     - BBT 資料中必須同時包含 `L2_vb` 與 `next_replacement_block` 兩個區塊的失效記錄。
     - 韌體正確處理了 WB LUN 上的連續 Program Fail，並正確更新了 Bad Block Table，無 Assert 發生。