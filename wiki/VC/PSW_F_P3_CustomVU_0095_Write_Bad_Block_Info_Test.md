# Test Spec: UFS Vendor Command 40C7/C0BC/405E Bad Block Table (BBT) Injection and Early Pool Verification

## Verification Criterion (VC)
驗證 UFS 韌體透過 Vendor Command (VC) 處理自定義 Bad Block Table (BBT) 的寫入與讀取一致性，以及 Early Pool 計數器的同步機制：
1. **數據結構完整性**：確認 VC `0xC0BC` 能正確解析並寫入由 CE (Chip Enable)、Plane 和 Block 組成的複合位元組格式數據，且該數據在內部 BBT 結構中保持邏輯一致性。
2. **BBT 寫入有效性**：確認寫入的隨機 Bad Block 資訊確實被韌體接收並更新至內部 BBT 表，導致讀回 (via VC `0x405E`) 的 BB 數量嚴格等於「初始 BB 數 + 注入數量」，且注入的 (CE, Plane, Block) 三元組必須完整存在於讀回的 BBT 數據中。
3. **Early Pool 計數同步**：確認每成功注入一個 Bad Block，韌體對應的 Early Pool Physical VB Count (via VC `0x40C7`) 必須精確增加 1，驗證韌體在標記 Bad Block 時正確更新了保留區塊的計數器。

## Test Case (TC) Checkpoints
1. [Case01_BBT_Initial_State_Record]：
   - 動作：透過 VC `0x40C7` 讀取初始的 Early Pool Physical VB Count 並記錄為 `early_pool_physical_VB_count`；透過 VC `0x405E` 讀取初始 BBT 數據，解析前 4 位元組得到初始 BB 數量 `BB_count`，並解析後續每 8 位元組的數據（Block 佔 3 bytes, CE/Plane 佔 1 byte 經位移運算）重建初始 BBT 集合 `bbt_set`。
   - 預期結果：成功獲取初始狀態數據，`BB_count` 為當前系統已知的 Bad Block 總數，`bbt_set` 包含所有現有的 (CE, Plane, Block) 組合。

2. [Case02_Random_BB_Generation_and_Filtering]：
   - 動作：根據 `flash_setting` 中的 `Max_Fdevice` (CE 數量)、`Plane_Per_Die` (Plane 數量) 和 `Max_PB` (每平面最大 Block 數)，隨機生成 5 到 10 組新的 (CE, Plane, Block) 資訊存入 `info_list`；過濾掉那些已經存在於初始 `bbt_set` 中的重複項，確保注入的 Bad Block 是全新的，並計算最終待注入的數量 `len(info_list)`。
   - 預期結果：`info_list` 中的所有元素均為未出現在初始 BBT 中的唯一 Bad Block 位置，且數量在 5-10 之間。

3. [Case03_Vendor_Command_C0BC_Write]：
   - 動作：將過濾後的 `info_list` 透過 `transfer` 函數轉換為符合韌體規格的 `bytearray` 格式（每個 CE 組前加入 `0xFFF0 + CE` 標記，Block 與 Plane 合併為 16-bit 整數 `((Block & 0x1FFF) << 3) | (Plane & 0x07)`，並填充至 0x4000 長度），隨後透過 Vendor Command `0xC0BC` 將此數據寫入控制器。
   - 預期結果：VC `0xC0BC` 執行成功，無異常拋出，韌體內部 BBT 結構已根據傳入的 byte 數據進行更新。

4. [Case04_BBT_Data_Integrity_Verification]：
   - 動作：再次透過 VC `0x405E` 讀取更新後的 BBT 數據，解析得到新的 BB 數量 `BB_count_new` 和新的 BBT 集合 `bbt_set_new`；檢查 `BB_count_new` 是否等於 `BB_count + len(info_list)`；檢查 `info_set` (待注入集合) 是否為 `bbt_set_new` 的子集。
   - 預期結果：`BB_count_new` 必須精確等於初始數量加上注入數量；所有注入的 (CE, Plane, Block) 三元組必須在 `bbt_set_new` 中找到完全匹配，證明數據寫入與解析邏輯正確無誤。

5. [Case05_Early_Pool_Count_Synchronization]：
   - 動作：透過 VC `0x40C7` 讀取更新後的 Early Pool Physical VB Count `early_pool_physical_VB_count_new`；比較其與初始值 `early_pool_physical_VB_count` 的差異。
   - 預期結果：`early_pool_physical_VB_count_new` 必須精確等於 `early_pool_physical_VB_count + len(info_list)`，證明每標記一個 Bad Block，Early Pool 的物理 VB 計數器均正確遞增，無計數遺漏或重複。