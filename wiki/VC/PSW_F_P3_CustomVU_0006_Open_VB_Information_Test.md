# Test Spec: UFS Open VB Lifecycle & GC Trigger Verification

## Verification Criterion (VC)
驗證 UFS 韌體在連續寫入、電源循環（SSU Sleep/Active）及 Write Booster (WB) 觸發機制下，Open VB (Virtual Block) 狀態機與內部 GC (Garbage Collection) 流程的正確性：
1. **基礎寫入與 VB 分配**：確認在 Normal、EM1 及 WB LUN 上進行 1MB 順序寫入後，Open VB 資訊中的 `first_free_physical_page` 指標會正確遞增，且所有預設 VB 欄位（如 L2_Open, WB_L2, Swap_Rain 等）均存在且非 0xFFFFFFFF。
2. **SSU 電源循環穩定性**：確認在執行 SSU Sleep (0x02) 後再 Active (0x01)，韌體能正確恢復並繼續分配 VB，且所有相關 VB 指標持續遞增，無狀態丟失。
3. **WB Flush 觸發 TLC GC**：確認透過寫入填满 Write Booster Buffer 並設定 `WRITEBOOSTER_BUFFER_FLUSH_EN` 旗標，會強制觸發 TLC 層級的 Defrag GC，導致 Open VB 資訊中出現特定的 GC 相關欄位（如 `open_logical_VB_number_for_Normal_Defrag_GC_Open_VB_TLC`）。
4. **EM1 寫入觸發 EM1 GC**：確認透過調整 LUN 配置為 EM1 模式並寫入至超過 SLC Threshold，會觸發 EM1 層級的 GC，導致 Open VB 資訊中出現 EM1 特定的 GC 欄位（如 `open_logical_VB_number_for_EM1_GC`）。

## Test Case (TC) Checkpoints

