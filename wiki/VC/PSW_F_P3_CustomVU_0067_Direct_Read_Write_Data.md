# Test Spec: UFS Direct NAND Mode Data Integrity Verification (SLC & TLC)

## Verification Criterion (VC)
驗證 UFS 韌體在 Direct NAND Mode（透過 Vendor Command 40F6/40F7/40F8）下，針對不同 Flash 儲存模式（SLC 與 TLC）的資料寫入與讀取完整性：
1. **SLC 模式驗證**：確認在 SLC 配置下，對指定 Die/Plane 的 Block 100 進行直接擦除與寫入後，讀回之 4KB 資料與原始 Pattern 完全一致，驗證 SLC 頁面的基礎資料路徑。
2. **TLC 模式驗證**：確認在 TLC 配置下，針對 Block 100 進行直接擦除與寫入後，讀回之資料與原始 Pattern 完全一致。特別驗證 TLC 模式下不同 Page 區域（0-1619 為 3-page 組、1620-1651 為 2-page 組、1652-3307 為 3-page 組、3308-3311 為單頁）的 Page 索引計算邏輯與資料讀取偏移量（Offset）的正確性，確保韌體能正確處理 TLC 多層單元頁面的非對稱結構。

## Test Case (TC) Checkpoints
1. [SLC_Direct_Write_Read_Integrity_Check]：
   - 動作：
     1. 初始化 Flash 設定，取得 Max_Fdevice (Die) 與 Plane_Per_Dive (Plane)。
     2. 設定測試參數：Block 範圍 100-100，使用 Pattern `0xABCDABCD`，最大頁面數 MAX_PAGE = 1103。
     3. 遍歷所有 Die 與 Plane。
     4. 對目標 Die/Plane/Block 100 發送 Vendor Command **40F6** (Direct Erase)，參數為 `mode=1` (SLC Mode)。
     5. 在頁面範圍內，以步長 10 遍歷 Page。計算當前 Page 組的 `page_start` 與 `page_end`（例如 Page 0-2, 3-5...）。
     6. 發送 Vendor Command **40F7** (Direct Write) 將 Pattern 寫入指定頁面，參數為 `mode=1`。
     7. 發送 Vendor Command **40F8** (Direct Read) 讀取相同頁面，參數為 `mode=1`。
     8. 構造預期資料 `pattern_data`：將 4 位元組 Pattern 重複填充至 4096 位元組（4KB）。
     9. 解析讀取回傳的 `data_read`，根據頁面數量 `i` 計算偏移量 `i * (16384 + 64)` 至 `(i + 1) * 16384 + i * 64`，提取對應頁面資料。
     10. 比對提取的頁面資料與 `pattern_data`。
   - 預期結果：所有 Die/Plane 的讀取資料必須與 `pattern_data` 完全相等。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這證明 SLC 模式下 Direct NAND 寫入路徑無誤，且韌體對 SLC 頁面長度（16KB + 64B OOB）的偏移計算正確。

2. [TLC_Direct_Write_Read_Integrity_Check]：
   - 動作：
     1. 設定測試參數：Block 範圍 100-100，使用 Pattern `0xABCDABCD`，最大頁面數 MAX_PAGE = 3311。
     2. 遍歷所有 Die 與 Plane。
     3. 對目標 Die/Plane/Block 100 發送 Vendor Command **40F6** (Direct Erase)，參數為 `mode=0` (TLC Mode)。
     4. 在頁面範圍內，以步長 10 遍歷 Page，並根據 Page 索引應用 TLC 特定的頁面分組邏輯：
        - **Region A (0 <= page < 1620)**：每 3 頁一組 (`page_start = page // 3 * 3`, `page_end = start + 2`)。
        - **Region B (1620 <= page < 1652)**：每 2 頁一組 (`page_start = 1620 + (page - 1620) // 2 * 2`, `page_end = start + 1`)。
        - **Region C (1652 <= page < 3308)**：每 3 頁一組 (`page_start = 1652 + (page - 1652) // 3 * 3`, `page_end = start + 2`)。
        - **Region D (3308 <= page < 3312)**：單頁處理 (`page_start = page`, `page_end = page`)。
     5. 發送 Vendor Command **40F7** (Direct Write) 將 Pattern 寫入計算出的頁面範圍，參數為 `mode=0`。
     6. 發送 Vendor Command **40F8** (Direct Read) 讀取相同頁面範圍，參數為 `mode=0`。
     7. 構造預期資料 `pattern_data`：將 4 位元組 Pattern 重複填充至 4096 位元組（4KB）。
     8. 解析讀取回傳的 `data_read`，使用與 SLC 相同的偏移公式 `i * (16384 + 64)` 提取頁面資料。
     9. 比對提取的頁面資料與 `pattern_data`。
   - 預期結果：所有 Die/Plane 的所有 Region 讀取資料必須與 `pattern_data` 完全相等。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這證明韌體能正確處理 TLC 模式下複雜的頁面分組邏輯（Page Grouping Logic），且在 Direct NAND Mode 下，無論頁面如何分組，底層 Flash 介面的資料寫入與讀取均保持數據完整性，無比特錯誤。