# Test Spec: UFS BEC Histogram Verification with Controlled Bit Flip on TLC LUN

## Verification Criterion (VC)
驗證 UFS 韌體在 TLC 區塊發生特定數量比特翻轉（Bit Flip）後，BEC (Bit Error Count) Histogram 的統計分佈是否符合預期：
1. **極低錯誤情境 (Flipbit <= 0x08)**：注入少量比特錯誤後，BEC Histogram 的 Bin 0, 1, 2 總計錯誤數應為 4，且 Bin 3-94 應為 0。
2. **高錯誤閾值情境 (BEC >= 320)**：若韌體檢測到極高錯誤數，Bin 80 的計數應為 4，且 Bin 2-79, 81-94 應為 0。
3. **常規錯誤分佈情境**：注入比特錯誤後，韌體透過 VU 0x409E 回報的錯誤位元數需對應至特定的 Histogram Bin。預期在該 Bin 及其相鄰的 Bin (Expect-2, Expect-1, Expect+1) 中，總計錯誤數應為 1，且其他 Bin 為 0。此測試旨在確認韌體能正確將物理層的比特錯誤映射至邏輯層的 BEC 統計直方圖中。

## Test Case (TC) Checkpoints

1. [Case01_Low_Flip_BEC_Histogram_Check]：
   - 動作：
     1. 透過 `issue_C08B` 禁用 Media Scan。
     2. 配置 LUN 0 為 Normal 類型，並寫入 4KB 資料至 LBA 0。
     3. 針對 LUN 0 的 LBA 0 對應之 TLC 區塊，透過 VU 0x4051 取得物理地址 (PBA)，並使用 VU 0x4060 讀取原始 Raw Data。
     4. 在 Raw Data 的特定位置注入 `flipbit` (範圍 0, 4, 8... 384) 個比特翻轉，並透過 VU 0xD060 擦除區塊後，使用 VU 0xC060 寫入修改後的 Payload。
     5. 寫入後立即讀取並透過 VU 0x409E 獲取 ECC 錯誤位元數 (`errorBitNumber1`)。
     6. 執行 VU 0x4026 重置 BEC Histogram 並確認所有 Die 的 Histogram 歸零。
     7. 執行 VU 0x4028 觸發 Media Scan 針對該 TLC 區塊進行掃描。
     8. 再次執行 VU 0x4026 讀取 BEC Histogram 數據。
     9. 解析 `tlc_histogram_die0` 的 Bin 0, 1, 2 數據，並檢查 Bin 3 至 94 是否為 0。
   - 預期結果：
     - 當 `flipbit <= 0x08` 時：
       - Bin 0, 1, 2 的計數總和必須等於 `0x04`。
       - Bin 3 至 94 的所有計數必須等於 `0x00`。
       - 這代表極少量的比特錯誤被正確歸類到低 BEC 區間。

2. [Case02_High_BEC_Threshold_Check]：
   - 動作：
     1. 重複 Case01 的寫入與比特翻轉步驟，但假設韌體內部邏輯判斷 `payload.bec.value >= 320` (此條件通常由韌體內部狀態或特定注入導致，腳本中作為分支條件)。
     2. 執行 VU 0x4026 重置 Histogram。
     3. 執行 VU 0x4028 觸發 Media Scan。
     4. 讀取 VU 0x4026 的 Histogram 數據。
     5. 解析 `tlc_histogram_die0` 的 Bin 80 數據，並檢查 Bin 2 至 79, 81 至 94 是否為 0。
   - 預期結果：
     - Bin 80 的計數必須等於 `0x04`。
     - Bin 2 至 79 以及 Bin 81 至 94 的所有計數必須等於 `0x00`。
     - 這代表高錯誤數被正確歸類至特定的高 BEC Bin (Bin 80)。

3. [Case03_Normal_Distribution_BEC_Histogram_Check]：
   - 動作：
     1. 重複 Case01 的寫入與比特翻轉步驟，且 `flipbit` 值導致韌體計算出的 BEC 小於 320 但大於 0x08。
     2. 執行 VU 0x4026 重置 Histogram。
     3. 執行 VU 0x4028 觸發 Media Scan。
     4. 讀取 VU 0x4026 的 Histogram 數據。
     5. 根據 VU 0x409E 回報的 `errorBitNumber1` 計算預期 Bin 索引：`expect_bin = error_bits_409E[0] // 4`。
     6. 計算相鄰 Bin 索引：`previous_previous_bin = expect_bin - 2`, `previous_bin = expect_bin - 1`, `next_bin = expect_bin + 1`。
     7. 讀取這四個 Bin (Expect, Prev-2, Prev-1, Next) 的計數並求和。
     8. 檢查其他 Bin (Bin 2 至 94，排除上述四個 Bin) 是否為 0。
   - 預期結果：
     - `expect_bin`, `previous_previous_bin`, `previous_bin`, `next_bin` 這四個 Bin 的計數總和必須等於 `0x01`。
     - 其他所有 Bin (Bin 2 至 94，排除上述四個 Bin) 的計數必須等於 `0x00`。
     - 這代表韌體將錯誤精確地分佈在與實際錯誤位元數相符的 Histogram 區間內，且沒有誤報其他區間。