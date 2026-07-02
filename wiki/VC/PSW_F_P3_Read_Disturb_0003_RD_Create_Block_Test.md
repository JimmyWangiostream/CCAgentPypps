# Test Spec: UFS FTL EC/RC Threshold Configuration & Persistence Verification

## Verification Criterion (VC)
驗證韌體在動態調整 SLC (EM1) 與 TLC (Normal) LUN 的 Virtual Block (VB) Erase Count (EC) 閾值後，Read Count (RC) 閾值 (RC_TH) 的計算邏輯是否正確，以及透過 Vendor Command (C087, 408C, 40CA) 讀取的硬體狀態是否與預期配置一致。具體驗證以下三個層面：
1. **動態閾值設定**：確認透過 `set_vb_erase_cnt_by_list` 強制修改 VB 的 EC 值後，系統能根據 mConfig 中的 `*_EC_*` 欄位正確計算並應用對應的 `RC_TH`。
2. **硬體狀態一致性**：確認透過 `issue_40CA` 讀取的內部 RC 閾值表，以及透過 `issue_408C` 讀取的 EC_RC 閾值表（針對 SLC/TLC 的 Open/Close 區塊類型），其 `EraseCountThreshold` 與 `ReadCountThreshold` 數值必須嚴格等於由 mConfig 計算出的預期值。
3. **初始狀態檢查**：確認新建立的 VB 在寫入完成後，其當前 RC 值必須為 0，且 RC_TH 必須與配置的閾值完全匹配。
4. **持久化與恢復**：確認在執行 HW_RESET (Power Down) 並等待 Bkops Idle 後，系統能正確恢復並維持上述配置狀態（透過最後一輪循環的檢查間接驗證）。

## Test Case (TC) Checkpoints
1. [EC_RC_Threshold_Configuration_Check]:
   - 動作：
     1. 初始化測試環境，配置 LUN 0 為 Normal (TLC)，LUN 1 為 EM1 (SLC)，其餘為 Dummy。
     2. 透過 `set_vb_erase_cnt_by_list` 將所有 Free Block Queue (EM1 或 TLC) 中的 VB 的 Erase Count (EC) 強制設為特定值 `set_value`。該值由 mConfig 中的 `*_EC_{group}` 欄位決定（若 group=4 則為上一組值+1）。
     3. 執行 `issue_C087` 將 Current L2 中的 VB 加入 Booking Queue 並觸發 Refresh 操作，確保硬體狀態同步。
     4. 針對對應 LUN 執行 Sequential Write (大小為 VB Size 的 1.5 倍)，產生新的 VB。
     5. 透過 `issue_4051` 獲取寫入起始與結束 LBA 對應的 Physical Address (PCA)，提取 Virtual Block Number (VB)。
     6. 透過 `issue_40CA` 讀取該 VB 的當前 Read Count (RC) 與 Read Count Threshold (RC_TH)。
     7. 透過 `issue_408C` 讀取對應區塊類型 (SLC/TLC Open/Close) 的 EC_RC 閾值表 (ReadThresholdSet)。
     8. 驗證邏輯：
        - 檢查該 VB 的當前 RC 是否等於 0。
        - 檢查該 VB 的 RC_TH 是否等於 `mConfig` 中對應欄位 `*_EC_RC_TH_{FP}B{group}` 的值乘以 1000。
        - 檢查 `issue_408C` 返回的 `ReadThresholdSet` 長度是否為 5。
        - 檢查 `ReadThresholdSet[group]` 的 `EraseCountThreshold` 是否等於 `mConfig` 中 `*_EC_{group}` 的值乘以 100。
        - 檢查 `ReadThresholdSet[group]` 的 `ReadCountThreshold` 是否等於 `mConfig` 中 `*_EC_RC_TH_{FP}B{group}` 的值乘以 1000。
   - 預期結果：
     - 所有新建立 VB 的 RC 必須為 0。
     - 所有讀取的 RC_TH 必須精確等於計算出的預期值 (EC * 1000 或 mConfig 指定值)。
     - `issue_408C` 返回的閾值表中，第 `group` 項的 EraseCountThreshold 與 ReadCountThreshold 必須與 mConfig 配置完全一致，否則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [POR_Persistence_and_State_Restoration_Check]:
   - 動作：
     1. 在完成上述所有 EC/RC 閾值配置與驗證後，執行 `api.init_tester_to_unit_ready` 觸發 HW_RESET (Power Down)。
     2. 等待系統重新上電並進入 Unit Ready 狀態，隨後執行 `polling_bkops_idle` 確保後台操作完成。
     3. 在下一個循環迭代中（或測試結束前），再次讀取 VB 狀態並驗證 EC 與 RC 閾值是否保持穩定，確認韌體在掉電重啟後未丟失關鍵的閾值配置或導致狀態異常。
   - 預期結果：
     - 系統能成功從 HW_RESET 恢復並進入 Unit Ready 狀態。
     - Bkops 操作完成後，系統狀態穩定，無異常錯誤碼。
     - 驗證邏輯確保在電源循環後，相關的閾值配置機制仍處於可驗證的有效狀態（透過循環結構中的連續檢查間接確保韌體恢復邏輯正確處理了持久化數據）。