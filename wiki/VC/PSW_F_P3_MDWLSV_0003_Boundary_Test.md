# Test Spec: MDWLSV Offset Consistency & P3 Alignment Verification

## Verification Criterion (VC)
驗證 UFS 韌體在多通道（Multi-CE）與混合儲存類型（SLC EM1 vs TLC Normal）並行寫入情境下，MDWLSV（Multi-Die Write Life Span Verification）機制中 `EM1_HOST` 的 Offset 欄位與 NAND Flash 硬體特徵欄位 `P3` 的一致性與同步性：
1. **VC12 (Initial State)**：確認在 EM1 LUN 寫入單個 SLC CE Page 且 Normal LUN 寫入 TLC CE Page 後，EM1 LUN 的 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 必須等於其對應的 `SB0_offset`（Sub-block 0 offset），代表初始狀態下 Offset 與 Sub-block 偏移量一致。
2. **VC13 (Full Plane Fill)**：確認在 EM1 LUN 持續寫入直到觸發特定物理頁條件（如 `first_empty_physical_page % 4 == 3` 且 `first_empty_CE == 1`）後，再寫入 TLC Share Page，此時 EM1 LUN 的 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 必須重置為 `0`，代表韌體已正確處理了 Open Block 的邊界切換或重置邏輯。
3. **VC14 (P3 Alignment & Multi-CE Sync)**：確認在 SADVersion 2/3 下，針對每個 CE (Chip Enable) 逐 Plane 寫入 EM1 LUN 時，韌體讀取的 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 必須嚴格等於該 CE 上所有已寫入 Plane 的 `P3` 欄位值中的最小值（Min P3）。此驗證確保韌體維護的邏輯 Offset 與 NAND 硬體記錄的 Program Verify 狀態（P3）在多通道並行寫入時保持絕對同步，無競態條件或狀態不同步。

## Test Case (TC) Checkpoints

1. [VC12_Initial_MDWLSV_Offset_Equality_Check]：
   - 動作：配置 LUN（EM1 LUN=3, Normal LUN=0），寫入 1 個 SLC CE Page Size (`slc_ce_page`) 至 EM1 LUN (LBA 0)，接著寫入 1 個 TLC CE Page Size (`tlc_ce_page`) 至 Normal LUN (LBA 0)。透過 Vendor Command 0x4029 讀取 MDWLSV Offset 資訊，解析 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 與 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_SB0_offset`。
   - 預期結果：`MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset.value` 必須等於 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_SB0_offset.value`。若不相等，則代表韌體在初始寫入後未正確初始化或同步 Sub-block 0 的偏移量，測試失敗。

2. [VC13_Em1_Full_Plane_Reset_To_Zero_Check]：
   - 動作：重置 LUN 配置。先寫入 16KB (`BLOCK4K_SIZE_16K_BYTE`) 至 EM1 LUN，接著寫入 TLC CE Page 至 Normal LUN。進入循環，持續寫入 16KB 至 EM1 LUN 並監控 `OpenVBInfo`，直到滿足條件：`SLC_L2.first_empty_physical_page.value % 4 == 3` 且 `first_empty_CE.value == 1` 且 `first_empty_plane.value == 0`（或單通道下 `first_empty_physical_page.value == 4`）。滿足條件後，寫入 1 個 TLC Share Page Size (`tlc_pageline`) 至 Normal LUN。最後透過 VU 0x4029 讀取 MDWLSV Offset。
   - 預期結果：`MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset.value` 必須等於 `0`。此結果驗證韌體在 EM1 LUN 填滿特定 Plane 配置並觸發 TLC 共享寫入後，正確將 EM1 的 Host Offset 重置為 0，符合 MDWLSV 的邊界管理邏輯。

3. [VC14_P3_Min_Value_Alignment_Check]：
   - 動作：
     1. **SADVersion 2/3 初始化**：對每個 CE (0 至 `ce_num-1`)，逐 Plane 寫入 16KB 至 EM1 LUN。在寫入過程中，若 `get_previous_info` 返回的 `previos_payload[ce*2] == MDWLSV_EM1`，則透過 Vendor Command 0x4022 讀取該 CE 的 NAND Feature，提取 `P3` 欄位值。
     2. **記錄基準值**：記錄每個 CE 首次出現 `MDWLSV_EM1` 時的 `P3` 值作為 `firstEM1P3[ce]`。
     3. **持續寫入與驗證**：繼續逐 Plane 寫入 EM1 LUN。每次寫入後，讀取 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset`。
     4. **比對邏輯**：計算當前 CE 所有已寫入 Plane 的 `P3` 值的最小值 (`p3_min`)。
   - 預期結果：
     - 對於每個 CE，`MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset.value` 必須嚴格等於 `p3_min`。
     - 若 `firstEM1P3[ce]` 不為 `0xFF` 且 `checkEM1P3[ce]` 為 True，則 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset.value` 必須等於 `firstEM1P3[ce]`。
     - 此檢查確保韌體維護的 MDWLSV Offset 始終反映硬體 NAND 中該 CE 上所有 Plane 的最低 P3 狀態，驗證多通道寫入時的狀態一致性。

4. [VC14_SADVersion2_SB0_Bitmap_Check]：
   - 動作：在 SADVersion 2 下，當寫入完成最後一個 Plane (`i == Plane_Per_Die - 1`) 且 `previos_payload[ce*2] == MDWLSV_EM1` 時，讀取 MDWLSV Offset 資訊。
   - 預期結果：`MDWLSV_MM_OPEN_BLOCK_EM1_HOST_SB0_offset.value` 必須等於 `MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset.value`。這驗證了在 SADVersion 2 的特定寫入序列後，SB0 的 Bitmap 或 Offset 狀態與主 Offset 保持一致，無殘留差異。

5. [VC14_SADVersion3_SLC_Share_Page_Reset_Check]：
   - 動作：在 SADVersion 3 下，完成上述逐 Plane 寫入後，寫入 1 個 SLC Share Page Size (`slc_pageline`) 至 EM1 LUN。讀取 MDWLSV Offset 資訊。
   - 預期結果：對於每個 CE，`MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset.value` 必須等於該 CE 在整個測試過程中記錄到的最小 `P3` 值 (`minEM1P3[ce]`)。這驗證了在 SLC Share Page 寫入後，MDWLSV Offset 仍正確反映硬體 P3 狀態。

6. [Final_OpenVB_Reset_Check]：
   - 動作：寫入 `slc_vb_size - 1 * slc_ce_page` 至 EM1 LUN。進入循環，只要 `SLC_L2.first_empty_physical_page.value != 0`，就寫入 4 Pages 至 EM1 LUN。最後讀取 VU 0x4029 的回應 Payload。
   - 預期結果：VU 0x4029 回應的 Payload 前 4 個 Byte (`data_payload[0:4]`) 必須全部為 `0x00`。這驗證在 Open VB 重置或特定邊界條件下，韌體返回的狀態資訊為零，符合預期規範。