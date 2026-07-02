# Test Spec: VC-36 (13.h) Program Fail with Exhausted Replacement Pool Recovery Test

## Verification Criterion (VC)
驗證當 UFS 韌體遭遇連續寫入失敗且備用區塊池（Replacement Pool）耗盡時的硬體行為與韌體保護機制：
1. **Pre-process 階段**：確認系統能透過 Vendor Command (VU 40D6) 預測並消耗備用區塊，直到剩餘可預測備用區塊數量不足（僅剩 1 個或為 0xFFFF），並透過 VU C012 在當前 L2 Open VB 注入 Program/Erase Fail，確保 Bad Block Table (BBT) 正確更新且 L2 VB 遷移。
2. **Step1 階段**：在 L2 VB 切換後，針對新的 Next Open VB 及其預測的第一個備用區塊同時注入 Program Fail (VU C012, block_info_list_count=2)，模擬備用區塊也失效的情境。
3. **核心驗證**：執行隨機寫入觸發寫入失敗後，韌體應進入 Assert 狀態（Assert Number 0x203），表示設備進入不可用狀態但尚未強制進入 Read-Only 模式；執行 HW_RESET 後，設備應恢復正常運作（Unit Ready），且 LOG VB 號碼必須發生改變（代表韌體嘗試修復或重置邏輯結構），若 LOG VB 未改變則視為韌體卡死（Stuck）。

## Test Case (TC) Checkpoints

1. [PreProcess_BBTable_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 L2 Open VB (`L2_vb`) 及透過 VU 40DC 獲取下一個 L2 Open VB (`L2_vb_next`)。
     2. 記錄當前 Bad Block Count (`BB_count`) 及透過 VU 40D6 獲取預測的接下來 2 個備用區塊 (`next_replacement_block_1`, `next_replacement_block_2`)。
     3. 讀取韌體內部變數 `gUfsApiStruct.ftl->bbt.max_revoke_cnt` 與 `revoke_cnt`。
     4. 若 `revoke_cnt == max_revoke_cnt` 且 `next_replacement_block_2 != 0xFFFF`，則透過 VU C012 在 `L2_vb_next` 注入 Program/Erase Fail (`fail_type=1`)。
     5. 從 LBA 0 開始順序寫入，直到 VU 40C1 返回的 L2 VB 發生變化，確認 L2 VB 已遷移。
     6. 透過 VU 4013 獲取 BE Fail 狀態，並透過 VU 405E 獲取新的 Bad Block 資訊。
     7. 計算 BBT 並驗證：新的 `BB_count` 必須等於舊的 `BB_count + 1`，且新的 BBT 資料中必須包含目標區塊 (`target_data_L2`)。
     8. 重複上述流程直到 VU 40D6 預測的下一個備用區塊為 0xFFFF 或 revoke_cnt 達到上限，確保備用資源被消耗至臨界點。
   - 預期結果：
     - 每次注入 Fail 後，BB Count 嚴格增加 1。
     - BBT 中正確記錄了被標記為 Bad 的區塊資訊。
     - L2 VB 在寫入失敗後成功遷移至新的邏輯區塊。
     - 最終狀態為備用區塊池即將耗盡，為 Step1 的雙重 Fail 情境做準備。

2. [Step1_Double_PF_Assert_0x203_Check]：
   - 動作：
     1. 透過 VU 40C1 獲取當前 LOG VB (`LOG_vb`) 及透過 VU 40DC 獲取下一個 LOG VB (`LOG_vb_next`)。
     2. 透過 VU 40D6 獲取預測的第一個備用區塊 (`next_replacement_block`)。
     3. 透過 VU C012 同時對 `LOG_vb_next` 與 `next_replacement_block` 注入 Program Fail (`fail_type=0`, `block_info_list_count=2`)，模擬當前區塊與備用區塊同時失效。
     4. 執行隨機寫入（Random Write），直到觸發寫入超時異常 (`G_TIMEOUT_ALL`)。
     5. 檢查韌體 Assert Number 是否為 `0x203`。
     6. 若 Assert 為 0x203，執行 `HW_RESET` (resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True) 重置設備。
     7. 重置後，透過 VU 40C1 獲取新的 LOG VB (`LOG_vb_new`) 並與重置前的 `LOG_vb` 比較。
   - 預期結果：
     - 寫入超時後，韌體必須觸發 Assert 0x203，確認設備處於非 Read-Only 的異常掛起狀態。
     - HW_RESET 後設備必須恢復 Unit Ready 狀態。
     - **關鍵驗證**：`LOG_vb_new` 必須不等於 `LOG_vb`。若兩者相同，代表韌體在重置後未能修復邏輯結構或陷入死循環，應拋出 `SIGHTING_RESPONSE_UNEXPECTED` 錯誤。這驗證了韌體在備用區塊耗盡且發生多重 Fail 時，能透過 Assert 機制保護硬體，並在重置後嘗試重建或切換邏輯區塊以恢復服務。