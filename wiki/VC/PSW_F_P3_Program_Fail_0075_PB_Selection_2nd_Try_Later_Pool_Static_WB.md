# Test Spec: WB LUN Program Fail with Double Replacement Block Injection (VC-36)

## Verification Criterion (VC)
驗證 Write Booster (WB) LUN 在遭遇連續 Program Fail 情境下的韌體行為：當 L2 Open Block 及其預判的下一個 Replacement Block 同時被注入 Program Fail 時，韌體應觸發 Assert 0x203 並進入非 Read-Only 的掛起狀態（Device remains unresponsive），而非強制進入 Read-Only 模式。此測試旨在確認在 WB 啟用且替換池資源耗盡（或雙重失敗）的極端情況下，FW 的錯誤處理機制與狀態機轉換邏輯。

## Test Case (TC) Checkpoints
1. [PreProcess_L2_EF_Creation]：
   - 動作：
     1. 配置 LUN 0 (Normal), 1 (EM1), 2 (WB) 為測試對象。
     2. 透過 VU 0x40C1 讀取當前 L2 Open VB (`L2_vb`)，並透過 VU 0x40DC 讀取下一個 Open VB (`L2_vb_next`)。
     3. 記錄當前 Bad Block Count (`BB_count`) 及透過 VU 0x40D6 讀取預測的接下來兩個 Replacement Block (`next_replacement_block_1`, `next_replacement_block_2`)。
     4. 讀取 FW 內部變數 `gUfsApiStruct.ftl->bbt.max_revoke_cnt` 與 `revoke_cnt`。
     5. 若 `revoke_cnt` 已達 `max_revoke_cnt` 且 `next_replacement_block_2` 不為 0xFFFF，則跳出循環；否則，透過 VU 0xC012 對 `L2_vb_next` 注入 Erase Fail (fail_type=1)。
     6. 對 LUN 0 進行連續 Write10 寫入，直到 L2 Open VB 發生跳變（即 `L2_vb_new != L2_vb`），確保目標 Block 被選為新的 L2 Open Block。
     7. 透過 VU 0x4013 檢查 BE Fail 狀態，並透過 VU 0x405E 重新讀取 BB 資訊。
     8. 驗證新的 BB Count (`BB_count_new`) 必須等於 `BB_count + 1`，且 `BB_data_new` 中必須包含目標 Block (`target_data_L2`) 的記錄。
     9. 重複上述流程直到滿足跳出條件（替換池預測區塊剩餘不足或 Revoke 計數滿）。
   - 預期結果：
     - 每次注入 Erase Fail 後，BB Count 必須精確增加 1。
     - 目標 Block 必須成功被標記為 Bad Block 並記錄在 BBT 中。
     - 循環最終在 `bbt_revoke_cnt == bbtmax_revoke_cnt` 且 `next_replacement_block_2 != 0xFFFF` 時結束，確保後續測試處於替換資源極限狀態。

2. [Step1_Double_PF_Assert_Check]：
   - 動作：
     1. 透過 VU 0x40C1 讀取 WB LUN (LUN 2) 的當前 L2 Open VB (`L2_vb`)。
     2. 透過 VU 0x40D6 讀取預測的下一個 Replacement Block (`next_replacement_block`)。
     3. 透過 VU 0xC012 同時對 `L2_vb` (當前 L2) 與 `next_replacement_block` (下一個替換塊) 注入 Program Fail (fail_type=0, block_info_list_count=2)。
     4. 啟用 Write Booster 標誌 (`api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)`)。
     5. 對 LUN 2 (WB LUN) 發送 Write10 命令，長度為 `WRITE_10_MAX_BLOCK_LEN`。
     6. 捕獲 `G_TIMEOUT_ALL` 異常。
     7. 檢查 FW Assert 編號是否為 `0x203`。
   - 預期結果：
     - Write10 命令必須超時並拋出 `G_TIMEOUT_ALL` 異常，證明設備在初始化後處於無響應狀態。
     - FW Assert 編號必須精確等於 `0x203`。
     - **關鍵驗證點**：韌體必須停留在 Assert 狀態（Device remains unresponsive），且**不得**進入 Read-Only 模式（若進入 Read-Only 模式通常會返回特定的 Read-Only 狀態碼或允許讀取，但此處預期為 Assert 掛起）。這驗證了在 WB 啟用且連續替換塊失敗時，FW 觸發了特定的 Assert 機制而非標準的 RO 保護機制。