1. [TC01_LUN_Config_and_RPMB_Init]：
   - 動作：呼叫 `config_lun` 配置 LUN 0 (Normal), LUN 1 (EM1), LUN 3 (WB)，設定 EM1 的 Allocation Unit 數量，並啟用 RPMB Region 0。執行 `rpmb_key_programming` 確保 RPMB 金鑰已寫入。
   - 預期結果：LUN 配置成功，LUN 0/1/3 處於 ENABLE 狀態，RPMB 寫入計數器 (Write Counter) 可正常讀取，無 `SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 異常。

2. [TC02_Initial_Write_and_OpenVB_Allocation]：
   - 動作：
     1. 呼叫 `get_and_print_open_vb_information` 取得初始狀態 `open_vb_information_original`。
     2. 對 LUN 0 (Normal) 寫入 1MB 資料 (LBA 0-255)。
     3. 對 LUN 1 (EM1) 寫入 1MB 資料 (LBA 0-255)。
     4. 對 RPMB 寫入 4KB 資料。
     5. 設定 Flag `WRITEBOOSTER_EN` 為 True，`WRITEBOOSTER_BUFFER_FLUSH_EN` 為 False。
     6. 對 LUN 3 (WB) 寫入 1MB 資料 (LBA 0-255)。
     7. 再次取得 Open VB 資訊 `open_vb_information_before`。
   - 預期結果：
     - `open_vb_information_before` 中所有預設欄位（包含 `L2_Open_logical_VB_Host_TLC_number`, `first_free_physical_page_of_Write_Booster_WB_L2`, `List_block_First_free_physical_page` 等）的值均不等於 0xFFFFFFFF。
     - 與 `open_vb_information_original` 相比，`first_free_physical_page_of_L2_Open_logical_VB_Host_TLC`、`first_free_physical_page_of_Write_Booster_WB_L2`、`first_free_physical_page_of_SWAP_RAIN_TLC` 等指標數值嚴格遞增。

3. [TC03_SSU_Power_Cycle_Stability]：
   - 動作：
     1. 呼叫 `ssu_sleep_and_active` 執行 SSU Sleep (Power Condition 0x02) 後緊接著 Active (Power Condition 0x01)。
     2. 等待設備恢復後，再次取得 Open VB 資訊 `open_vb_information_before` (此處代碼邏輯為重複獲取，實際驗證點在於 SSU 後的狀態一致性)。
     3. 驗證 `open_vb_information_before` 的預設欄位存在性。
     4. 驗證關鍵指標（`first_free_physical_page_of_L2_Open_logical_VB_Host_TLC`, `first_free_physical_page_of_Write_Booster_WB_L2`, `first_free_physical_page_of_SWAP_RAIN_TLC`, `first_free_physical_page_of_SWAP_RAIN_WB`, `List_block_First_free_physical_page`, `LOG_Block_First_free_physical_page`）相寫入前嚴格遞增。
   - 預期結果：SSU 電源循環未導致 VB 狀態重置或損壞，所有物理頁指標持續增長，代表韌體在電源管理狀態切換下正確維護了 Open VB 的元數據。

4. [TC04_Continued_Write_and_Pre_GC_Check]：
   - 動作：
     1. 清除 Flag `WRITEBOOSTER_EN`。
     2. 對 LUN 0 (Normal) 寫入 1MB 資料 (LBA 256-511)。
     3. 對 LUN 1 (EM1) 寫入 1MB 資料 (LBA 256-511)。
     4. 對 RPMB 寫入 4KB 資料 (LBA 1-2)。
     5. 設定 Flag `WRITEBOOSTER_EN` 為 True。
     6. 對 LUN 3 (WB) 寫入 1MB 資料 (LBA 256-511)。
     7. 執行 SSU Sleep/Active。
     8. 取得 Open VB 資訊 `open_vb_information_after`。
   - 預期結果：
     - `open_vb_information_after` 中新增的欄位（如 `first_free_physical_page_of_EM1_L2_Host_VB`, `start_physical_page_of_VB_of_TMP_RAIN_VB_SSU_VB`, `first_free_physical_page_of_RPMB_VB`, `first_free_physical_page_of_SWAP_RAIN_EM1`, `PTE_block_First_free_physical_page`）均存在且不等於 0xFFFFFFFF。
     - 所有物理頁指標（包含 L2, EM1, WB, Swap, List, LOG, PTE）相 `open_vb_information_before` 嚴格遞增。

5. [TC05_WB_Flush_Trigger_TLC_GC]：
   - 動作：
     1. 設定 Flag `WRITEBOOSTER_EN` 為 True。
     2. 進入迴圈，以 `chunk_size=64MB` 對 LUN 0 進行連續寫入，每次寫入 `tlc_vb_size` 大小的資料，直到 `api.read_attribute(AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)` 返回值不等於 0xA (表示 Buffer 已滿或狀態改變)。
     3. 取得寫入前的 Open VB 資訊 `open_vb_information`。
     4. 呼叫 `issue_D0FD_en_disable_BKOPS(0x00)` 暫停背景操作。
     5. 設定 Flag `WRITEBOOSTER_BUFFER_FLUSH_EN` 為 True，強制 WB 資料刷入 Flash。
     6. 取得寫入後的 Open VB 資訊 `open_vb_information_TLC_GC`。
     7. 呼叫 `issue_D0FD_en_disable_BKOPS(0x01)` 恢復背景操作並輪詢至 BKOPS Idle。
   - 預期結果：
     - `open_vb_information_TLC_GC` 中必須存在以下三個特定欄位且值不等於 0xFFFFFFFF：
       - `open_logical_VB_number_for_Normal_Defrag_GC_Open_VB_TLC`
       - `first_free_physical_page_for_Normal_Defrag_VB_GC_Open_VB_TLC`
       - `open_Remap_VB_number_for_GC_Open_VB_TLC`
     - 這證明 WB Buffer 滿載並 Flush 後，觸發了 TLC 層級的 Defragmentation GC 流程。

6. [TC06_EM1_Write_Trigger_EM1_GC]：
   - 動作：
     1. 重新配置 LUN，僅啟用 LUN 1 為 EM1 類型，並設定 `slc_au` 為 `SLC_VB_AU_SIZE * 20`。
     2. 取得當前 SLC 和 TLC 的 GC Threshold (`api.get_gc_threshold()`)。
     3. 呼叫 `issue_D0FD_en_disable_BKOPS(0x02)` 暫停背景操作。
     4. 呼叫 `write_until_threshold` 對 LUN 1 進行寫入，直到 `USED_BLK_POOL_EM1` 的 VB 數量達到 SLC Threshold。
     5. 取得 Open VB 資訊 `open_vb_information_EM1`。
     6. 呼叫 `issue_D0FD_en_disable_BKOPS(0x03)` 恢復背景操作並輪詢至 BKOPS Idle。
   - 預期結果：
     - `open_vb_information_EM1` 中必須存在以下三個特定欄位且值不等於 0xFFFFFFFF：
       - `open_logical_VB_number_for_EM1_GC`
       - `first_free_physical_page_of_EM1_GC_VB`
       - `open_Remap_VB_number_for_EM1_GC`
     - 這證明當 EM1 LUN 的已用 VB 數量超過 SLC Threshold 時，觸發了 EM1 專屬的 GC 流程。