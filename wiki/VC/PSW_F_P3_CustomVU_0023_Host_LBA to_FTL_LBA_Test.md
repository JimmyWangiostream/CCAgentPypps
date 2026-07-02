# Test Spec: UFS L2P Translation Consistency Verification (Phison L2P vs Micron FTL LBA)

## Verification Criterion (VC)
驗證 UFS 裝置在 LUN 0~3 配置完成並執行順序寫入後，Phison Vendor Command (L2P) 與 Micron Vendor Command (40D4) 所回傳的邏輯區塊到物理區塊/邏輯區塊地址的轉換結果必須完全一致。具體而言，針對 LUN 0 (Normal), LUN 1 (Boot A), LUN 2 (Boot B), LUN 3 (Enhanced Normal) 分別隨機選取一個 LBA，透過 `lba_to_pba` 取得 Phison 的 LCA (Logical Chunk Address)，並透過 `issue_40D4_to_get_FTL_LBA` 取得 Micron FTL 的 LBA，兩者數值必須相等。此測試旨在確認韌體層級的 L2P 映射表與底層快閃記憶體控制器 (FTL) 的物理映射邏輯在多種 LUN 類型與記憶體類型 (Normal/Enhanced) 下保持同步，無映射偏差。

## Test Case (TC) Checkpoints
1. [LUN_Configuration_and_Write_Pattern]：
   - 動作：
     1. 讀取 Geometry Descriptor 計算 AU (Allocation Unit) 大小，並根據 `max_number_lu` (32) 與 Boot AU 大小計算 Normal LUN 的分配單元數。
     2. 透過 `push_write_config` 寫入 Config Descriptor，啟用 LUN 0~3：
        - LUN 0: `MemoryType.NORMAL`, `BootLUNID.NOT_BOOTABLE`, 容量為 `normal_au_size`。
        - LUN 1: `MemoryType.ENHANCED_1`, `BootLUNID.BOOT_LUN_A`, 容量為 `boot_au_size`。
        - LUN 2: `MemoryType.ENHANCED_1`, `BootLUNID.BOOT_LUN_B`, 容量為 `boot_au_size`。
        - LUN 3: `MemoryType.ENHANCED_1`, `BootLUNID.NOT_BOOTABLE`, 容量為 `normal_au_size`。
        - 其他 LUN 禁用。
     3. 對 LUN 0~3 分別執行 Sequence Write，寫入長度為 `min(4MB, LUN_Capacity)` 的資料，起始 LBA 為 0。
     4. 對每個 LUN (0~3)，使用 `random.randint` 隨機選取一個 LBA (範圍 0 至寫入長度)。
   - 預期結果：LUN 0~3 成功啟用並配置正確的 Memory Type 與 Boot ID；寫入操作成功完成，LBA 範圍內的所有區塊已映射至物理區塊。

2. [Phison_L2P_vs_Micron_FTL_LBA_Consistency_Check]：
   - 動作：
     1. 針對步驟 1 中隨機選取的每個 LUN 的 LBA，呼叫 `lba_to_pba(lun, lba)` 獲取 Phison Vendor Command 回傳的 `L2P_PCA` 結構，提取其中的 `l112_lca` 欄位值。
     2. 針對同一 LUN 與 LBA，呼叫 `issue_40D4_to_get_FTL_LBA(lun, lba)` 獲取 Micron Vendor Command 0x40D4 回傳的 `ftl_lba` 結構，提取其中的 `lba` 欄位值。
     3. 比對 `ftl_lba.lba.value` 與 `phison_pca.l112_lca.value`。
   - 預期結果：
     - 對於 LUN 0 (Normal): `ftl_lba.lba.value` 必須等於 `phison_pca.l112_lca.value`。
     - 對於 LUN 1 (Boot A): `ftl_lba.lba.value` 必須等於 `phison_pca.l112_lca.value`。
     - 對於 LUN 2 (Boot B): `ftl_lba.lba.value` 必須等於 `phison_pca.l112_lca.value`。
     - 對於 LUN 3 (Enhanced Normal): `ftl_lba.lba.value` 必須等於 `phison_pca.l112_lca.value`。
     - 若任何一組數值不相等，觸發 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH` 異常，並記錄錯誤資訊顯示 Expected LBA (Phison LCA) 與 Actual LBA (Micron FTL LBA) 的差異。