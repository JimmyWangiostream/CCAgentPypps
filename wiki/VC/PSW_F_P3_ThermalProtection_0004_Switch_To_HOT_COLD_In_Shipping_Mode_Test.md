# Test Spec: Thermal Protection VU (D0F1/D0F3) Stuck Recovery & Data Integrity Test

## Verification Criterion (VC)
驗證 UFS 裝置在熱保護（Thermal Protection）機制觸發時的韌體行為與資料完整性：
1. **模式切換與閾值設定**：確認透過 Vendor Command (VC) D0F3 切換至 HOT_ONLY 及 HOT_COLD 模式，並透過 VC D0F1 正確寫入高低溫保護閾值（需扣除 80°C 偏移量）。
2. **熱保護觸發與韌體掛起**：在設定閾值後，當寫入 4KB 資料時，若觸發熱保護條件，韌體應進入 Assert 狀態導致寫入命令超時（Timeout），且必須記錄非零的 Assert Code 以證明熱保護機制已正確介入並阻止資料寫入。
3. **硬體重啟恢復與資料隔離**：執行 HW_RESET 後，驗證系統恢復正常，且透過讀取寫入位置之後的 LBA 區塊，確認其 CRC 值為預期的 0x0（即未寫入狀態或初始狀態），證明觸發熱保護時的寫入操作被完全中止，未造成資料污染或半寫入狀態。

## Test Case (TC) Checkpoints
1. [Case01_HOT_ONLY_Threshold_Set_Check]：
   - 動作：
     1. 執行 FormatUnit 於 UFS_DEVICE LUN。
     2. 發送 VC D0F3 將熱保護類型設為 `TP_ENABLE` 且模式為 `TP_HARD_HOT_ONLY`。
     3. 發送 VC D0FC 設定 Shipping Mode。
     4. 發送 VC D0F3 將熱保護模式切換為 `TP_HARD_HOT_COLD`。
     5. 讀取 `threshold_for_high_thermal_stuck_area` 與 `threshold_for_low_thermal_stuck_area`，計算並透過 VC D0F1 寫入閾值：Low Threshold = `180 - 80` (100°C)，High Threshold = `StuckThreshold.high - 80`。
     6. 嘗試對 Normal LUN (LUN 0) 的 LBA 0 寫入 4KB 資料。
   - 預期結果：
     - 寫入命令應因觸發熱保護而超時（Timeout）。
     - 韌體 Assert Code 必須為非零值（`assert_code != 0x0`），確認熱保護機制已觸發並記錄錯誤。

2. [Case02_HOT_COLD_Threshold_Set_Check]：
   - 動作：
     1. 重複上述模式切換流程（D0F3 HOT_ONLY -> D0FC -> D0F3 HOT_COLD）。
     2. 透過 VC D0F1 寫入閾值：Low Threshold = `StuckThreshold.low - 80`，High Threshold = `80 - 80` (0°C)。
     3. 嘗試對 Normal LUN (LUN 0) 的 LBA 0 寫入 4KB 資料。
   - 預期結果：
     - 寫入命令應因觸發熱保護而超時（Timeout）。
     - 韌體 Assert Code 必須為非零值（`assert_code != 0x0`），確認在不同閾值設定下熱保護機制仍能有效觸發。

3. [Case03_HW_RESET_Recovery_Data_Integrity_Check]：
   - 動作：
     1. 在寫入超時並確認 Assert Code 後，執行 `api.init_tester_to_unit_ready` 進行 HW_RESET（powerdown=False）。
     2. 裝置恢復後，發送 Read10 命令讀取 LBA `TestLBA + TestSize`（即緊接在嘗試寫入位置之後的 4KB 區塊）。
     3. 設定讀取命令的 SW CRC 檢查值為 `0x0`。
   - 預期結果：
     - 讀取命令必須成功完成（無超時或錯誤）。
     - 讀取回來的資料 CRC 必須與預期值 `0x0` 匹配，證明之前的寫入操作因熱保護觸發而被完全中止，未對儲存媒體造成任何資料寫入或損壞。