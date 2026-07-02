# Test Spec: UFS FTL Status Counter & SPOR Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在多種操作情境下 FTL 狀態計數器（透過 Vendor Command 0x40C3 讀取）的準確性與一致性，以及異常掉電（SPOR）後的系統恢復機制：
1. **基礎計數器驗證**：確認 Host Write/Read、GC、Refresh、Media Scan、Read Disturb、XTEMP 溫度變化、Hibernate 等事件觸發時，對應的 FTL 計數器（如 `hostSLCDataSize_NORMAL`, `RefreshCnt`, `counterDeltaT1` 等）能精確遞增或滿足特定條件。
2. **SPOR 與 PTE 恢復驗證**：確認在 PTE (Pointer to Index) 區塊注入 UECC 錯誤並執行無 SSU 的 HW_RESET 後，韌體能正確識別 Power Loss Flag (BIT6)，並觸發 PTE 重建流程，導致 `oneShotTableDefragCount` 或 `SPOR_recovery_count` 等相關計數器正確更新，且 PTE 狀態恢復正常。
3. **APL (Active Page List) 狀態驗證**：確認在 SPOR 情境下，APL 中的 `last_written_page`、`apl_status_of_host_vb` 等欄位能正確反映寫入進度或錯誤狀態（如 0xFFFFFFFF 表示未完成/錯誤）。

## Test Case (TC) Checkpoints

1. [TC01_Basic_FTL_Counter_Increment_Check]:
   - 動作：配置 LUN 為 SLC (LUN 0) 與 TLC (LUN 1)，分別執行特定大小的 Write/Read 操作（如 25MB, 4KB），並觸發 Unmap、Format、Hibernate 進入/退出、Write Booster 開關切換。每次操作前後透過 Vendor Command 0x40C3 讀取對應欄位（如 `write_data_volume_25MB`, `discardCount`, `idleTimeAndHybernate`, `HOST_WRITE_COMMAND_COUNT_LOWER` 等）。
   - 預期結果：所有觸發的 FTL 事件必須導致對應的 0x40C3 計數器欄位數值精確遞增（例如 `expected_delta=1` 或根據寫入大小計算的具體數值），且 `HOST_WRITE_COMMAND_COUNT_UPPER` 與 `HOST_READ_COMMAND_COUNT_UPPER` 必須保持為 0。

2. [TC02_XTEMP_Temperature_Transition_Counter_Check]:
   - 動作：透過 Vendor Command 設定所有 VB 的 EC 值以啟用 XTEMP 機制，執行 HW_RESET。接著透過 VU 0xD08A 將 NAND 溫度設定為 `XTEMP_Refresh_T1 - 1`（Cold Risky）並等待 `XTEMP_TIME_DETECTION_VALUE` 時間，再設定為安全溫度；重複類似步驟測試 `XTEMP_Refresh_T2` 相關的 Hot Risky 狀態。最後讀取 `counterDeltaT1` 與 `counterDeltaT2` 計數器。
   - 預期結果：當溫度跨越 `XTEMP_Refresh_T1` 或 `XTEMP_Refresh_T2` 閾值並停留足夠時間後，對應的 `counterDeltaT1` 或 `counterDeltaT2` 計數器必須遞增 1，證明韌體正確統計了溫度狀態轉換次數。

3. [TC03_SPOR_PTE_UECC_Recovery_and_Count_Check]:
   - 動作：
     1. 寫入資料至 TLC LUN 並取得 PTE 的 VB 號碼與 FEP。
     2. 透過 `flipbit_on_PTE_smart` 在 PTE 的特定 Page 注入 100 個比特翻轉（模擬 UECC 錯誤）。
     3. 執行隨機寫入並觸發 SPOR（透過 DCMD7 或硬體重啟模擬掉電），隨後執行無 SSU 的 HW_RESET。
     4. 讀取 PTE 狀態，並透過 Vendor Command 0x40D1 讀取 System Init Timestamp 的 payload 第 88-92 位元，檢查 BIT6 (Power Loss Flag) 是否被設定。
     5. 讀取 0x40C3 中的 `oneShotTableDefragCount` 或 `SPOR_recovery_count`。
   - 預期結果：
     - 0x40D1 回傳的 payload 中 BIT6 必須為 1，代表韌體偵測到異常掉電。
     - `oneShotTableDefragCount` 或 `SPOR_recovery_count` 必須遞增 1，代表韌體觸發了 PTE 重建或恢復流程。
     - PTE 的 VB 號碼在恢復後應保持邏輯一致或按預期更新，且無未修復的 UECC 殘留導致系統崩潰。

4. [TC04_APL_Status_Verification_During_SPOR]:
   - 動作：
     1. 寫入資料至特定 LUN，取得 PBA 並透過 VU 0x40C3 讀取 `open_data_vb` 或 `table_vb` 的 APL 狀態。
     2. 執行 SPOR 流程（寫入中斷電）。
     3. 恢復後，透過 VU 0x40C3 讀取 `open_data_vb` 中的 `apl_status_list`。
     4. 檢查 `last_written_page`、`apl_status_of_host_vb`、`apl_status_of_first_empty_page` 欄位。
   - 預期結果：
     - 若寫入未完成，`last_written_page` 不應為 0xFFFFFFFF（除非是特定錯誤狀態），且 `apl_status_of_host_vb` 應反映正確的寫入狀態（如 0 表示正常，或特定錯誤碼）。
     - 對於 PTE 類型的 VB，`apl_status_of_host_vb` 在 SPOR 後可能顯示 0xFFFFFFFF 表示該頁寫入失敗或未完成，需與韌體恢復邏輯一致。

5. [TC05_Read_Disturb_and_Media_Scan_Trigger_Check]:
   - 動作：
     1. 設定 Read Disturb 閾值，對特定 VB 執行大量重複讀取操作。
     2. 觸發 Media Scan 並監控其進度（透過 VU 0x40CF）。
     3. 讀取 0x40C3 中的 `Read_Disturb_Trigger_Num`、`Media_Scan_finished_Instance_Num`、`mediaScanFinishScanVB` 等計數器。
   - 預期結果：
     - 當讀取次數超過閾值時，`Read_Disturb_Trigger_Num` 必須遞增。
     - Media Scan 完成特定 VB 掃描後，`mediaScanFinishScanVB` 或相關計數器應正確反映掃描進度或完成次數。