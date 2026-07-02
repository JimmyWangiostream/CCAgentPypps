# Test Spec: UFS ERS (Error Recovery Statistics) Persistence & PSA Flow Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 PSA (Pre-Soldering Area) 初始化流程及異常掉電情境下，Error Recovery Statistics (ERS) 中 `DEFAULT_READ_PASS_COUNT` 的硬體計數器行為：
1. **PSA 寫入階段**：確認在 LUN 0 (PSA) 執行 `PRE_SOLDERING` 狀態設定及全容量 Write10 後，韌體內部讀取計數器會因 PSA 資料寫入而增加。
2. **掉電恢復一致性**：確認在 PSA 流程完成 (`LOADING_COMPLETE`) 並執行 Read10 後，再次執行 HW_RESET 掉電重啟，韌體恢復後讀取的 `DEFAULT_READ_PASS_COUNT` 必須與掉電前完全一致，證明該計數器儲存於非揮發性記憶體或韌體持久化區塊中，且未因 PSA 流程中的 Unmap/Write 操作產生誤差或重置。
3. **系統狀態檢查**：確認掉電恢復後，Bad Block Information (VU 405E)、NAND 溫度 (VU 4021)、Read Count Threshold (VU 40CA) 及 Media Scan Parameters (VU 40CF) 等 Vendor Command 可正常回應，確保韌體處於穩定可操作狀態。

## Test Case (TC) Checkpoints

1. [Case01_PSA_Write_ERS_Increment_Check]：
   - 動作：
     1. 配置 LUN 0 為 PSA LUN，LUN 1 為 Normal LUN，並停止 Refresh 機制 (`Issue C088 Stop`)。
     2. 執行第一次 `Issue 40BA` 讀取 ERS，提取 `ERSIndex.DEFAULT_READ_PASS_COUNT` (索引 65) 的計數值作為基準 `read_count_1st`。
     3. 執行 HW_RESET 掉電重啟。
     4. 重新啟用 Read Count 統計 (`Issue D019 Enable`)。
     5. 將 LUN 0 設定為 `PRE_SOLDERING` 狀態，並對 LUN 0 執行全容量 (Max PSA Data Size) 的 Write10 操作。
     6. 執行第二次 `Issue 40BA` 讀取 ERS，獲取 `read_count_2nd`。
   - 預期結果：`read_count_2nd` 的各 Plane/CE 計數值應大於或等於 `read_count_1st`，反映 PSA 寫入操作產生的內部讀取/校驗行為；韌體未崩潰，VU 40BA 回應正常。

2. [Case02_PSA_Completion_ERS_Stability_Check]：
   - 動作：
     1. 將 LUN 0 的 PSA State 寫入 `LOADING_COMPLETE`。
     2. 對 LUN 0 執行全容量 (Max PSA Data Size) 的 Read10 操作。
     3. 執行第三次 `Issue 40BA` 讀取 ERS，獲取 `read_count_3rd`。
   - 預期結果：`read_count_3rd` 記錄了 PSA 寫入及後續讀取後的累計讀取計數；韌體狀態穩定，無錯誤注入或異常中斷。

3. [Case03_PowerCycle_ERS_Persistence_Check]：
   - 動作：
     1. 執行 HW_RESET 掉電重啟 (`powerdown = True`)。
     2. 重新啟用 Read Count 統計 (`Issue D019 Enable`)。
     3. 執行第四次 `Issue 40BA` 讀取 ERS，獲取 `read_count_4th`。
     4. 比對 `read_count_4th` 與 `read_count_3rd` 的數值。
   - 預期結果：`read_count_4th` 的每一個 Plane/CE 計數值必須嚴格等於 `read_count_3rd` 對應的值。若發現 `read_count_4th` 中有任何值小於 `read_count_3rd`，則判定為測試失敗 (`SIGHTING_FAIL_DATA_COMPARE_FAIL`)。此結果驗證了 `DEFAULT_READ_PASS_COUNT` 在掉電後能正確持久化恢復，且 PSA 流程未導致計數器意外重置或損壞。

4. [Case04_System_Health_Post_PSA_Check]：
   - 動作：
     1. 在 Case03 掉電恢復後，依次執行以下 Vendor Commands：
        - `Issue 405E` 獲取 Bad Block Information。
        - `Issue 4021` 獲取 NAND 溫度。
        - `Issue 40CA` 獲取 Read Count Threshold Table。
        - `Issue 40CF` 獲取 Media Scan Parameters。
     2. 最後執行 `Issue C088 Start Refresh` 啟動 Refresh 機制。
   - 預期結果：所有 VU Commands 必須成功返回有效 Payload，無 Timeout 或 Sense Key 錯誤；確認韌體在 PSA 流程及掉電恢復後，Bad Block 管理、溫度監控及 Media Scan 參數均處於正常運作狀態。