# Test Spec: UFS BBT (Bad Block Table) Consistency Verification via Vendor Command 40C8

## Verification Criterion (VC)
驗證 UFS 韌體內部維護的 Bad Block Table (BBT) 與透過 Vendor Command (VU) 0x40C8 查詢到的硬體層級壞塊資訊是否完全一致。測試邏輯分為兩階段：首先透過 Direct Read 讀取 Flash 特定 LWP 的 Spare Area 標記 (0x8B) 定位 BBT 儲存區塊，並解析其位元圖以計算各 CE/Plane 的壞塊總數；其次，透過 VU 0x40C8 獲取韌體統計的壞塊計數。最終比對「總壞塊數」與「各 CE/Plane 維度的壞塊分佈」，確保韌體邏輯與硬體實際狀態無偏差。

## Test Case (TC) Checkpoints
1. [BBT_Locality_and_Parsing_Check]：
   - 動作：執行 `find_bbt_block` 函數，對 Flash 前 20 個 VB (Virtual Block) 進行全空間掃描 (CE x Plane x Block)。針對每個 LWP 執行 Direct Read (PCA: `l0_op=0x20000`, `b4_mode=1`, `l12_fpage=0`)，讀取包含 FW Spare 的 4KB 資料。檢查資料偏移量 `api.DATA_SIZE_4K_BYTE * 4 + 4` (即第 16KB+4 位元組，對應第 4 頁的 Spare Area 特定欄位) 是否等於 `0x8B`。若找到標記，則將該 PCA 與 Payload 傳回，並執行 `calculate_bbt` 解析 Payload。解析邏輯為：遍歷所有 CE 和 Block/Plane，計算 offset `block * (Plane_Per_Die // 2) + plane // 2`，讀取該位元組並檢查 `(data[offset] >> 4 * (plane % 2)) & 0xF` 的第 1 bit (`api.BIT2`) 是否為 1。若為 1，則記錄該 Block/CE/Plane 為壞塊。
   - 預期結果：必須在 Block < 20 的範圍內找到 Spare Mark 為 `0x8B` 的區塊；成功解析出 `self.BB_DATA` 列表，其中每個元素包含正確的 Block, CE, Plane 資訊，且總壞塊數等於列表中元素個數。若 Block >= 20 仍未找到，則拋出 `SIGHTING_PBA_UNEXPECTED` 錯誤。

2. [VU_40C8_Total_BB_Count_Check]：
   - 動作：透過 `project_api.issue_40C8_to_get_bad_blocks_count()` 發送 Vendor Command 0x40C8，獲取回應資料 `self.VU_DATA`。解析 `self.VU_DATA[0:4]` (Little Endian) 得到 `total_CePlane` (總 CE/Plane 數量)。計算韌體報告的總壞塊數：從 offset 4 開始，每 4 位元組代表一個 CE/Plane 的壞塊數，累加所有 CE/Plane 的壞塊數得到 `total_BB_count`。
   - 預期結果：成功獲取 VU 回應；計算出的 `total_BB_count` 必須與 Step 1 中解析出的 `len(self.BB_DATA)` 完全相等。若不相等，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

3. [VU_40C8_CePlane_Distribution_Check]：
   - 動作：從 `self.VU_DATA` 中提取每個 CE/Plane 的壞塊計數，存入列表 `CePlane_VU` (長度為 `total_CePlane`)。同時，根據 Step 1 解析出的 `self.BB_DATA`，統計每個 CE/Plane 索引 (`index = CE * Plane_Per_Die + Plane`) 下的壞塊數量，存入列表 `CePlane_BBT`。比對 `CePlane_VU` 與 `CePlane_BBT` 兩個列表是否逐元素相等。
   - 預期結果：`CePlane_VU` 與 `CePlane_BBT` 必須完全一致。這代表韌體不僅總計正確，且壞塊在物理儲存單元 (CE/Plane) 上的分佈也與 VU 查詢結果吻合。若有任何索引位置的數值不同，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。