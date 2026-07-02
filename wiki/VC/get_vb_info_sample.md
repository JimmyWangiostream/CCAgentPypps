# Test Spec: VB Info API Diagnostic & State Verification

## Verification Criterion (VC)
驗證 `project_api.create_get_vb_info()` 介面在 `access_vendor=False` 模式下，對 UFS 韌體中 VB (Version Block) 核心狀態機與儲存結構的讀取正確性與完整性：Case 01 確認 VB Group 邏輯分組識別碼（Group ID）的硬體映射正確；Case 02 確認有效 VB 計數器（Valid Count）與實際寫入狀態一致；Case 03 確認 VB Remap 表（Remap Table）是否正確反映當前 VB 的邏輯到物理映射關係；Case 04 確認特定 VB Group（如 `USED_BLK_POOL_MLC`）的大小配置與韌體定義相符；Case 05 確認 `show` 與 `dumpfile` 函數能正確過濾無效 VB 並輸出完整二進制/文本狀態，確保韌體內部 VB 結構無損壞且可被外部腳本正確解析。

## Test Case (TC) Checkpoints
1. [Case01_VB_Group_ID_Check]：
   - 動作：初始化 `vb_info_api` 並呼叫 `get_info()` 取得 VB 資訊結構體，讀取索引為 0 的 VB 物件之 `group` 欄位值，並透過 logger 輸出該值。
   - 預期結果：`vb_info[0].group.value` 必須返回預期的 VB Group 識別碼（例如代表 MLC 或 TLC 池的特定枚舉值），確認韌體能正確識別當前 VB 所屬的硬體儲存分區組別，無記憶體越界或結構解析錯誤。

2. [Case02_VB_Valid_Count_Check]：
   - 動作：呼叫 `vb_info_api.get_valid_count(access_vendor=False)` 獲取 VB 的有效計數列表，讀取索引為 0 的計數值並輸出。
   - 預期結果：`valid_cnts[0]` 必須為非負整數，且數值應與該 VB 區塊內實際標記為 Valid 的 Page/LCU 數量一致，確認韌體內部 VB 狀態機中的 Valid Count 計數器未被損壞或誤算。

3. [Case03_VB_Remap_Table_Check]：
   - 動作：呼叫 `vb_info_api.get_remap_table(access_vendor=False)` 獲取 VB 的 Remap 表，讀取索引為 0 的 Remap 目標 VB 編號並輸出。
   - 預期結果：`remaps[0]` 必須返回一個有效的 VB 編號（通常為當前 VB 自身編號或指向備援 VB 的編號），確認韌體中的 VB Remap 機制（用於處理 VB 損壞時的備援切換）狀態正確，且 API 能正確讀取該硬體映射表。

4. [Case04_VB_Group_Size_Check]：
   - 動作：呼叫 `vb_info_api.get_group_size(access_vendor=False)` 獲取 VB Group 大小資訊，讀取 `project_api.VB_GROUP.USED_BLK_POOL_MLC` 對應的大小值並輸出。
   - 預期結果：`grp_sizes[project_api.VB_GROUP.USED_BLK_POOL_MLC]` 必須返回預期的區塊數量或容量值（例如 256, 512 等，依具體 HW 定義而定），確認韌體對 MLC 區塊池的 VB 分組大小配置與硬體規格書定義完全一致。

5. [Case05_VB_Dump_Filter_Check]：
   - 動作：分別呼叫 `vb_info_api.show(access_vendor=False)` 與 `vb_info_api.show(print_valid_cnt_zero_vb=False, access_vendor=False)`，並執行 `vb_info_api.dumpfile(access_vendor=False)`。
   - 預期結果：第一次 `show` 應輸出所有 VB 狀態（包含 Valid Count 為 0 的）；第二次 `show` 應僅輸出 Valid Count 大於 0 的 VB，確認過濾邏輯正確；`dumpfile` 應成功生成包含完整 VB 原始資料（Raw Data）的檔案，確認韌體能正確將內部 VB 結構序列化輸出，無 I/O 錯誤或資料截斷。