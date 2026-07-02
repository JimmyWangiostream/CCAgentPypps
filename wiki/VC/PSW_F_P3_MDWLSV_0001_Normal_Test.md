# Test Spec: MDWLSV Open Block Offset Consistency Verification

## Verification Criterion (VC)
驗證韌體在不同 LUN 類型（Normal TLC, EM1, RPMB）及不同寫入模式（Normal, Write Booster SLC）下，MDWLSV (Multi-Die Write Leveling Strategy Verification) 機制所記錄的 Open Block Offset 與 NAND Feature 中的 P3 欄位（代表當前寫入位置的物理區塊偏移）是否嚴格一致。測試涵蓋四個關鍵階段：
1. **TLC L2 寫入**：確認 Normal LUN 寫入 TLC CE Page 後，Die0 的 `SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` 與 NAND Feature P3 一致。
2. **EM1 L2 寫入**：確認 EM1 LUN 寫入後，Die0 的 `MM_OPEN_BLOCK_EM1_HOST_offset` 與 NAND Feature P3 一致。
3. **L1 與 WB 寫入**：確認 Normal LUN 寫入 L1 後，再啟用 Write Booster (WB) 寫入 SLC，Die0 的 `MM_OPEN_BLOCK_NOMAL_HOST_SLC_offset` 與 NAND Feature P3 一致。
4. **RPMB 與後續 TLC 寫入**：確認 RPMB LUN 寫入後，Die0 的 `MM_OPEN_BLOCK_RPMB_HOST_offset` 與 NAND Feature P3 一致，且隨後 Normal LUN 再次寫入 TLC 時，RPMB 的 Offset 保持不變（作為控制驗證）。

## Test Case (TC) Checkpoints
1. [TC01_TLC_L2_Write_Offset_Check]：
   - 動作：配置 LUN，針對 `TestNormalLun` (LUN 0) 寫入 1 個 TLC CE Page 大小的資料（長度為 `Plane_Per_Die * 4 * 3`）。透過 Vendor Command 0x4022 讀取 NAND Feature，解析 payload 第 16-19 位元組得到 `P3` 值。接著透過 Vendor Command 0x4029 讀取 MDWLSV Offset 資訊，解析 payload 第 46-47 位元組得到 `Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset`。
   - 預期結果：`Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` 的值必須等於 `P3` 的值，且兩者均不為 0。若不等於 0 或兩者不相等，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [TC02_EM1_L2_Write_Offset_Check]：
   - 動作：針對 `TestEM1Lun` (LUN 3) 寫入 1 LBA 大小的資料。透過 Vendor Command 0x4022 讀取 NAND Feature 得到新的 `P3` 值。接著透過 Vendor Command 0x4029 讀取 MDWLSV Offset 資訊，解析 payload 第 2-3 位元組得到 `Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset`。
   - 預期結果：`Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 的值必須等於該次寫入後讀取的 `P3` 值，且兩者均不為 0。若不等於 0 或兩者不相等，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

3. [TC03_L1_and_WB_SLC_Offset_Check]：
   - 動作：首先針對 `TestNormalLun` (LUN 0) 寫入 1 LBA 大小的資料（L1 寫入）。透過 Vendor Command 0x4022 讀取 NAND Feature 得到 `P3` 值。接著透過 Vendor Command 0x4029 讀取 MDWLSV Offset 資訊，解析 payload 第 14-15 位元組得到 `Die0_MDWLSV_MM_OPEN_BLOCK_NOMAL_HOST_SLC_offset`。驗證此 Offset 等於該次 L1 寫入後的 `P3`。隨後，啟用 Write Booster (`WRITEBOOSTER_EN`)，再次針對 `TestNormalLun` 寫入 1 LBA 資料。透過 Vendor Command 0x4022 讀取 NAND Feature 得到新的 `P3` 值。透過 Vendor Command 0x4029 讀取 MDWLSV Offset 資訊，解析 payload 第 18-19 位元組得到 `Die0_MDWLSV_MM_OPEN_BLOCK_WRITE_BOOSTER_offset`。
   - 預期結果：
     - L1 寫入階段：`Die0_MDWLSV_MM_OPEN_BLOCK_NOMAL_HOST_SLC_offset` 必須等於 L1 寫入後的 `P3` 值，且不為 0。
     - WB 寫入階段：`Die0_MDWLSV_MM_OPEN_BLOCK_WRITE_BOOSTER_offset` 必須等於 WB 寫入後的 `P3` 值，且不為 0。
     - 若任一階段 Offset 為 0 或與對應的 `P3` 值不符，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

4. [TC04_RPMB_Write_Offset_Check]：
   - 動作：禁用 Write Booster Buffer Flush (`WRITEBOOSTER_BUFFER_FLUSH_EN`)。透過 RPMB API 對 `RPMBRegion.REGION_0` 寫入 1 筆資料。透過 Vendor Command 0x4022 讀取 NAND Feature 得到 `P3` 值。接著透過 Vendor Command 0x4029 讀取 MDWLSV Offset 資訊，解析 payload 第 22-23 位元組得到 `Die0_MDWLSV_MM_OPEN_BLOCK_RPMB_HOST_offset`。
   - 預期結果：`Die0_MDWLSV_MM_OPEN_BLOCK_RPMB_HOST_offset` 的值必須等於 RPMB 寫入後讀取的 `P3` 值，且兩者均不為 0。若不等於 0 或兩者不相等，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

5. [TC05_Post_RPMB_TLC_Write_Control_Check]：
   - 動作：禁用 Write Booster Buffer Flush。針對 `TestNormalLun` (LUN 0) 再次寫入 1 個 TLC CE Page 大小的資料。透過 Vendor Command 0x4029 讀取 MDWLSV Offset 資訊，解析 payload 第 22-23 位元組得到 `Die0_MDWLSV_MM_OPEN_BLOCK_RPMB_HOST_offset`。
   - 預期結果：此步驟主要驗證在 Normal LUN 進行大量 TLC 寫入後，RPMB 相關的 Open Block Offset 欄位（`Die0_MDWLSV_MM_OPEN_BLOCK_RPMB_HOST_offset`）不應被錯誤更新或重置為 0，應保持與 TC04 結束時一致的有效值（或至少不為 0，視韌體具體實現而定，但腳本邏輯檢查其不為 0 且與之前 RPMB 寫入後的狀態邏輯相符，腳本中實際檢查的是 `rpmb_get_nand_feature.P3` 與 `MDWLSV_info.Die0_MDWLSV_MM_OPEN_BLOCK_RPMB_HOST_offset` 的匹配，這意味著韌體可能在每次寫入後更新所有相關 LUN 的 Offset 記錄或僅更新當前 LUN，腳本邏輯暗示檢查的是 RPMB 寫入後的 Offset 是否正確記錄，此處腳本邏輯稍顯重複，但核心是驗證 RPMB Offset 記錄的正確性）。*註：根據腳本邏輯，TC05 實際上是再次驗證 RPMB Offset 的正確性，確保在後續 TLC 寫入前，RPMB 的 Offset 記錄是準確的。*