# Test Spec: UFS BBR/REMAP Table Consistency Verification via 40C9 VU

## Verification Criterion (VC)
驗證韌體內部維護的 BBR (Bad Block Replacement) 與 REMAP 映射表與 Flash 硬體底層狀態的一致性：透過解析 SRAM 中的 REMAP 表與直接讀取 Flash Spare Area 中的 BBR 表，建立 `Physical VB (pb)` 到 `Logical VB` 的完整映射鏈；隨後發送 Micron Vendor Command 0x40C9 查詢該物理區塊對應的邏輯 VB，並嚴格比對 40C9 返回的 `logical_vb` 與由 BBR/REMAP 表計算得出的預期 `logical_vb` 是否完全一致，以確保韌體映射邏輯與硬體實際狀態無偏差。

## Test Case (TC) Checkpoints
1. [BBR_Table_Parsing_and_Consistency_Check]：
   - 動作：
     1. 初始化並讀取 Flash 設定 (`FlashSetting`) 與韌體幾何資訊。
     2. 執行 `find_bbr_table`：遍歷 Block 0-19，針對每個 CE 與 Plane 執行 Direct Read (PCA `0x20000`, SLC mode)，檢查 Spare Area 前 5 位元組是否為 `0xFF, 0xFF, 0xFF, 0xFF, 0x8B` 且第 128 位元組第 4 位 (`spare[128] & 0x10`) 為 0。若符合，則從 Page 2 讀取兩筆 4KB 資料組合成 BBR Raw Data。
     3. 解析 BBR Raw Data：根據 `plane_shift=3` 計算每個 CE/Plane 的起始索引，每 256 位元組為一個 CE/Plane 的 BBR 表。遍歷索引 0-126 (步長 2)，解壓縮 Little-Endian 16-bit 整數。若 `pb` (offset `i*2`) 不等於 `0xFFFF`，則記錄該條目至 `bbr_list`，包含 `ce`, `pln`, `vb` (BBR VB, offset `i*2+2`), `pb`。
     4. 執行 `find_remap_table`：從 SRAM 地址 `debug_info.VB_list_remap_address` 讀取 REMAP 表，遍歷所有 `vb` (0 至 `l52_total_vb_count`)，解壓縮 Little-Endian 16-bit 整數，記錄 `vb` 與 `remap_vb` 至 `remap_list`。
     5. 建立映射鏈：遍歷 `physical_vb` 從 20 至總 VB 數。若 `physical_vb` 存在於 `bbr_list` 中，計算 `plnId = ce*6 + pln`，取得 `bbr_vb`。接著在 `remap_list` 中尋找 `remap_vb == bbr_vb` 的條目，取得 `logical_vb`。若找到，將 `{logical_vb, physical_vb, ce, plane, plnId}` 加入 `vb_map_list`。
     6. 驗證一致性：對 `vb_map_list` 中的每一項，發送 Vendor Command 0x40C9 (透過 `issue_40C9_to_get_logical_vb`)，傳入 `pb` 與 `plnId`，獲取硬體返回的 `vb.logical_vb.value`。
     7. 比對：檢查 40C9 返回的 `vb.logical_vb.value` 是否等於 `vb_map_list` 中對應的 `logical_vb`。
   - 預期結果：
     - BBR 表解析必須成功識別出有效的 Bad Block 映射條目 (`pb != 0xFFFF`)。
     - REMAP 表必須正確讀取並解析。
     - 對於每一個成功映射的 `physical_vb`，Vendor Command 0x40C9 返回的 `logical_vb` 必須與由 BBR 表 (`bbr_vb`) 和 REMAP 表 (`remap_vb -> vb`) 鏈式計算得出的 `logical_vb` **完全相等**。
     - 若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，表示韌體映射表與硬體實際邏輯區塊編號不一致，存在映射錯誤風險。