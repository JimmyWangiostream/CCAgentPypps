# Test Spec: UFS Read Scan (RS) Configuration & UECC Detection Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Read Scan (RS) 機制在不同 MConfig 寄存器配置下的行為一致性與正確性：
1. **全局開關驗證**：確認透過 `set_Enable_Disable_Read_Scan` 關閉 RS 時，系統不會檢測或報告任何 UECC 錯誤；開啟時則正常運作。
2. **頁面類型選擇驗證**：確認 `PAGE_TYPE_SELECT` 寄存器控制 RS 掃描範圍。當 `BIT0` (Normal Page) 被禁用但 `BIT1/2` 啟用時，RS 應僅掃描特定頁面類型並檢測到注入的 UECC；當所有頁面類型選擇位 (`BIT0-2`) 均被禁用時，RS 應完全停止掃描。
3. **TLC 數據塊驗證**：確認 `TLC_data_block` 寄存器控制是否對 TLC 數據塊執行 RS。當 `BIT1` 被禁用時，RS 應忽略 TLC 數據塊中的錯誤。
4. **子區塊選擇驗證**：確認 `SUBBLOCK_SELECT` 寄存器控制 RS 掃描的具體子區塊偏移。當特定 `BIT` (0-3) 被禁用時，RS 應跳過對應的子區塊，導致注入在該子區塊內的 UECC 無法被檢測到（即 `error_detected_WLs` 中不包含 WL3）。
5. **溫度閾值驗證**：確認 `TEMP_LOW` 與 `TEMP_HIGH` 寄存器定義的溫度範圍是否影響 RS 觸發（本測試通過極端溫度值驗證寄存器寫入有效性，預期行為取決於韌體具體實現，通常用於驗證配置未導致異常）。

## Test Case (TC) Checkpoints
1. [Case01_Global_RS_Disable_Check]：
   - 動作：透過 `project_api.set_Enable_Disable_Read_Scan(enable=0)` 全局禁用 Read Scan，執行 HW_RESET 並重新配置 LUN。寫入 15 個 WL 的 TLC 資料，在 WL3 的特定 LBA 注入 UECC 錯誤，接著寫入剩餘 1 個 WL 資料。讀取 VU 40BF 狀態碼，並查詢 `get_gc_read_scan_released_scan_pageline()` 獲取檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 0（代表 RS 未進行或未完成掃描）；`error_detected_WLs` 列表長度必須為 0。這證明全局禁用 RS 後，硬體/韌體完全跳過了錯誤檢測流程。

2. [Case02_RS_Enable_Default_Check]：
   - 動作：恢復 MConfig 為備份狀態（默認啟用 RS），執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 1（代表 RS 掃描完成）；`error_detected_WLs` 列表長度必須大於 0，且必須包含數值 3。這證明在默認配置下，RS 能正確檢測到 WL3 中的 UECC 錯誤。

3. [Case03_Disable_PAGE_TYPE_SELECT_ALL_Check]：
   - 動作：修改 MConfig，將 `PAGE_TYPE_SELECT` 的 `BIT0`, `BIT1`, `BIT2` 全部清零（禁用所有頁面類型選擇），執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 0；`error_detected_WLs` 列表長度必須為 0。這證明當所有頁面類型的掃描選擇位都被禁用時，RS 機制不會對任何頁面類型執行掃描，從而漏檢 UECC。

4. [Case04_Disable_PAGE_TYPE_SELECT_Some_Check]：
   - 動作：修改 MConfig，保留 `BIT0` 啟用，但將 `BIT1` 和 `BIT2` 清零（禁用部分頁面類型選擇），執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 1；`error_detected_WLs` 列表長度必須大於 0，且必須包含數值 3。這證明即使部分頁面類型選擇位被禁用，只要仍有有效頁面類型被選擇，RS 仍能正常檢測到 WL3 中的 UECC。

