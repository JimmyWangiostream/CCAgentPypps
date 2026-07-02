# Test Spec: UFS BFEA (Bad Flash Entry Allocation) State Verification via Vendor Command 0x40B0

## Verification Criterion (VC)
驗證韌體 BFEA (Bad Flash Entry Allocation) 機制在特定 LUN 寫入操作後的狀態一致性與正確性：
1. **BFEA Table Initialization (Flow2)**：確認透過 Vendor Command 0x40B0 (Function Code 2) 對所有 TLC VB (Group ID 27) 進行 BFEA Scan 設定後，韌體能正確記錄 Bin Index (0x03)；並透過 Function Code 3 讀取確認該 Bin Index 與預期值 `self.bin` (0x03) 完全匹配，驗證 BFEA 表項寫入成功。
2. **RPMB Write Impact (Case 01)**：確認在 RPMB LUN (LUN 1) 執行全容量寫入後，針對 RPMB 區域對應的 VB/CE 執行 BFEA Scan (Function Code 3)，其輸出 Byte[0-3] 必須為 0x00000000，驗證 RPMB 寫入不影響 BFEA 狀態或 BFEA 狀態保持初始 Clean 狀態。
3. **Boot LUN Write Impact (Case 02)**：確認在 Boot LUN A (LUN 2) 執行全容量寫入後，針對 Boot LUN 對應的 VB/CE 執行 BFEA Scan，輸出 Byte[0-3] 必須為 0x00000000，驗證 Enhanced Memory 區域的寫入操作不會觸發錯誤標記。
4. **Enhanced Memory Write Impact (Case 03)**：確認在 Enhanced Memory LUN (LUN 3) 執行全容量寫入後，針對該 LUN 對應的 VB/CE 執行 BFEA Scan，輸出 Byte[0-3] 必須為 0x00000000，驗證 Enhanced 區域寫入正常且無 Bad Block 標記。
5. **Write Booster SLC Write Impact (Case 04)**：確認在啟用 Write Booster (WB) 後，針對 Normal LUN (LUN 0) 寫入 SLC 容量資料，針對該 LUN 對應的 VB/CE 執行 BFEA Scan，輸出 Byte[0-3] 必須為 0x00000000，驗證 WB 機制下的 SLC 寫入未導致 Flash 壞塊或 BFEA 狀態異常。

## Test Case (TC) Checkpoints

1. [Case01_BFEA_Init_RPMB_Write_Check]：
   - 動作：
     1. 透過 `get_target_vb_list(27)` 取得所有 TLC VB 列表 (`free_queue_tlc`)。
     2. 針對每個 VB 及每個 CE，發送 Vendor Command 0x40B0 (Function Code 2, Set BFEA)，參數為 `vb`, `ce`, `bin=3`。
     3. 針對同一 VB/CE，發送 Vendor Command 0x40B0 (Function Code 3, Get BFEA)，讀取 payload。
     4. 驗證 payload Byte[0-3] (Little Endian) 等於 `self.bin` (0x03)。若不等則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     5. 執行 `flow3(1)`：透過 RPMB API 對 RPMB LUN (LUN 1) 寫入 4MB 資料 (`BLOCK256B_SIZE_4M_BYTE * 4`)。
     6. 計算 RPMB LUN (LUN 1) 起始 LBA 0 對應的 PBA，提取其 VB (`test_vb`) 與 CE (`test_ce`)。
     7. 針對該 `test_vb` 與 `test_ce`，發送 Vendor Command 0x40B0 (Function Code 3)，讀取 payload。
   - 預期結果：
     - 步驟 4 中，所有 TLC VB 的 BFEA 讀回值必須為 0x03，確認 BFEA 表項設定生效。
     - 步驟 7 中，payload Byte[0-3] 必須等於 0x00000000，代表 RPMB 寫入後，該 Flash 區域的 BFEA 狀態為 Clean (Bin 0)，無壞塊標記。

2. [Case02_BFEA_BootLUN_Write_Check]：
   - 動作：
     1. 執行 `flow3(2)`：對 Boot LUN A (LUN 2) 寫入全容量資料 (`_param.gLUCapacity[2]`)，使用 HW_FIX 模式。
     2. 計算 Boot LUN A (LUN 2) 起始 LBA 0 對應的 PBA，提取其 VB (`test_vb`) 與 CE (`test_ce`)。
     3. 針對該 `test_vb` 與 `test_ce`，發送 Vendor Command 0x40B0 (Function Code 3)，讀取 payload。
   - 預期結果：
     - payload Byte[0-3] 必須等於 0x00000000，代表 Boot LUN 寫入完成後，對應 Flash 區域的 BFEA 狀態為 Clean，韌體未標記任何 Bad Block。

3. [Case03_BFEA_EnhancedLUN_Write_Check]：
   - 動作：
     1. 執行 `flow3(3)`：對 Enhanced Memory LUN (LUN 3) 寫入全容量資料 (`_param.gLUCapacity[3]`)，使用 HW_FIX 模式。
     2. 計算 Enhanced LUN (LUN 3) 起始 LBA 0 對應的 PBA，提取其 VB (`test_vb`) 與 CE (`test_ce`)。
     3. 針對該 `test_vb` 與 `test_ce`，發送 Vendor Command 0x40B0 (Function Code 3)，讀取 payload。
   - 預期結果：
     - payload Byte[0-3] 必須等於 0x00000000，代表 Enhanced Memory 寫入完成後，對應 Flash 區域的 BFEA 狀態為 Clean。

4. [Case04_BFEA_WB_SLC_Write_Check]：
   - 動作：
     1. 執行 `flow3(4)`：
        - 設定 Flag `WRITEBOOSTER_EN` 啟用 Write Booster。
        - 對 Normal LUN (LUN 0) 寫入 SLC 容量資料 (`self.slc_vb_size`)，使用 HW_FIX 模式。
     2. 計算 Normal LUN (LUN 0) 起始 LBA 0 對應的 PBA，提取其 VB (`test_vb`) 與 CE (`test_ce`)。
     3. 針對該 `test_vb` 與 `test_ce`，發送 Vendor Command 0x40B0 (Function Code 3)，讀取 payload。
   - 預期結果：
     - payload Byte[0-3] 必須等於 0x00000000，代表在 Write Booster 啟用狀態下，SLC 區域寫入完成後，對應 Flash 區域的 BFEA 狀態為 Clean，WB 機制未引入 Flash 壞塊或狀態異常。