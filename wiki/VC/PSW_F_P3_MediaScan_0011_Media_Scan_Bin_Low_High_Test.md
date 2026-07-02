# Test Spec: UFS Media Scan Bin Threshold & Refresh Queue Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體 Media Scan 機制中，基於 BFEA (Block Failure Early Assessment) Bin 數值與配置參數 (BIN_LOW/BIN_HIGH) 的區塊掃描決策邏輯：
1. **Case 01 (Skip Scan - Low Bin)**：當 TLC VB 的 BFEA Bin 設定為 9，且配置 `BIN_LOW=10` 時，韌體應識別該區塊為「低風險/新區塊」，在 Media Scan 執行期間**跳過**該 VB 的掃描，且該 VB 不得出現在 `scanned_blocks` 列表中。
2. **Case 02 (Skip Scan - High Bin/Used Pool)**：當 TLC VB 的 BFEA Bin 設定為 9，且配置 `BIN_LOW=10` 時，若該 VB 屬於 MLC Used Pool，韌體同樣應**跳過**掃描，確保 Used Pool 中的低 Bin 區塊不被誤判為高風險。
3. **Case 03 (Booking RefreshQ - Out of Range)**：當 TLC VB 的 BFEA Bin 設定為 11，且配置 `BIN_LOW=8, BIN_HIGH=10` 時，該 VB 超出掃描範圍。此時若透過 VUC 0x088 停止即時刷新執行，韌體應將該 VB **排隊 (Booking)** 至 Refresh Queue，並透過 VUC 0x0C5 驗證 `BookingQueueVB` 中確實包含該 VB。
4. **Case 04 (Normal Scan - In Range)**：當 TLC VB 的 BFEA Bin 設定為 9，且配置 `BIN_LOW=8, BIN_HIGH=10` 時，該 VB 落在掃描範圍內。Media Scan 執行後，該 VB 必須被**正常掃描**，並出現在 `scanned_blocks` 列表中。

## Test Case (TC) Checkpoints

1. **[Case01_SkipScan_LowBin_TLC]**：
   - 動作：
     1. 透過 VUC 0x08B 禁用 Media Scan。
     2. 配置 LUN 並對 LUN 0 順序寫入 2000 Pagelines 的 TLC 資料。
     3. 透過 VUC 0x4051 取得最後寫入 Page 的物理地址 (PCA)，解析出對應的 Logical VB Number (`cur_l2_vb`)，並確認其模式為 Current L2 MLC。
     4. 透過 VUC 0x085 設定 `BIN_LOW=10`。
     5. 針對 `cur_l2_vb` 的所有 CE，透過 VUC 0x40B0 (Set BFEA Table, Op=2) 將該 VB 的 BFEA Bin 設定為 **9**。
     6. 透過 VUC 0x40B0 (Get BFEA Table, Op=3) 讀取並驗證 Byte[0-3] 輸出值確實為 9。
     7. 透過 VUC 0x08B 啟用 Media Scan。
     8. 透過 VUC 0x085 設定 `last_scan_spend_time=0x1000000` 觸發掃描。
     9. 輪詢 VUC 0x0CF 獲取 Media Scan 狀態，直到 `scan_group` 變化或掃描完成。
     10. 檢查 VUC 0x0CF Payload 中的 `scanned_blocks` 列表。
   - 預期結果：
     - `cur_l2_vb` **不得**出現在 `scanned_blocks` 列表中。
     - 若 `cur_l2_vb` 出現在列表中，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 這證明當 BFEA Bin (9) < BIN_LOW (10) 時，韌體正確跳過掃描。

2. **[Case02_SkipScan_LowBin_UsedPool]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 對 LUN 0 寫入一個 TLC VB 大小的資料。
     3. 透過 VUC 0x4051 取得寫入區塊的 PCA，解析出 `used_vb`，並確認其 VB Group 為 `USED_BLK_POOL_MLC`。
     4. 設定 `BIN_LOW=10`。
     5. 針對 `used_vb` 的所有 CE，透過 VUC 0x40B0 (Set) 將 BFEA Bin 設定為 **9**。
     6. 透過 VUC 0x40B0 (Get) 驗證 Bin 值為 9。
     7. 啟用 Media Scan。
     8. 觸發 Media Scan 並等待完成。
     9. 檢查 VUC 0x0CF Payload 中的 `scanned_blocks` 列表。
   - 預期結果：
     - `used_vb` **不得**出現在 `scanned_blocks` 列表中。
     - 這證明即使區塊位於 Used Pool，只要 BFEA Bin 低於 BIN_LOW，仍應被跳過掃描。

3. **[Case03_BookingRefreshQ_HighBin]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 對 LUN 0 寫入一個 TLC VB 大小的資料，取得 `used_vb` 並確認其為 `USED_BLK_POOL_MLC`。
     3. 設定 `BIN_LOW=8`, `BIN_HIGH=10`。
     4. 針對 `used_vb` 的所有 CE，透過 VUC 0x40B0 (Set) 將 BFEA Bin 設定為 **11**。
     5. 透過 VUC 0x40B0 (Get) 驗證 Bin 值為 11。
     6. 透過 VUC 0x088 發送 `StopRefreshRefreshCanStillBeEnqueue` 參數，停止即時刷新但允許排隊。
     7. 啟用 Media Scan。
     8. 觸發 Media Scan 並等待 5 秒。
     9. 透過 VUC 0x0C5 讀取 `BookingQueue`。
   - 預期結果：
     - `BookingQueue` 中的 `LogicalVBNumberInBookingQueue` 必須大於 0。
     - `BookingQueueVB` 列表中必須包含 `used_vb`。
     - 若未包含或佇列為空，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 這證明當 BFEA Bin (11) > BIN_HIGH (10) 時，韌體將該區塊加入 Refresh Queue 而非直接掃描或忽略。

4. **[Case04_NormalScan_InRange]**：
   - 動作：
     1. 禁用 Media Scan。
     2. 對 LUN 0 寫入一個 TLC VB 大小的資料，取得 `used_vb` 並確認其為 `USED_BLK_POOL_MLC`。
     3. 設定 `BIN_LOW=8`, `BIN_HIGH=10`。
     4. 針對 `used_vb` 的所有 CE，透過 VUC 0x40B0 (Set) 將 BFEA Bin 設定為 **9**。
     5. 透過 VUC 0x40B0 (Get) 驗證 Bin 值為 9。
     6. 啟用 Media Scan。
     7. 觸發 Media Scan 並等待 5 秒。
     8. 透過 VUC 0x0CF 讀取 Media Scan 狀態，獲取 `scanned_blocks` 列表。
   - 預期結果：
     - `used_vb` **必須**出現在 `scanned_blocks` 列表中。
     - 若未出現，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 這證明當 BFEA Bin (9) 介於 BIN_LOW (8) 和 BIN_HIGH (10) 之間時，韌體執行正常的 Media Scan。