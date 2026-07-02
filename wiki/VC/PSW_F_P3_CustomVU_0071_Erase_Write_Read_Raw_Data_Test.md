# Test Spec: UFS Direct I/O Raw Data Integrity & State Transition Verification

## Verification Criterion (VC)
驗證 UFS 韌體在直接操作物理層（Direct I/O）時的資料完整性與區塊狀態機轉換邏輯：
1. **初始狀態驗證**：確認 LUN 0 (Normal/TLC) 與 LUN 1 (Enhanced 1/SLC) 在寫入後，其對應物理頁面的 Header 狀態欄位（Payload 0x4000-0x4003）為 `0x00000000` (Normal)，且資料區可讀。
2. **Erase 狀態驗證**：確認執行 Vendor Command `D060` 對特定物理區塊進行 Erase 後，該區塊所有頁面的 Header 狀態欄位必須變更為 `0x01010101` (Empty)，代表區塊已清除且準備接受寫入。
3. **Raw Write 完整性驗證**：確認執行 Vendor Command `C060` 寫入全 `0xAA` 資料後，韌體正確處理 TLC (3 Pages/Block) 與 SLC (1 Page/Block) 的頁面數量差異，且讀回之 Payload 資料區（0x0000-0x3FFF）必須與寫入資料完全一致，Header 狀態恢復為 `0x00000000` (Normal)。

## Test Case (TC) Checkpoints

1. [LUN_Configuration_and_Physical_Address_Mapping]：
   - 動作：透過 `WriteDescriptor` 配置 LUN 0 為 `MemoryType.NORMAL` (TLC 模式) 並分配 `normal_total_AU` 個 Allocation Units；配置 LUN 1 為 `MemoryType.ENHANCED_1` (SLC 模式) 並分配 `EM1_total_AU` 個 Allocation Units。隨後對 LUN 0 寫入 `tlc_vb_size` 大小的資料，對 LUN 1 寫入 `slc_vb_size` 大小的資料。使用 `issue_4051` 分別取得 LUN 0 隨機 LBA 對應的 `tlc_pca` 與 LUN 1 隨機 LBA 對應的 `slc_pca` 物理地址資訊（包含 Die, Plane, Block, Page, Virtual Block Number）。
   - 預期結果：LUN 0 與 LUN 1 成功啟用；`tlc_pca` 與 `slc_pca` 成功獲取有效的物理地址結構，且 `Virtual Block Number` 不為零，代表邏輯區塊已正確映射至物理閃存單元。

2. [Pre_Write_Normal_State_Check]：
   - 動作：針對 `tlc_pca` 與 `slc_pca` 所指向的物理位置（Die, Plane, Block, Page），透過 `issue_40C7` 查詢 Bad Block 資訊以獲取實際使用的 `RemapPB`（若無替換則為原 Block）。接著使用 Vendor Command `4060` 讀取該頁面的原始資料（Raw Data）。檢查讀回 Payload 的 0x4000 到 0x4004 欄位。
   - 預期結果：Payload[0x4000:0x4004] 的數值必須等於 `0x00000000`。這代表該物理頁面目前處於 "Normal" 狀態，且韌體尚未標記為 Empty 或 Error，確認寫入操作後的初始狀態正確。

3. [Erase_State_Transition_Check]：
   - 動作：針對上述確定的 `RemapPB`，執行 Vendor Command `D060` 進行物理區塊 Erase 操作。Erase 完成後，再次使用 `issue_4060` 讀取同一頁面的原始資料。檢查讀回 Payload 的 0x4000 到 0x4004 欄位。
   - 預期結果：Payload[0x4000:0x4004] 的數值必須等於 `0x01010101`。這代表該物理頁面已進入 "Empty" 狀態，韌體已正確更新區塊狀態標記，準備接受新的資料寫入。

4. [Raw_Write_Integrity_and_Page_Count_Verification]：
   - 動作：
     1. 根據 `SlcEnable` 標誌準備寫入資料：若為 SLC (LUN 1)，準備 `DATA_SIZE_16K_BYTE` 長度的全 `0xAA` 資料；若為 TLC (LUN 0)，準備 `DATA_SIZE_20K_BYTE * 3` 長度的全 `0xAA` 資料。
     2. 執行 Vendor Command `C060` 將上述資料寫入對應的 Die, Plane, Block, Page。
     3. 根據模式決定讀取頁面數量：SLC 讀取 1 頁，TLC 讀取 3 頁。
     4. 對每一頁執行 `issue_4060` 讀取原始資料。
     5. 檢查每頁的 Payload[0x4000:0x4004] 是否為 `0x00000000`。
     6. 檢查每頁的 Payload[0x0000:0x4000] 資料區是否與對應的 `0xAA` 寫入資料片段完全一致。
   - 預期結果：
     1. 所有讀回頁面的 Header 狀態欄位 [0x4000:0x4004] 必須為 `0x00000000` (Normal)，代表寫入成功且狀態已更新。
     2. 所有讀回頁面的資料區 [0x0000:0x4000] 必須完全等於 `0xAA` 填充的資料，無任何比特翻轉或資料損壞。
     3. 此步驟同時驗證了韌體對 SLC (1 Page) 與 TLC (3 Pages) 不同頁面結構的 Direct I/O 處理邏輯正確性。