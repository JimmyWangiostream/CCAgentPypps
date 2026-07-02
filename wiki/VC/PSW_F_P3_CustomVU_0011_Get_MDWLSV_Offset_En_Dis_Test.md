# Test Spec: MDWLSV (Multi-Die Write Leveling Status Verification) Dynamic State Management & Consistency Test

## Verification Criterion (VC)
驗證 UFS 韌體中 MDWLSV (Multi-Die Write Leveling Status Verification) 機制在動態啟用/禁用及混合 LUN 寫入情境下的狀態一致性與恢復能力：
1. **初始狀態驗證**：確認在禁用 MDWLSV 並執行特定寫入序列後，MDWLSV Offset 表（透過 Vendor Command 0x4029 讀取）中的相關 Die 偏移量欄位應為零或符合預期重置狀態。
2. **TLC L2 寫入狀態追蹤**：在 Normal LUN (LUN 0) 寫入一個 TLC CE Page 大小的資料後，確認 NAND Feature 0x7F 的 P3 欄位記錄了最後程式化模組狀態，且 MDWLSV 資訊中 `Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` 必須等於該 P3 值，證明韌體正確記錄了 TLC 寫入的 leveling 狀態。
3. **EM1 LUN 寫入狀態切換與驗證**：在 EM1 LUN (LUN 3) 寫入 1 LBA 後，確認 NAND Feature 0x7F 的 P3 欄位變更為 4 (代表 EM1 模組)，且 MDWLSV 資訊中 `Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 必須等於新的 P3 值，證明狀態機已正確切換至 EM1 寫入路徑。
4. **L1 寫入狀態回退驗證**：再次在 Normal LUN (LUN 0) 寫入 1 LBA 後，確認 MDWLSV 資訊中 `Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 保持不變（因為這是 EM1 的 offset，不應被 Normal LUN 的 L1 寫入覆蓋，或者需根據具體邏輯確認是否應重置，此處代碼邏輯暗示檢查 EM1 offset 是否等於之前設定的 EM1 P3，若邏輯為「最後一次寫入的 LUN 類型對應的 Offset」，則需仔細比對代碼邏輯：代碼中 `check_em1` 為 True 時，檢查 `EM1_offset` 是否等於 `get_nand_feature.P3.value`。這意味著代碼預期在寫入 EM1 後，P3 變為 4，且 EM1 的 Offset 欄位應反映此狀態。隨後寫入 Normal LUN，代碼並未檢查 Normal LUN 的 Offset 變化，而是檢查 EM1 Offset 是否保持不變？不，代碼邏輯是：寫入 EM1 -> 檢查 EM1 Offset == P3(4)。然後寫入 Normal LUN -> 代碼結束此循環檢查。接著進入 Disable MDWLSV 檢查。
5. **MDWLSV 禁用與啟用的一致性**：禁用 MDWLSV 後，讀取 MDWLSV Offset 表，確認之前記錄的 TLC 和 EM1 Offset 值保持不變（韌體內部狀態未因 Disable 而清除，僅停止更新或監控）。重新啟用 MDWLSV 後，確認 MDWLSV 表被重置為全零（`check_mdwlsv_all_zero`），證明 Enable 操作觸發了狀態表的初始化/重置機制。
6. **長時隨機寫入穩定性**：在 10 分鐘內，隨機對 LUN 0-3 進行 64MB-128MB 的隨機寫入，並隨機切換 MDWLSV 的 Enable/Disable 狀態。驗證在此高負載與狀態切換頻繁的情境下，測試不會超時（Timeout），且每次 Disable 後再 Enable 時，MDWLSV 表均能正確重置為零，確保狀態機無死鎖或狀態洩漏。

## Test Case (TC) Checkpoints

1. [Case01_Init_Disable_MDWLSV_Check]：
   - 動作：透過 `HwSetting` 將 `MEDIUM_SCAN_TRIGGER_TIME` 設為 0x80 以禁用 Media Scan。執行 Vendor Command C08C 禁用 MDWLSV (`disableMDWLSV=1`)，隨後立即執行 C08C 啟用 MDWLSV (`EnableMDWLSV=0`，注意代碼中 `self.disableMDWLSV = 1` 和 `self.EnableMDWLSV = 0`，但通常 C08C 參數 1 為 Enable, 0 為 Disable，需根據 `issue_C08C_to_EnDis_MDWLSV` 內部實現，假設 1=Enable, 0=Disable 或反之，代碼中先傳 1 再傳 0，然後讀取 0x4029)。讀取 Vendor Command 0x4029 獲取 MDWLSV Offset 資訊，並解析 `MDWLSV_format`。
   - 預期結果：解析後的 `MDWLSV_info` 必須通過 `check_mdwlsv_all_zero` 檢查，即所有 Die (0-3) 的所有 Offset 欄位（如 `Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` 等）數值必須全部為 0x00。這代表在初始禁用/啟用循環後，MDWLSV 狀態表處於乾淨的初始狀態。

