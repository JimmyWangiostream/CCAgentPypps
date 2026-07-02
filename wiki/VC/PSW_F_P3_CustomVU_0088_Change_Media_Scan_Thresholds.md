# Test Spec: UFS Media Scan Threshold Validation (BEC, DiffEC, ArcOffset, CenterEC, XTemp)

## Verification Criterion (VC)
驗證韌體 Media Scan 機制中，針對 SLC 模式 EM1 LUN 的硬體錯誤檢測閾值（Thresholds）配置是否正確生效：
1. **BEC_VALLEY_TH 驗證**：確認當注入 100 個錯誤位元（BEC）時，若閾值設定低於實際 BEC，Media Scan 狀態應為 `UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC` (15)；若閾值大於等於實際 BEC，狀態應為 `UNFOLD_FOR_GOOD_BEC` (13)。
2. **VALLEY_DIFFEC_TH 驗證**：確認當注入 150 個錯誤位元導致 4KB 間差異（DiffEC）時，若閾值設定小於等於實際 DiffEC，狀態應為 `FOLD_FOR_DIFFEC` (7)；若閾值大於實際 DiffEC，狀態應為 `UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC` (15)。
3. **VALLEY_OFST_TH (ArcOffset) 驗證**：確認當注入 150 個錯誤位元產生 ArcOffset 時，若閾值設定小於等於實際 ArcOffset，狀態應為 `FOLD_FOR_DIFFEC` (7)；若閾值大於實際 ArcOffset，狀態應為 `UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC` (15)。
4. **VALLEY_CENTER_EC_TH 驗證**：確認當注入 150 個錯誤位元產生 CenterEC 時，若閾值設定小於等於實際 CenterEC，狀態應為 `FOLD_FOR_DIFFEC` (7)；若閾值大於實際 CenterEC，狀態應為 `UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC` (15)。
5. **XTEMP_DELTA_TH 驗證**：確認在 NAND 溫度設定為 20°C (Controller 85°C) 且注入 150 個錯誤位元的情境下，若 XTemp Delta 閾值設為 0xFF (寬鬆)，狀態應為 `FOLD_FOR_DIFFEC` (7)；若設為 0x01 (嚴格)，狀態應為 `FOLD_FOR_TEMP` (8)。

## Test Case (TC) Checkpoints

1. **[TC01_BEC_Valley_Threshold_Check]**：
   - 動作：配置 LUN 0 (Normal) 與 LUN 1 (EM1)，寫入各 1 WL 大小的 SLC/TLC 資料。針對 LUN 1 (EM1) 的 LBA 0 執行 `flipbit_on_SLC` 注入 100 個錯誤位元。透過 VU 0x4051 取得物理地址，設定 VU 0x4028 參數為 SLC 模式、Partial Block、EM1 VB。執行 VU 0x4028 獲取黃金 BEC 值。隨後迴圈測試 BEC 閾值為 `[Golden-1, Golden, Golden+1]`，透過 VU 0xD08E 設定 `w14_bec_valley_th_slc`，並再次執行 VU 0x4028 檢查 `media_scan_status`。
   - 預期結果：當 `payload.bec.value > bec_th` 時，`payload.media_scan_status.value` 必須等於 `15` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC`)；當 `payload.bec.value <= bec_th` 時，`payload.media_scan_status.value` 必須等於 `13` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_FOR_GOOD_BEC`)。

2. **[TC02_DiffEC_Threshold_Check]**：
   - 動作：重置 LUN 配置並寫入資料。針對 LUN 1 (EM1) 的 LBA 0 的 4 個 4KB 區塊分別注入 150 個錯誤位元。執行 VU 0x4028 獲取黃金 DiffEC 值。迴圈測試 DiffEC 閾值為 `[Golden-1, Golden, Golden+1]`，透過 VU 0xD08E 設定 `w18_valley_diffec_th_slc`，並再次執行 VU 0x4028 檢查 `media_scan_status`。
   - 預期結果：當 `payload.diff_ec.value >= diff_ec_th` 時，`payload.media_scan_status.value` 必須等於 `7` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_DIFFEC`)；當 `payload.diff_ec.value < diff_ec_th` 時，`payload.media_scan_status.value` 必須等於 `15` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC`)。

3. **[TC03_ArcOffset_Threshold_Check]**：
   - 動作：重置 LUN 配置並寫入資料。針對 LUN 1 (EM1) 的 LBA 0 的 4 個 4KB 區塊分別注入 150 個錯誤位元。執行 VU 0x4028 獲取黃金 ArcOffset 值（取絕對值）。迴圈測試 ArcOffset 閾值為 `[Golden-1, Golden, Golden+1]`，透過 VU 0xD08E 設定 `b20_valley_ofs_th_slc`，並再次執行 VU 0x4028 檢查 `media_scan_status`。
   - 預期結果：當 `abs(arc_offset) > arc_offset_th` 時，`payload.media_scan_status.value` 必須等於 `7` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_DIFFEC`)；當 `abs(arc_offset) <= arc_offset_th` 時，`payload.media_scan_status.value` 必須等於 `15` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC`)。

4. **[TC04_CenterEC_Threshold_Check]**：
   - 動作：重置 LUN 配置並寫入資料。針對 LUN 1 (EM1) 的 LBA 0 的 4 個 4KB 區塊分別注入 150 個錯誤位元。執行 VU 0x4028 獲取黃金 CenterEC 值。迴圈測試 CenterEC 閾值為 `[Golden-1, Golden, Golden+1]`，透過 VU 0xD08E 設定 `w16_valley_center_ecth_slc`，並再次執行 VU 0x4028 檢查 `media_scan_status`。
   - 預期結果：當 `payload.center_ec.value > center_ec_th` 時，`payload.media_scan_status.value` 必須等於 `7` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_DIFFEC`)；當 `payload.center_ec.value <= center_ec_th` 時，`payload.media_scan_status.value` 必須等於 `15` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC`)。

5. **[TC05_XTemp_Delta_Threshold_Check]**：
   - 動作：重置 LUN 配置並寫入資料。針對 LUN 1 (EM1) 的 LBA 0 的 4 個 4KB 區塊分別注入 150 個錯誤位元。透過 VU 0xD08A 設定 NAND 溫度為 20°C，Controller 溫度為 85°C，並透過 VU 0x4021 驗證溫度設定正確。執行 VU 0x4028 獲取基準狀態。隨後測試兩個極端 XTemp Delta 閾值：`0x01` 與 `0xFF`，透過 VU 0xD08E 設定 `b21_xtemp_th_delta_slc`，並再次執行 VU 0x4028 檢查 `media_scan_status`。
   - 預期結果：當 `temp_th == 0xFF` 時，`payload.media_scan_status.value` 必須等於 `7` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_DIFFEC`)；當 `temp_th == 0x01` 時，`payload.media_scan_status.value` 必須等於 `8` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_TEMP`)。