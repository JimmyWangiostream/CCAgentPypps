# Test Spec: UFS Random Mixed I/O Stress Test with HW Compare Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 LUN 0 至 LUN 2 範圍內，針對 128KB 至 1MB 隨機大小區塊進行高頻率（10-32 次/輪）的隨機寫入（Random Write）、隨機擦除（Random Erase）與隨機讀取（Random Read）混合負載時，硬體控制器（HW）的數據完整性與一致性：
1. **寫入驗證**：確認 `api.random_write` 在啟用 `HW_COMPARE` 模式下，寫入 LBA 的實際硬體數據與 Host 發送之 Payload 完全一致，無比特錯誤或損壞。
2. **讀取驗證**：確認 `api.random_read` 在寫入與擦除操作後，讀回之 LBA 數據與 `write_record` 中記錄的原始預期數據完全匹配，驗證資料路徑在混合 I/O 壓力下的數據保留能力。
3. **擦除行為**：確認 `api.random_erase` 在指定 LBA 範圍內正確執行 Block Erase 操作，為後續寫入準備空白狀態，且不影響其他未指定 LBA 的數據完整性。

## Test Case (TC) Checkpoints
1. [Random_Mixed_IO_HW_Integrity_Check]：
   - 動作：
     1. 初始化寫入記錄表 `write_record`。
     2. 執行單一測試輪次（Loop 1），隨機生成 10 至 32 個命令計數（`cmd_count`）。
     3. 設定操作範圍為 LUN 0 至 LUN 2，LBA 範圍為 0 至 `gLUCapacity[0]`。
     4. 執行 `api.random_write`：隨機選擇 LUN/LBA，區塊大小隨機分佈於 128KB (`BLOCK4K_SIZE_128K_BYTE`) 至 1MB (`BLOCK4K_SIZE_1M_BYTE`) 之間。關鍵參數設定 `need_compare=True` 且 `compare_method=api.CompareMethod.HW_COMPARE`，此動作強制控制器在寫入完成後，由硬體邏輯直接比對 Flash 單元內的實際數據與 Host 發送之數據，並將結果寫入 `write_record`。
     5. 執行 `api.random_erase`：在同一 LUN/LBA 範圍內，使用相同大小分佈隨機選擇區塊進行 Erase 操作，更新 `write_record` 狀態。
     6. 執行 `api.random_read`：在同一 LUN/LBA 範圍內，使用相同大小分佈隨機選擇區塊進行 Read 操作。關鍵參數設定 `need_compare=True`，此動作強制控制器讀取數據後，與 `write_record` 中記錄的預期數據（來自步驟 4 的寫入記錄）進行逐位元比對。
   - 預期結果：
     1. `random_write` 階段：所有發送的 Write 命令必須成功完成，且硬體比對機制（HW_COMPARE）未報告任何數據不一致錯誤（Data Mismatch）。這代表寫入路徑在 128KB-1MB 大區塊壓力下，數據寫入 Flash 的完整性得到硬體級別確認。
     2. `random_erase` 階段：所有 Erase 命令必須成功完成，無 Timeout 或 Erase Failure 錯誤碼。
     3. `random_read` 階段：所有發送的 Read 命令必須成功完成，且讀回數據與 `write_record` 中的預期數據完全一致（Bit-for-Bit Match）。這代表在經歷隨機寫入與隨機擦除的混合干擾後，數據在 Flash 中的保留狀態正確，讀取路徑無誤碼，驗證了 UFS 控制器在混合 I/O 負載下的數據一致性與韌體調度邏輯的穩定性。