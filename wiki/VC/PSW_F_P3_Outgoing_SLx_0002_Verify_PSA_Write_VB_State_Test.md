# Test Spec: UFS LUN Memory Type & PSA State Transition Verification

## Verification Criterion (VC)
驗證 UFS 裝置在配置不同 Memory Type (Normal vs Enhanced_1) 的 LUN 後，韌體內部 VB (Virtual Block) 的 Trim 狀態分佈是否符合預期，並確認 PSA (Pre-Soldering Area) 寫入流程在 HW_RESET 後能正確保留並恢復系統狀態：
1. **初始狀態驗證**：在配置 LUN 0 (Normal) 和 LUN 1 (Enhanced_1) 後，未進行寫入前，VB Group 的 Trim 狀態應全部分佈於 `SLx_TRIM` (SLx 保留區) 和 `POR_TRIM` (上電預設狀態)，且無其他異常狀態。
2. **PSA 寫入與重置驗證**：配置 LUN 3 (Normal) 為 PSA 區，寫入指定大小資料並標記為 `LOADING_COMPLETE`，執行 HW_RESET 後，系統應能正確恢復。
3. **Enhanced_1 LUN 寫入後驗證**：在 HW_RESET 後，對 LUN 1 (Enhanced_1) 進行全容量寫入，驗證其觸發的 VB 狀態遷移。預期結果為：`SLx_TRIM` 集合中必須包含 `FREE_BLK_QUEUE_SLC` 和 `FREE_BLK_QUEUE_MLC`；`POR_TRIM` 集合中必須包含 `CURRENT_L1` 和 `CURRENT_L2_SLC`。這代表 Enhanced_1 的寫入操作正確地將相關 VB Group 標記為當前使用狀態 (Current) 且符合 SLC/MLC 的層級定義。

## Test Case (TC) Checkpoints

1. [LUN_Config_and_Initial_VB_State_Check]：
   - 動作：
     1. 執行 `set_LUN_configuration`：
        - 配置 LUN 0 (TestNormalLun)：Memory Type 設為 `NORMAL`，Alloc Units 設為 8192，Thin Provisioning。
        - 配置 LUN 1 (TestEM1Lun)：Memory Type 設為 `ENHANCED_1`，Alloc Units 設為 2000，Thin Provisioning。
        - 配置 LUN 3 (TestPSALun)：Memory Type 設為 `NORMAL`，Alloc Units 設為 8192，Thin Provisioning。
        - 其他 LUN 禁用。
     2. 執行 `get_vb_trim_set` 讀取所有 VB 的 `vb_trim` 欄位（解析 `vb_info.bin` 中的 bit 16-17）。
     3. 檢查 `slx_trim_set` 是否包含 `{VB_GROUP_TYPE.FREE_BLK_QUEUE_SLC, VB_GROUP_TYPE.FREE_BLK_QUEUE_MLC}`。
     4. 檢查 `por_trim_set` 是否包含 `{VB_GROUP_TYPE.CURRENT_L2_MLC, VB_GROUP_TYPE.CURRENT_L1}`。
   - 預期結果：
     - `slx_trim_set` 必須包含 `FREE_BLK_QUEUE_SLC` 和 `FREE_BLK_QUEUE_MLC`。
     - `por_trim_set` 必須包含 `CURRENT_L2_MLC` 和 `CURRENT_L1`。
     - 若任一集合檢查失敗，觸發 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`。這確認了 LUN 配置生效後，VB 管理器的初始狀態機處於預期的空閒/預設分佈。

2. [PSA_Write_and_HW_Reset_Preservation_Check]：
   - 動作：
     1. 讀取 Device Descriptor 中的 `l37_psa_max_data_size`。
     2. 寫入 Attribute `PSA_DATA_SIZE` 為該最大值。
     3. 寫入 Attribute `PSA_STATE` 為 `PRE_SOLDERING`。
     4. 對 LUN 3 (TestPSALun) 執行 `sequential_write`：從 LBA 0 開始，寫入大小等於 `slc_vb_size` (由 FW Geometry 計算) 的資料，Chunk Size 為 128MB，FUA=0，使用 HW Compare。
     5. 寫入 Attribute `PSA_STATE` 為 `LOADING_COMPLETE`。
     6. 執行 `HW_RESET` (Dcmd5ResetType.HW_RESET) 並等待 Unit Ready。
   - 預期結果：
     - PSA 資料必須成功寫入 LUN 3。
     - HW_RESET 後，韌體必須識別 PSA 狀態為 `LOADING_COMPLETE`，確保 PSA 區資料在重啟後不被清除或覆蓋，且 LUN 配置保持不變。

3. [EM1_Write_and_Post_Reset_VB_State_Transition_Check]：
   - 動作：
     1. 在 HW_RESET 完成後，對 LUN 1 (TestEM1Lun, Enhanced_1) 執行 `sequential_write`：從 LBA 0 開始，寫入 1MB 資料 (128MB chunk)，FUA=0，使用 HW Compare。
     2. 再次執行 `get_vb_trim_set` 讀取所有 VB 的 `vb_trim` 欄位。
     3. 檢查 `slx_trim_set` 是否包含 `{VB_GROUP_TYPE.FREE_BLK_QUEUE_SLC, VB_GROUP_TYPE.FREE_BLK_QUEUE_MLC}`。
     4. 檢查 `por_trim_set` 是否包含 `{VB_GROUP_TYPE.CURRENT_L1, VB_GROUP_TYPE.CURRENT_L2_SLC}`。
   - 預期結果：
     - `slx_trim_set` 必須包含 `FREE_BLK_QUEUE_SLC` 和 `FREE_BLK_QUEUE_MLC`。
     - `por_trim_set` 必須包含 `CURRENT_L1` 和 `CURRENT_L2_SLC`。
     - 這驗證了對 Enhanced_1 LUN 的寫入操作，正確地觸發了韌體將對應的 VB Group 標記為 `CURRENT_L1` 和 `CURRENT_L2_SLC` (在 POR_TRIM 集合中)，同時保持 SLC/MLC 隊列在 SLx_TRIM 集合中，符合 Enhanced_1 的內部區塊管理邏輯。