# Test Spec: UFS BFEA (Bad Flash Element Analysis) & L2P Mapping Consistency Verification

## Verification Criterion (VC)
驗證韌體在執行 BFEA (Bad Flash Element Analysis) 掃描並標記特定 VB (Virtual Block) 為 Bin 3 後，針對該 VB 範圍內的 LBA 進行寫入操作，確認 L2P (Logical to Physical) 映射是否正確地將資料寫入至預期的 TLC VB，且該 VB 的 BFEA 狀態在寫入後仍保持為 Bin 0 (Normal/Active)，同時驗證寫入後的 VB 確實存在於 Current L2 VB (Group 7) 與 Used L2 VB (Group 17) 列表中，以確保韌體在 BFEA 標記情境下的寫入路由邏輯與狀態機切換正確無誤。

## Test Case (TC) Checkpoints
1. [TC01_LUN_Configuration_and_Purge_Check]：
   - 動作：透過 `random_config` 隨機選擇一個 LUN (`random_en_lun`, 0-31) 並啟用，配置其為 Normal Memory Type，分配總容量的一半作為 Alloc Units，並設定為 Thin Provisioning。接著對該 LUN 執行 Unmap 操作覆蓋整個 LBA 空間，並透過 SetFlag (PURGE_EN) 觸發 Purge 流程，輪詢 `AttributeIDN.PURGE_STATUS` 直到狀態碼等於 `0x03` (Purge Complete)。
   - 預期結果：LUN 配置成功應用；Purge 狀態碼必須精確等於 `0x03`，代表所有邏輯區塊已被標記為無效且硬體準備就緒，為後續寫入與 BFEA 測試提供乾淨的初始狀態。

2. [TC02_BFEA_Scan_Preparation_and_Verification]：
   - 動作：呼叫 `get_target_vb_list` 取得 Group ID 為 `27` (Free Queue TLC) 的 VB 列表作為目標 VB (`target_set_bfea_vb_list`)。針對列表中的每個 VB 及每個 CE (Chip Enable)，發送 Vendor Command `0x40B0` 參數 `2` (BFEA Scan Set) 並指定 `bin=3`。隨後立即發送參數 `3` (BFEA Scan Get) 讀取 payload 的 Byte[0:3]。
   - 預期結果：讀取的 payload Byte[0:3] (Little Endian) 數值必須精確等於 `3` (即 `self.bin`)，代表韌體已成功將指定 VB 的 BFEA 狀態標記為 Bin 3 (Bad/Reserved)，且查詢機制能正確回傳該標記值。

3. [TC03_Data_Write_and_L2P_Mapping_Check]：
   - 動作：計算寫入長度為 `tlc_vb_size * 3.5` (約 0.5 VB 大小)，以 512KB (128 x 4KB) 為 Chunk Size，對目標 LUN 執行連續 Write10 命令，並啟用 `fua=1` 與 `CmdParamPatternMode.HW_FIX`。寫入完成後，透過 `api.lba_to_pba` 將最後一個 LBA (`total_len - 1`) 轉換為 PBA，提取其 VB (`w10_block`) 與 CE (`b5_ce`) 編號，並檢查前 90% 的 LBA 分段映射，收集所有涉及的 VB 與 CE 進入 `check_vb_list` 與 `check_ce_list`。
   - 預期結果：寫入命令必須全部成功；`check_vb_list` 中必須包含至少一個 VB，且這些 VB 必須與步驟 2 中標記為 Bin 3 的 VB 列表 (`target_set_bfea_vb_list`) 有重疊或邏輯關聯，證明寫入操作確實觸發了針對特定 VB 的映射行為。

4. [TC04_Post_Write_BFEA_Status_and_Group_Consistency_Check]：
   - 動作：針對 `check_vb_list` 中的每個 VB 與 CE，發送 Vendor Command `0x40B0` 參數 `3` (BFEA Scan Get) 讀取 payload Byte[0:3]。同時，分別呼叫 `get_target_vb_list` 取得 Group 7 (Current L2 VB) 與 Group 17 (Used L2 VB) 的 VB 列表。檢查 `check_vb_list` 中的 VB 是否同時存在於 Group 7 和 Group 17 的列表中。
   - 預期結果：
     1. 所有檢查 VB 的 BFEA 狀態 (Byte[0:3]) 必須精確等於 `0`，代表韌體在寫入後自動將該 VB 從 Bin 3 恢復為 Normal (Bin 0) 狀態，或寫入操作未觸發 BFEA 錯誤標記。
     2. `check_vb_list` 中的 VB 必須同時存在於 Group 7 (Current L2) 和 Group 17 (Used L2) 列表中，若任一條件不滿足，則拋出 `SIGHTING_PBA_UNEXPECTED` 錯誤，驗證 L2P 映射與 VB 狀態機在寫入後的正確性與一致性。