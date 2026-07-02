# Test Spec: UFS L2P Mapping Consistency & PTE/PMD Data Integrity Verification

## Verification Criterion (VC)
驗證 UFS 韌體在正常寫入流程後，Host 端透過 Phison Vendor Command (VU 0x91/0x92) 與 Micron Vendor Command (VU 0x4051/0x4052) 取得的邏輯到物理位址轉換 (L2P) 資訊必須完全一致，且 PTE (Page Table Entry) 與 PMD (Page Map Data) 的內部資料結構必須與直接讀取 (Direct Read) 的 Flash 原始資料相符。此測試涵蓋所有 LUN (含 Boot LUN A/B 及 Normal LUN)，確認韌體在 Thin Provisioning 配置下，LBA 到 PBA (包含 Die, Plane, Block, Page, Offset) 的映射邏輯無誤，且 PTE/PMD 的 Virtual Block Number (VB Number) 非 0xFFFFFFFF 時，其對應的韌體內部表結構與 Flash 實際儲存的映射資料具備 1:1 的數據一致性。

## Test Case (TC) Checkpoints
1. [LUN_Configuration_and_Write_Init]：
   - 動作：透過 `push_write_config` 配置所有 LUN (最多 32 個)，設定 Memory Type 為 NORMAL (LUN 1, 2, 3 設為 ENHANCED_1 作為 Boot LUN A/B/C)，啟用 Thin Provisioning 與 4KB Logical Block Size。隨後針對每個 LUN 執行 Sequence Write (寫入 16MB 或 LUN 容量)，並隨機選取一個 LBA 進行後續驗證。
   - 預期結果：所有 LUN 配置成功寫入 Configuration Descriptor；寫入操作完成後，Flash 內部映射表 (L2P) 已更新，且針對選取的 LBA 存在有效的物理位址映射。

2. [L2P_PBA_Consistency_Check_Phison_vs_Micron]：
   - 動作：針對選定的 LBA，分別呼叫 Phison VU (`lba_to_pca`) 與 Micron VU 4051 (`issue_4051_to_get_physical_address`) 獲取 PBA 資訊。比對兩者返回的 `L2P_PCA` 與 `physical_address_info` 結構體，檢查項目包含：CE (Die) 編號、Plane 編號、Virtual Block Number、Physical Block Number (無 BBT)、Page Number (需經 `wl_page_2_physical_page` 轉換為實際物理 Page) 以及 Page Offset。
   - 預期結果：Phison 與 Micron 返回的 CE、Plane、Block、Page、Offset 數值必須完全相等。特別注意 Page 數值需考慮 Access Mode 1 或 2 的邏輯頁到物理頁轉換邏輯，確保韌體內部 L2P 查詢結果與 Vendor Command 解析結果一致。

3. [PTE_Data_Integrity_Verification]：
   - 動作：若 Micron VU 返回的 `PPT_virtual_block_number` 不等於 `0xFFFFFFFF` (代表該 LBA 有有效映射)，則執行以下檢查：
     1. 使用 Phison VU 返回的 LCA (Logical Chunk Address) 除以 1024 作為索引，呼叫 `load_PTE_data` 讀取韌體記憶體中的 PTE 結構資料。
     2. 根據 Micron VU 返回的 PBA 資訊，構建 `PCA` 結構體 (設定 Mode=1, CE, Plane, Block, Page, Offset)，呼叫 `direct_read` 直接從 Flash 讀取該 PTE 所在的物理區塊資料。
     3. 比對 `load_PTE_data` 的結果與 `direct_read` 的結果。
   - 預期結果：韌體記憶體中的 PTE 結構資料必須與直接從 Flash 讀取的原始資料完全一致。這驗證了 PTE 表在韌體緩衝區與 Flash 實際儲存之間沒有數據損壞或同步錯誤。

4. [PMD_Data_Integrity_Verification]：
   - 動作：若 Micron VU 返回的 `PPT2_virtual_block_number` 不等於 `0xFFFFFFFF` (代表該 LBA 有有效映射)，則執行以下檢查：
     1. 使用 LUN 和 LBA 呼叫 `load_PMD_data` 讀取韌體記憶體中的 PMD 結構資料。
     2. 根據 Micron VU 返回的 PBA 資訊 (使用 PPT2 相關欄位)，構建 `PCA` 結構體 (設定 Mode=1, CE, Plane, Block, Page, Offset)，呼叫 `direct_read` 直接從 Flash 讀取該 PMD 所在的物理區塊資料。
     3. 比對 `load_PMD_data` 的結果與 `direct_read` 的結果。
   - 預期結果：韌體記憶體中的 PMD 結構資料必須與直接從 Flash 讀取的原始資料完全一致。這驗證了 PMD 表在韌體緩衝區與 Flash 實際儲存之間沒有數據損壞或同步錯誤。

5. [LBA_Reverse_Mapping_Check]：
   - 動作：使用 Micron VU 4052 (`issue_4052_to_get_logical_address`)，傳入步驟 2 中獲得的 Die, Plane, Physical Block, Page, Offset 資訊，反向查詢邏輯位址。
   - 預期結果：反向查詢返回的 LUN 與 LBA 必須與測試開始時隨機選取的 LUN 與 LBA 完全一致。這驗證了 L2P 映射表的雙向查詢邏輯正確，無映射衝突或遺漏。