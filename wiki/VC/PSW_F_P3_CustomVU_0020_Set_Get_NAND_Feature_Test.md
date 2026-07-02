# Test Spec: UFS Vendor Command NAND Feature Register Read/Write & MDWLSV Offset Verification

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command (0x4022/0x4023) 對 NAND Flash 內部 Feature Register 的讀寫一致性與狀態恢復機制，並確認 MDWLSV (Multi-Die Write Leveling Save/Verify) 相關 Block Offset 資訊的結構完整性：
1. **Feature Register 讀寫一致性**：針對所有 CE (Chip Enable) 及指定的 Feature Address (0x01, 0x10, 0x20 等)，確認 `issue_4022` (Get) 能正確回傳 P1-P4 參數，且 `issue_4023` (Set) 能將指定參數寫入硬體暫存器。
2. **隨機值注入與恢復**：針對 Feature Address `0x01`，驗證寫入隨機生成的 P1-P4 值後，透過 `issue_4022` 讀回的值與寫入值完全一致；隨後寫入原始預設值，確認狀態可完全恢復至初始狀態。
3. **MDWLSV 結構解析**：驗證 `assign_MDWLSV_info` 函數能正確從 Vendor Command 回傳的 Payload 中解析出 Die 0-3 的各種 Open Block Offset (如 EM1_HOST, TABLE_PTE, NORMAL_HOST_SLC/TLC 等) 及其 SB0 (Secondary Block 0) 偏移量，確保記憶體映射結構無誤。

## Test Case (TC) Checkpoints

1. [Feature_Register_Read_Write_Consistency_Check]：
   - 動作：
     1. 初始化 LUN 配置，啟用 Normal (LUN 0), BootA (LUN 1), BootB (LUN 2), EM1 (LUN 3)。
     2. 遍歷所有 CE (從 0 到 `Max_Fdevice` - 1)。
     3. 對於 `make_payload()` 定義的地址列表 (包含 0x01, 0x10, 0x20, 0x22, 0x23, 0x24, 0x40, 0x58, 0x7F, 0x80, 0x81, 0x83, 0x84, 0x86, 0x87, 0x90, 0x93, 0x96, 0xA0, 0xA1, 0xA2, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xAB, 0xB1, 0xB2, 0xB3, 0xB4, 0xDA, 0xE1, 0xE2, 0xE3, 0xE7)，執行以下循環：
        - 呼叫 `issue_4022_to_get_NAND_feature(CE, b)` 讀取當前 Feature Register 狀態，解析出 `result`, `die`, `P1`, `P2`, `P3`, `P4`。
        - 若地址 `b` 不等於 `0x58`，則呼叫 `issue_4023_to_set_NAND_feature(CE, b, P1, P2, P3, P4)` 將讀回的預設值重新寫入（確保狀態不變或確認寫入成功），並檢查回傳的 `q_value`。
   - 預期結果：
     - 所有 `issue_4022` 呼叫必須成功回傳有效的 `data_payload`，且解析出的 `result` 欄位應為 0 (Success)。
     - 所有 `issue_4023` 呼叫必須成功寫入，回傳的 `q_value` 應符合預期（通常為 0 或特定狀態碼），代表 NAND 控制器已接受該 Feature 設定。
     - 對於地址 `0x58`，跳過寫入步驟，僅驗證讀取功能正常。

2. [Feature_01_Random_Injection_and_Recovery_Check]：
   - 動作：
     1. 針對每個 CE，首先呼叫 `issue_4022_to_get_NAND_feature(CE, 0x01)` 獲取 Feature Address `0x01` 的原始預設值，記錄為 `feature01_P1`, `feature01_P2`, `feature01_P3`, `feature01_P4`。
     2. 生成四個隨機整數 `testP1`, `testP2`, `testP3`, `testP4` (範圍 0x01 - 0xFF)。
     3. 呼叫 `issue_4023_to_set_NAND_feature(CE, 0x01, testP1, testP2, testP3, testP4)` 將隨機值寫入 NAND Feature Register `0x01`。
     4. 立即呼叫 `issue_4022_to_get_NAND_feature(CE, 0x01)` 讀回當前值，解析為 `get_nand_feature`。
     5. 驗證讀回的 `P1`, `P2`, `P3`, `P4` 是否分別等於 `testP1`, `testP2`, `testP3`, `testP4`。
     6. 呼叫 `issue_4023_to_set_NAND_feature(CE, 0x01, feature01_P1, feature01_P2, feature01_P3, feature01_P4)` 將原始預設值寫回。
     7. 再次呼叫 `issue_4022_to_get_NAND_feature(CE, 0x01)` 讀回，驗證 `P1`-`P4` 是否恢復為初始的 `feature01_P1`-`feature01_P4`。
   - 預期結果：
     - 步驟 4 讀回的 `P1`-`P4` 必須精確等於步驟 2 生成的隨機值，證明 Vendor Command 寫入邏輯正確且暫存器狀態已更新。
     - 步驟 7 讀回的 `P1`-`P4` 必須精確等於步驟 1 記錄的原始預設值，證明韌體支援 Feature Register 的狀態恢復，無資料損毀或鎖定現象。

3. [MDWLSV_Structure_Parsing_Integrity_Check]：
   - 動作：
     1. 雖然 `step1` 中未直接呼叫 `issue_4029`，但程式碼提供了 `assign_MDWLSV_info` 函數用於解析 Vendor Command 回傳的 Payload。
     2. 驗證該函數的解析邏輯：從 `data_payload` 的特定索引位置提取數據並賦值給 `MDWLSV_format` 結構體。
     3. 重點檢查 Die 0 至 Die 3 的 Offset 解析公式，例如 Die 0 使用索引 `i`，Die 1 使用 `i + 1*60`，Die 2 使用 `i + 2*60`，Die 3 使用 `i + 3*60`。
     4. 檢查關鍵 Offset 欄位，如 `Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` (索引 2), `Die0_MDWLSV_MM_OPEN_BLOCK_TABLE_PTE_offset` (索引 6), `Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` (索引 46) 等是否正確映射。
   - 預期結果：
     - `assign_MDWLSV_info` 必須能正確將二進制 Payload 轉換為結構化物件。
     - 對於任何給定的合法 Payload，解析出的 Offset 值必須與 Payload 中對應字節的數值完全一致。
     - 結構體中的 `DieX_MDWLSV_..._SB0_offset` 欄位必須對應到 Payload 中 `offset_index + 1` 的位置（例如 `EM1_HOST` 在索引 2，其 `SB0` 在索引 3），確保 Secondary Block 偏移量的相對關係正確。