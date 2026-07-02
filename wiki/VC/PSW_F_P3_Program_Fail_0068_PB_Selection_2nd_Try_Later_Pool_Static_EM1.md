# Test Spec: VC-36 (13.h) Program Fail Recovery with BB Table Update and Read-Only Mode Enforcement

## Verification Criterion (VC)
驗證韌體在遭遇連續 Program/Erase Fail 導致備用區塊耗盡時的錯誤處理機制：
1. **預處理階段**：確認在 EM1 LUN (LUN 1) 上透過 VU C012 注入 Erase Fail 觸發 L2 VB 的 Erase Fail (EF)，並驗證 Bad Block Table (BBT) 正確更新（BB Count +1 且目標 Block 被標記為 Bad）。此階段需確保系統尚未進入 Read-Only 模式，且預測備用區塊池仍有剩餘空間（`next_replacement_block_2 != 0xFFFF`）。
2. **主測試階段 (Step 1)**：針對 EM1 LUN 進行寫入操作，同時透過 VU C012 注入 Program Fail (PF) 至當前 L2 VB 及其下一個預測備用區塊。驗證當備用區塊完全耗盡且無法修復時，裝置是否進入非響應狀態並觸發特定的韌體 Assert (0x203)，確認此狀態下裝置尚未強制進入 Read-Only 模式（或處於 Assert 掛起狀態），而非正常恢復。

## Test Case (TC) Checkpoints
1. [PreProcess_EF_Trigger_BBT_Update_Check]：
   - 動作：
     1. 配置 LUN 0 為 Normal，LUN 1 (EM1) 為測試目標。
     2. 在 LUN 1 寫入 4KB 資料以初始化。
     3. 透過 VU 40C1 讀取當前 L2 Open VB (`L2_vb`)，透過 VU 40DC 讀取下一個 L2 VB (`L2_vb_next`)。
     4. 透過 VU 405E 記錄初始 Bad Block Count (`BB_count`)。
     5. 透過 VU 40D6 讀取預測的接下來 2 個備用區塊 (`next_replacement_block_1`, `next_replacement_block_2`)，並讀取 FW 內部變數 `gUfsApiStruct.ftl->bbt.max_revoke_cnt` 與 `revoke_cnt`。
     6. 若 `revoke_cnt` 未達上限且 `next_replacement_block_2` 不為 0xFFFF，則透過 VU C012 對 `L2_vb_next` 注入 Erase Fail (`fail_type=1`)。
     7. 在 LUN 0 進行連續寫入，直到 L2 VB 切換至新的 VB（觸發對 `L2_vb_next` 的實際 Erase 操作，從而觸發預先注入的 EF）。
     8. 透過 VU 4013 檢查 BE Fail 狀態，並透過 VU 405E 再次讀取 BBT。
   - 預期結果：
     - 新的 BB Count (`BB_count_new`) 必須等於 `BB_count + 1`。
     - 計算後的 BBT 資料中必須包含目標 Block (`L2_vb_next`) 的資訊，確認該 Block 已被標記為 Bad。
     - 此循環持續進行直到備用區塊池接近耗盡（`revoke_cnt` 接近 `max_revoke_cnt` 或 `next_replacement_block_2` 變為 0xFFFF），確保後續測試是在備用資源極限情境下進行。

2. [Step1_Double_PF_Assert_0x203_Check]：
   - 動作：
     1. 透過 VU 40C1 讀取 EM1 LUN 當前的 L2 VB (`L2_vb`)。
     2. 透過 VU 40D6 讀取下一個預測備用區塊 (`next_replacement_block`)。
     3. 透過 VU C012 同時注入 Program Fail (`fail_type=0`) 至兩個區塊：
        - Block 0: 當前 L2 VB (`L2_vb`)。
        - Block 1: 下一個備用區塊 (`next_replacement_block`)。
     4. 在 EM1 LUN (LUN 1) 發起 Write10 命令寫入 4KB 資料。
     5. 捕獲命令執行時的異常，預期會拋出 `G_TIMEOUT_ALL` 異常。
     6. 在異常處理中，檢查 FW Assert 編號。
   - 預期結果：
     - 寫入命令必須超時並拋出 `G_TIMEOUT_ALL`，表示裝置在處理連續 Program Fail 且無可用備用區塊時進入非響應狀態。
     - `api.get_fw_assert_number()` 必須返回 `0x203`。
     - 這確認了韌體在備用區塊耗盡且無法修復 Program Fail 時，觸發了特定的 Assert 機制（0x203），且根據 VC 描述，此狀態對應於「Device remains unresponsive after initialization. Confirmed not in read-only mode」，即韌體選擇 Assert 而非自動切換至 Read-Only 模式（或在此測試情境下，Assert 發生在 Read-Only 強制切換之前/作為錯誤狀態的標記）。