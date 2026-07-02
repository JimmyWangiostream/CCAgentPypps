# Test Spec: UFS Vendor Command 40EE Clock Tree Frequency Verification

## Verification Criterion (VC)
驗證透過 Vendor Command 0x40EE 讀取韌體內部時脈樹狀結構（Clock Tree）的硬體時脈狀態：確認 CPU 核心時脈（Group 2）為 667 MHz、系統緩衝區與 COP0 時脈（Group 3）為 200 MHz、LDPC 解碼器與編碼器時脈（Domain 12 & 13）為 266 MHz，以及 ONFI PHY MDLL 時脈（Domain 15）為 1600 MHz。此測試旨在確認韌體在當前運行狀態下，各關鍵硬體模組的時脈分頻與配置符合設計規範，且 Vendor Command 的資料回傳機制正確無誤。

## Test Case (TC) Checkpoints
1. [VCMD_40EE_Clock_Freq_Check]：
   - 動作：呼叫 `project_api.issue_40EE_to_get_current_clk_freq()` 發送 Vendor Command 0x40EE 至 UFS 裝置，獲取包含時脈樹狀結構資訊的回應資料物件 `data`。接著分別讀取並比對以下欄位數值：
     1. `data.clk_tree_grp2_cpu.value` 與預期值 667 進行比對。
     2. `data.clk_tree_grp3_buf.value` 與預期值 200 進行比對。
     3. `data.clk_tree_grp3_cop0.value` 與預期值 200 進行比對。
     4. `data.domain_12_ldpc_dec_clk.value` 與預期值 266 進行比對。
     5. `data.domain_13_ldpc_enc_clk.value` 與預期值 266 進行比對。
     6. `data.domain_15_onfi_phy_mdll.value` 與預期值 1600 進行比對。
     若任何欄位數值與預期值不符，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常並記錄錯誤日誌。
   - 預期結果：
     - `clk_tree_grp2_cpu` 必須等於 667 (MHz)，代表 CPU 核心運行於指定時脈。
     - `clk_tree_grp3_buf` 與 `clk_tree_grp3_cop0` 必須均等於 200 (MHz)，代表系統緩衝區與 COP0 模組時脈正確。
     - `domain_12_ldpc_dec_clk` 與 `domain_13_ldpc_enc_clk` 必須均等於 266 (MHz)，代表 LDPC 編解碼器時脈配置正確。
     - `domain_15_onfi_phy_mdll` 必須等於 1600 (MHz)，代表 ONFI PHY 的 MDLL 時脈鎖定於預期頻率。
     - 所有比對成功後，測試通過，確認 Vendor Command 0x40EE 能正確回傳硬體時脈狀態且數值符合規格。