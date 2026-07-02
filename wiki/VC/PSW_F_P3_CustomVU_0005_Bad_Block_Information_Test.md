# Test Spec: UFS BBT (Bad Block Table) Consistency Verification between Firmware and Micron VU

## Verification Criterion (VC)
驗證 UFS 韌體內部計算出的 BBT (Bad Block Table) 與透過 Vendor Command 0x405E 從 Micron VU (Vendor Utility) 獲取的硬體 BBT 資訊在邏輯上完全一致。驗證過程包含三個核心階段：首先透過 Vendor Command 0x405E 讀取硬體層級的壞塊統計與詳細列表；其次，透過 Direct Read 指令掃描 Flash 介面的 Spare Area 標記（特定 Byte 0x8B）定位 BBT 儲存區塊，並解析該區塊內的位元圖（Bitmask）以重建韌體視角的 BBT；最後，嚴格比對兩者之間的總壞塊數量、Block ID、CE (Chip Enable) 及 Plane 索引是否完全匹配，確保韌體對 Flash 介面的壞塊識別機制與硬體報告無誤差。

## Test Case (TC) Checkpoints
1. [Step1_VU_BBT_Data_Extraction]：
   - 動作：執行 Vendor Command 0x405E，從 UFS 裝置讀取 BBT 相關資訊，並將返回的原始資料儲存於 `self.VU_DATA` 中。該資料結構的前 4 Bytes (Little Endian) 為總壞塊數量，後續每 8 Bytes 描述一個壞塊的詳細資訊（包含退休原因、PBA 地址等）。
   - 預期結果：成功獲取非空的 `self.VU_DATA`，且資料長度符合預期，代表 Vendor Command 0x405E 正確返回了硬體層級的 BBT 報告。

2. [Step2_BBT_Block_Location_and_Parsing]：
   - 動作：遍歷 Flash 的所有 VB (Virtual Block) 索引 (0 至 `l52_total_vb_count - 1`)、所有 CE (0 至 `Max_Fdevice - 1`) 及所有 Plane (0 至 `Plane_Per_Die - 1`)。針對每個組合，設定 Direct Read PCA 參數：`l0_op = 0x20000` (Direct Read), `b4_mode = 1` (SLC Mode), `l12_fpage = 0`。讀取包含 FW Spare Area 的 4KB 資料。檢查資料偏移量 `api.DATA_SIZE_4K_BYTE * 4 + 4` (即第 16KB + 4 Bytes 處，通常對應於特定 Block 的 Spare Area 標記位) 是否等於 `0x8B`。若找到匹配項，則記錄該 PCA 配置並返回對應的 Payload 作為 BBT 原始數據；若遍歷至 Block >= 20 仍未找到，則拋出 `SIGHTING_PBA_UNEXPECTED` 錯誤。
   - 預期結果：在 Block < 20 的範圍內成功定位到 BBT 儲存區塊，且該區塊對應的 Spare Area 標記位確認為 `0x8B`，成功提取出包含壞塊位圖的 `bbt_block_data`。

3. [Step3_BBT_Reconstruction]：
   - 動作：根據提取的 `bbt_block_data` 計算韌體視角的 BBT。對於每個 CE，讀取對應的 4KB 資料段。在每個 CE 的資料段內，遍歷所有 Block 和 Plane。計算位圖偏移量 `offset = block * (Plane_Per_Die // 2) + plane // 2`。從 `data[offset]` 中提取對應 Plane 的壞塊類型標記：`bad_type = (data[offset] >> 4*(plane%2)) & 0xF`。檢查 `bad_type` 的第 2 位 (Bit 2, `api.BIT2`) 是否為 1。若為 1，則將該 Block、CE、Plane 組合加入 `self.BB_DATA` 列表。
   - 預期結果：`self.BB_DATA` 列表準確反映了 Flash 介面上所有被標記為壞塊 (Bit 2 set) 的邏輯位置，且列表長度與硬體報告的總壞塊數一致。

4. [Step4_Consistency_Check_VU_vs_Firmware]：
   - 動作：
     1. 解析 `self.VU_DATA` 前 4 Bytes 得到 `total_BB_count` (Micron VU 報告的總壞塊數)。
     2. 比對 `total_BB_count` 與 `len(self.BB_DATA)` (韌體計算的總壞塊數)。若不相等，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     3. 建立 `VU_DATA_map`：遍歷 `self.VU_DATA` 中的每個壞塊記錄，解析 PBA 格式獲取 `blockNum` 和 `CePlane`，將 `CePlane >> 3` (即 CE 索引) 存入以 Block 為 Key 的列表中。
     4. 遍歷韌體計算出的 `self.BB_DATA` 中的每個壞塊，計算其 `CePlane` 值 (`CE * Plane_Per_Die + Plane`)。
     5. 檢查 `bbt["Block"]` 是否存在於 `VU_DATA_map` 中，且計算出的 `CePlane` 是否存在於對應的列表中。若任一條件不滿足，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
   - 預期結果：
     1. Micron VU 報告的總壞塊數與韌體解析出的壞塊數完全相等。
     2. 韌體識別出的每一個壞塊 (Block, CE, Plane) 都能在 Micron VU 的報告中找到完全對應的記錄。
     3. 這證明韌體的 BBT 解析邏輯與硬體 Vendor Command 返回的真實狀態完全同步，無遺漏或誤判。