5. [Case05_Disable_TLC_data_block_Check]：
   - 動作：修改 MConfig，將 `TLC_data_block` 的 `BIT1` 清零（禁用 TLC 數據塊掃描），執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 1；`error_detected_WLs` 列表長度必須大於 0，且必須包含數值 3。這證明 `TLC_data_block` 配置主要影響 TLC 特定邏輯，但在本測試情境下（注入在 WL3），RS 仍應能檢測到錯誤（需根據韌體具體實現確認，若 WL3 屬於被禁用的 TLC 數據塊範圍則預期為 0，但根據代碼邏輯 `diable_TLC_data_block` 通常指禁用特定 TLC 優化掃描，此處預期為檢測到錯誤以驗證其他掃描路徑正常，或根據具體韌體定義調整預期為未檢測到。*註：根據代碼邏輯，若此配置導致 WL3 不被掃描，則預期結果應為 status=0 或 error_detected_WLs 不含 3。但鑑於代碼中將此歸類為 "disable" 類，且其他 disable 類預期為未檢測到，此處需嚴格對應代碼邏輯：若 `TLC_data_block` 禁用導致 WL3 掃描被跳過，則預期為未檢測到。然而，代碼中將 `diable_TLC_data_block` 與 `disable_PAGE_TYPE_SELECT_SOME` 等歸為同一組 `if` 條件，暗示其預期行為應為「檢測到錯誤」，這可能意味著該配置僅禁用特定 TLC 優化而非基礎掃描，或者測試設計者預期在此配置下錯誤仍能被檢測。基於代碼結構 `if test in [...]` 包含此項，預期結果應為檢測到錯誤。*）：VU 40BF 狀態碼必須等於 1；`error_detected_WLs` 必須包含 3。

6. [Case06_Disable_SUBBLOCK_SELECT_0_Check]：
   - 動作：修改 MConfig，將 `SUBBLOCK_SELECT` 的 `BIT0` 清零，設置 `SB_offset=0`，執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 的 `SB_offset=0` 對應 LBA 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 1；`error_detected_WLs` 列表長度必須大於 0，但**不**包含數值 3。這證明當特定子區塊選擇位被禁用時，RS 會跳過該子區塊，導致注入在該子區塊內的 UECC 無法被檢測到。

7. [Case07_Disable_SUBBLOCK_SELECT_1_Check]：
   - 動作：修改 MConfig，將 `SUBBLOCK_SELECT` 的 `BIT1` 清零，設置 `SB_offset=1`，執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 的 `SB_offset=1` 對應 LBA 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 1；`error_detected_WLs` 列表長度必須大於 0，但**不**包含數值 3。這證明禁用 BIT1 後，RS 跳過對應子區塊，漏檢注入的 UECC。

8. [Case08_Disable_SUBBLOCK_SELECT_2_Check]：
   - 動作：修改 MConfig，將 `SUBBLOCK_SELECT` 的 `BIT2` 清零，設置 `SB_offset=2`，執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 的 `SB_offset=2` 對應 LBA 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 1；`error_detected_WLs` 列表長度必須大於 0，但**不**包含數值 3。這證明禁用 BIT2 後，RS 跳過對應子區塊，漏檢注入的 UECC。

9. [Case09_Disable_SUBBLOCK_SELECT_3_Check]：
   - 動作：修改 MConfig，將 `SUBBLOCK_SELECT` 的 `BIT3` 清零，設置 `SB_offset=3`，執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 的 `SB_offset=3` 對應 LBA 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
   - 預期結果：VU 40BF 狀態碼必須等於 1；`error_detected_WLs` 列表長度必須大於 0，但**不**包含數值 3。這證明禁用 BIT3 後，RS 跳過對應子區塊，漏檢注入的 UECC。

10. [Case10_Temp_Config_Verification_Check]：
    - 動作：分別設置極端溫度閾值（`set_TEMP_LOW`: 254/255 和 `set_TEMP_HIGHT`: 0/1），執行 HW_RESET。寫入 15 個 WL 資料，在 WL3 注入 UECC，寫入剩餘 1 個 WL。讀取 VU 40BF 狀態碼，並查詢檢測到的錯誤 WL 列表。
    - 預期結果：VU 40BF 狀態碼必須等於 1；`error_detected_WLs` 列表長度必須大於 0，且必須包含數值 3。這證明溫度閾值配置不會阻止 RS 掃描的執行，錯誤仍能被正常檢測。