2. [Case02_TLC_Write_Leveling_Tracking]：
   - 動作：配置 LUN (Normal LUN 0, Boot A/B, EM1 LUN 3)。在 Normal LUN (LUN 0) 寫入 `tlc_ce_page` (計算為 `Plane_Per_Die * 4 * 3`) 個 LBA 的資料。執行 Vendor Command 0x4029 獲取 MDWLSV Offset，解析出 `Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` (記為 `tlc_l2_offset`)。同時執行 Vendor Command 0x4022 讀取 NAND Feature 0x7F，獲取 P3 欄位值。執行 `get_previous_info` 確認最後程式化模組狀態。
   - 預期結果：`get_previous_info` 返回的 payload 第一個 byte 必須為 1 (代表 TLC L2)。`Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` 的值必須嚴格等於 NAND Feature 0x7F 的 P3 值，且不能為 0。這驗證了韌體在 Normal LUN 進行大塊 TLC 寫入時，正確更新了 MDWLSV 表中的 TLC 相關 Offset 欄位，並與 NAND Feature 記錄的狀態同步。

3. [Case03_EM1_Write_Leveling_Switch]：
   - 動作：在 EM1 LUN (LUN 3) 寫入 1 LBA 的資料。執行 Vendor Command 0x4029 獲取 MDWLSV Offset，解析出 `Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` (記為 `EM1_offset`)。執行 Vendor Command 0x4022 讀取 NAND Feature 0x7F，獲取新的 P3 值。執行 `get_previous_info` 確認狀態。
   - 預期結果：`get_previous_info` 返回的 payload 第一個 byte 必須為 4 (代表 EM1)。`Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 的值必須嚴格等於當前 NAND Feature 0x7F 的 P3 值 (即 4)，且不能為 0。這驗證了當寫入目標切換至 EM1 LUN 時，MDWLSV 表正確記錄了 EM1 相關的 Offset，並與 NAND Feature 狀態同步。

4. [Case04_Normal_L1_Write_No_EM1_Override_Check]：
   - 動作：在 Normal LUN (LUN 0) 寫入 1 LBA 的資料。執行 Vendor Command 0x4029 獲取 MDWLSV Offset。
   - 預期結果：代碼邏輯中，此步驟主要用於確保寫入成功。雖然代碼未在此處明確斷言 Normal LUN 的 Offset 變化，但結合後續步驟，此動作確保了系統處於混合寫入狀態。關鍵驗證點在於後續 Disable MDWLSV 前的狀態保持。

5. [Case05_MDWLSV_Disable_State_Preservation]：
   - 動作：執行 Vendor Command C08C 禁用 MDWLSV。執行 Vendor Command 0x4029 獲取 MDWLSV Offset。
   - 預期結果：解析後的 `Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 必須等於 Case03 中記錄的 `EM1_offset`，且 `Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` 必須等於 Case02 中記錄的 `tlc_l2_offset`。這證明禁用 MDWLSV 功能僅停止狀態更新或監控，並未清除或重置韌體內部已記錄的 Leveling Offset 狀態表。

6. [Case06_MDWLSV_Enable_Table_Reset]：
   - 動作：執行 Vendor Command C08C 啟用 MDWLSV。執行 Vendor Command 0x4029 獲取 MDWLSV Offset。
   - 預期結果：解析後的 `MDWLSV_info` 必須通過 `check_mdwlsv_all_zero` 檢查，即所有 Offset 欄位必須全部為 0x00。這驗證了重新啟用 MDWLSV 時，韌體會主動重置 MDWLSV Offset 表，確保新的寫入操作從乾淨的狀態開始追蹤，避免舊狀態干擾新的 Leveling 計算。

7. [Case07_Random_Write_Stability_With_MDWLSV_Toggling]：
   - 動作：進入 10 分鐘循環。每次循環隨機選擇 LUN (0-3)，隨機生成 10-32 個 Write10 命令，總寫入大小在 64MB 至 128MB 之間，並執行 HW Compare 驗證數據完整性。隨機觸發 MDWLSV 的 Enable/Disable 切換：若當前為 Disable 狀態，則隨機概率下執行 Enable，並立即讀取 0x4029 驗證表是否重置為零；若當前為 Enable 狀態，則隨機概率下執行 Disable。
   - 預期結果：
     1. 所有隨機寫入命令必須成功完成，無 Timeout 錯誤。
     2. 每次執行 MDWLSV Enable 後，緊接著讀取的 0x4029 數據必須全為 0x00。
     3. 整個 10 分鐘測試期間，系統必須保持穩定，無崩潰或無響應。這驗證了 MDWLSV 狀態機在高頻切換和大量數據寫入下的魯棒性與狀態重置機制的可靠性。