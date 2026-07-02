# Test Spec: VC-19 (5.b) Erase Fail with Spare Block Exhaustion FW Stuck Test

## Verification Criterion (VC)
驗證當 Normal Area 的 Spare Block 耗盡且替換區塊（Replacement Block）亦發生 Erase Fail 時，韌體（FW）應進入死鎖（Stuck）狀態並觸發特定的 Assert 機制：Case 01 為預處理階段，透過連續寫入觸發 L2 VB 切換並注入單一 Erase Fail，確保系統處於可預測的臨界狀態；Case 02 為核心驗證，在 L2 VB 切換後，同時對目標 L2 VB 及其預測的第一個替換區塊（Next Replacement Block）注入 Erase Fail，隨後執行連續寫入，驗證 FW 因無法找到可用 Spare Block 而卡死，並確認 FW Assert 編號為 0x202，且 L2 VB 號碼不再發生變化。

## Test Case (TC) Checkpoints

1. [Case01_Preprocess_EF_Single_Check]：
   - 動作：透過 Vendor Command (VU 40C1) 讀取當前 L2 Open Logical VB (L2_vb)，並透過 VU 40DC 讀取下一個預期的 L2 VB (L2_vb_next)。記錄當前 Bad Block (BB) 計數。透過 VU 40D6 讀取預測的前兩個替換區塊地址。針對 L2_vb_next 所在的 CE 0, Plane 0 區塊，透過 VU C012 注入 Erase Fail (fail_type=1)。接著從 LBA 0 開始執行連續 Write10 指令，每次寫入 WRITE_10_MAX_BLOCK_LEN 長度，並持續透過 VU 40C1 監控 L2_vb 狀態，直到 L2_vb 發生跳變（L2_vb_new != L2_vb）為止。最後確認 BB 計數增加 1，且 BBT 中已包含該目標區塊。重複此流程直到 VU 40D6 返回的第二個替換區塊為 0xFFFF（表示僅剩一個可用替換區塊或即將耗盡）。
   - 預期結果：L2_vb 成功切換至 L2_vb_next；BB 計數精確增加 1；BBT 正確標記目標區塊為 Bad Block；系統進入預處理完成狀態，為後續的 Spare Block 耗盡情境做準備。

2. [Case02_Spare_Exhaustion_FW_Stuck_0x202_Check]：
   - 動作：重置 LUN 配置或確保處於 Case01 結束狀態。透過 VU 40C1 獲取當前 L2_vb，透過 VU 40DC 獲取 L2_vb_next。透過 VU 40D6 獲取下一個替換區塊 (next_replacement_block_1)。針對 CE 0, Plane 0 的 L2_vb_next **以及** next_replacement_block_1 這兩個區塊，透過 VU C012 同時注入 Erase Fail (fail_type=1, block_info_list_count=2)。隨後從 LBA 0 開始執行連續 Write10 指令。在發送 Write10 時設定 `skip_response_check=True` 以捕捉超時或異常。監控 FW Assert 狀態。
   - 預期結果：Write10 指令應觸發 G_TIMEOUT_ALL 異常或 FW 無回應；FW Assert 編號必須精確等於 0x202；透過 VU 40C1 讀取的 L2_vb_new 必須與注入前的 L2_vb 完全相同（無變化），證明韌體因無法分配 Spare Block 且替換區塊亦失效而陷入死鎖（Stuck），未執行任何邏輯推進。