# Test Spec: UFS VB Management & RPMB Triggered EM1 LUN Activation Test

## Verification Criterion (VC)
驗證 UFS 韌體在 RPMB (Replay Protected Memory Block) 金鑰寫入與資料寫入後，對 Virtual Block (VB) 狀態機與 LUN 配置的影響：
1. **初始狀態驗證**：確認系統上電後，所有 VB 均處於 `FREE` 狀態且為 `SLx_TRIM`（可擦除），無 `POR_TRIM`（上電保留）標記。
2. **RPMB 觸發機制驗證**：確認執行 `RPMB Key Programming` 與 `RPMB Write Data` 後，韌體自動將相關的 SLC VB 組別從 `FREE` 轉換為 `CURRENT_L2_SLC`（EM1 開啟狀態），並驗證此狀態變更是否與後續 EM1 LUN 的寫入行為產生關聯。
3. **LUN 配置與 VB 映射驗證**：確認透過 Configuration Descriptor 正確配置 LUN 0 (Normal), LUN 1 (EM1), LUN 3 (WB) 的 Alloc Units 與 Memory Type，並驗證在 EM1 LUN 執行 Sequential Write 後，對應的 SLC VB 索引（Index）與 RPMB 寫入時鎖定的 VB 索引完全一致，證明 RPMB 寫入操作預先佔用或觸發了 EM1 LUN 所需的 SLC 資源。

## Test Case (TC) Checkpoints

1. [Case01_Initial_Free_VB_State_Check]：
   - 動作：執行 `pre_process` 初始化硬體連結與幾何描述，呼叫 `get_vb_trim_set` 讀取所有 VB 的 `vb_trim` 欄位（透過 Vendor Command `get_vb_info` 解析 payload 的 bit 16-17），並檢查 `slx_trim_set` 與 `por_trim_set`。
   - 預期結果：`slx_trim_set` 必須包含 `{VB_GROUP_TYPE.FREE_BLK_QUEUE_SLC, VB_GROUP_TYPE.FREE_BLK_QUEUE_MLC}`；`por_trim_set` 必須包含 `{VB_GROUP_TYPE.LIST_BLK, VB_GROUP_TYPE.LIST_INDEX_BLK, VB_GROUP_TYPE.TMP_CODE_BLK, VB_GROUP_TYPE.LOG_TAB_BLK}` 且**不包含**任何 FREE 區塊組別。這代表系統初始時所有可用 VB 均為可擦除狀態，且系統保留區塊已正確標記為 POR_TRIM。

2. [Case02_RPMB_Write_Trigger_EM1_Open_VB]：
   - 動作：執行 `rpmb_key_programming`（若未寫入則先寫入金鑰），接著執行 `rpmb.rpmb_write_data(0, BLOCK256B_SIZE_4K_BYTE)` 向 RPMB Region 0 寫入 4KB 資料。寫入後再次呼叫 `get_vb_trim_set` 檢查 VB 狀態變化。
   - 預期結果：`slx_trim_set` 必須**排除** `{VB_GROUP_TYPE.FREE_BLK_QUEUE_MLC}`（表示 MLC 自由區塊未變，或僅 SLC 變化）；`por_trim_set` 必須**包含** `{VB_GROUP_TYPE.CURRENT_L2_SLC}`。這驗證了 RPMB 寫入操作觸發了韌體將 SLC 區塊標記為 `CURRENT_L2_SLC`（即 EM1 開啟狀態），這是 EM1 LUN 運作的必要前置條件。

3. [Case03_LUN_Configuration_Validation]：
   - 動作：透過 `set_LUN_configuration` 修改 Configuration Descriptor：
     - LUN 0 (Index 0, Unit 0): `MemoryType.NORMAL`, `NumAllocUnits=8192`。
     - LUN 1 (Index 0, Unit 1): `MemoryType.ENHANCED_1`, `NumAllocUnits=2000`。
     - LUN 3 (Index 0, Unit 3): `MemoryType.NORMAL`, `NumAllocUnits=8192`。
     發送 `WriteDescriptor` 並對這三個 LUN 發送 `RequestSense` 確認配置生效。
   - 預期結果：韌體應接受配置，且 LUN 1 被正確識別為 Enhanced 1 類型，分配 2000 個 Allocation Units (AU)。此步驟確保後續寫入操作針對正確的硬體資源進行。

4. [Case04_Purge_All_VB_Reset]：
   - 動作：執行 `purge_all`，發送 `SetFlag(IDN=PURGE_EN)` 並輪詢 `AttributeIDN.PURGE_STATUS` 直到狀態碼為 `0x03` (Complete)。隨後再次呼叫 `get_vb_trim_set`。
   - 預期結果：`slx_trim_set` 必須**排除**所有 FREE 區塊組別（表示所有 FREE 區塊已被標記為不可用或已處理）；`por_trim_set` 必須**包含** `{VB_GROUP_TYPE.FREE_BLK_QUEUE_SLC, VB_GROUP_TYPE.FREE_BLK_QUEUE_MLC, VB_GROUP_TYPE.CURRENT_L2_MLC, VB_GROUP_TYPE.CURRENT_L1}`。這代表 Purge 操作後，所有 VB 均進入保留或特定狀態，為下一次 RPMB 觸發做準備。

5. [Case05_Second_RPMB_Write_VB_Allocation]：
   - 動作：再次執行 `rpmb_key_programming` 與 `rpmb.rpmb_write_data(0, BLOCK256B_SIZE_4K_BYTE)`。寫入後呼叫 `get_vb_index(VB_GROUP_TYPE.CURRENT_L2_SLC)` 獲取當前 SLC VB 索引，記錄為 `RPMB_write_SLC_vb_index`。
   - 預期結果：`por_trim_set` 必須包含 `{VB_GROUP_TYPE.CURRENT_L2_SLC}`。`RPMB_write_SLC_vb_index` 應返回一個有效的 VB ID，代表 RPMB 寫入操作成功佔用或標記了一個特定的 SLC VB。

6. [Case06_EM1_LUN_Sequencial_Write_VB_Mapping]：
   - 動作：對 LUN 1 (`TestEM1Lun`) 執行 `sequential_write`，寫入 1MB 資料 (`api.BLOCK4K_SIZE_1M_BYTE`)，使用 `HW_COMPARE` 模式。寫入完成後，再次呼叫 `get_vb_trim_set` 並獲取 `EM1_LUN_write_SLC_vb_index = get_vb_index(VB_GROUP_TYPE.CURRENT_L2_SLC)`。
   - 預期結果：`por_trim_set` 必須包含 `{VB_GROUP_TYPE.RAIN_SWAP_NO_OBR_SLC_L2_SLC}` 以及所有相關的 CURRENT 區塊。這驗證 EM1 LUN 寫入後，系統狀態進一步擴展至包含 RAIN Swap 相關的 SLC 區塊。

7. [Case07_VB_Index_Consistency_Check]：
   - 動作：比對步驟 5 取得的 `RPMB_write_SLC_vb_index` 與步驟 6 取得的 `EM1_LUN_write_SLC_vb_index`。
   - 預期結果：`RPMB_write_SLC_vb_index` 必須**嚴格等於** `EM1_LUN_write_SLC_vb_index`。這證實了 RPMB 的寫入操作與 EM1 LUN 的資料寫入操作共享並鎖定同一個 SLC VB 資源，驗證了韌體中 RPMB 與 EM1 LUN 之間的 VB 資源分配邏輯一致性。