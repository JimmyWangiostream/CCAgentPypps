# Test Spec: UFS FTL Geometry & FwConfiguration Consistency Verification

## Verification Criterion (VC)
驗證 UFS 韌體內部 FTL (Flash Translation Layer) 幾何結構變數與透過 Vendor Command (0x408A) 獲取的韌體配置結構 (`GetFwConfiguration`) 之間的數據一致性。此測試旨在確認韌體啟動時讀取的硬體參數（如 Die 數量、Channel 數量、Block/Page 幾何、Pool 分配邏輯）與韌體內部定義的配置表完全吻合，確保無硬體識別錯誤或韌體配置衝突。具體檢查點涵蓋：
1. **硬體幾何一致性**：Die 數、Channel 數、Block/Page 數、Superlock 結構、ECC/Metadata Spare 大小。
2. **邏輯地址空間分配一致性**：Host Data、Static Pool、Dynamic Pool、Table VB 的起始邏輯 VB 號碼與 BBT (Bad Block Table) 狀態及 Head Size 的關聯性。
3. **壞塊管理一致性**：最大早期壞塊計數 (Max GBB Count) 與實際擦除計數表的一致性。

## Test Case (TC) Checkpoints
1. [FTL_Geometry_and_Config_Match_Check]：
   - 動作：
     1. 透過 `read_fw_value` 從韌體記憶體讀取 FTL 核心幾何參數：`total_fvl`, `physical_ch_cnt`, `block_per_plane`, `physical_plane_per_vb`, `d2_page_per_block` (TLC Pages), `d1_page_per_block` (SLC Pages), `total_vb`, `lc_per_page`, `bbtmax_revoke_cnt`, `last_tbl_pool_vb`, `last_slc_pool_vb`, `head_size`。
     2. 呼叫 `get_later_bad_cnt` 讀取壞塊擦除計數表 (Bad Block Erase Count Table) 的特定欄位 (Bytes 2-3, Big Endian) 作為 `latter_bad_cnt`。
     3. 透過 Vendor Command 0x408A (`issue_408A_to_get_fw_version`) 獲取韌體配置結構 `fw_configuration`。
     4. 透過 `get_flash_setting` 獲取硬體偵測到的 `ce_num` (Max_Fdevice)。
     5. 執行以下嚴格比對：
        - `fw_configuration.NumberOfTotalDie` == `ce_num`
        - `fw_configuration.NumberOfChannels` == `physical_ch_cnt`
        - `fw_configuration.NumberOfBlocksPerPlane` == `block_per_plane`
        - `fw_configuration.NumberOfPagesPerTlcBlock` == `d2_page_per_block`
        - `fw_configuration.NumberOfPagesPerSlcBlock` == `d1_page_per_block`
        - `fw_configuration.SizeOfPhysicalPage` == 18352 (Bytes)
        - `fw_configuration.SizeOfPhysicalAddressUnit` == 16384 (Bytes)
        - `fw_configuration.NumberOfBlocksInSuperlock` == `physical_plane_per_vb`
        - `fw_configuration.CountOfAllSuperlocks` == `total_vb`
        - `fw_configuration.VPCountPerPhysicalPage` == `lc_per_page`
        - `fw_configuration.MetadataSpareSizePerKB` == 16
        - `fw_configuration.ECCSpareSizePerKB` == 456
        - `fw_configuration.DMMaximumReplacedBlockCountForBBRemapPerPlane` == `bbtmax_revoke_cnt`
        - `fw_configuration.FirstLogicalVBNumberForHostData` == `last_tbl_pool_vb + 1`
        - `fw_configuration.TheFirstLogVBOfStaticPool` == `last_tbl_pool_vb + 1`
        - `fw_configuration.TheFirstLogVBOfDynamicPool` == `last_slc_pool_vb + 1`
        - `fw_configuration.TheFirstLogVBOfTableVB` == `head_size`
        - `fw_configuration.MaxGBBCount` == `latter_bad_cnt`
   - 預期結果：所有上述比對條件必須全部為 True。若任一條件不符，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。這代表韌體對硬體幾何的認知、邏輯區塊池的分配策略（Table Pool 結束後緊接 Host/Static Pool，SLC Pool 結束後緊接 Dynamic Pool）、以及壞塊管理閾值均與實際硬體狀態及韌體內部配置表完全同步。