# Test Spec: Sticky Read & Read Count Verification with Power Cycle

## Verification Criterion (VC)
驗證 UFS 韌體中 Sticky Read 機制與 Read Count 統計功能的正確性及持久性：
1. **Default Read Count**: 確認在啟用 Read Count 後，針對特定 LUN/LBA 的標準讀取操作會正確增加 EHS (Error Recovery Statistics) 中 Index 65 的計數器，而 Sticky Read 計數器 (Index 66) 保持不變。
2. **Sticky Read Count**: 確認在啟用 Sticky Read 並強制設定 Read Last 為 Sticky Read 後，針對相同 LUN/LBA 的讀取操作會同時增加 EHS 中 Index 65 與 Index 66 的計數器，且兩者增量必須一致。
3. **Counter Freeze on Disable**: 確認關閉 Read Count 功能後，後續讀取操作不會導致 EHS 中 Index 65 與 66 的計數器發生任何變化。
4. **Power Cycle Persistence**: 確認在 HW_RESET 硬體重啟後，EHS 中 Index 65 與 66 的計數器必須重置為 0（或初始狀態），證明這些統計計數器為易失性暫存器，不具備掉電保存功能。

## Test Case (TC) Checkpoints

1. [Case01_Default_Read_Count_Increment_Check]：
   - 動作：
     1. 配置 LUN 0 為 Normal LU 並寫入 1 VB 大小的資料。
     2. 透過 VUC 0x4051 將隨機 LBA 轉換為物理地址 (PBA: die, plane, block, page, offset)。
     3. 執行 `issue_D019` 啟用 Read Count 功能。
     4. 針對 Case `DEFAULT_READ_PASS_CASE`，不設定 Sticky Read 預備條件。
     5. 透過 `issue_40BA` 讀取初始 EHS 狀態 (`ers_bk`)。
     6. 遍歷所有 Page Type (SLC/MLC/TLC)，透過 `issue_4052` 將 PBA 轉回 LBA，並對每個 LBA 執行一次 Host Read 4K 操作。
     7. 每次讀取後，透過 `issue_40BA` 讀取當前 EHS 狀態 (`ers`)。
     8. 呼叫 `compare_ers_entry` 計算 Index 65 (Default Read Pass Count) 與 Index 66 (Sticky Read Pass Count) 的差值。
   - 預期結果：
     - Index 65 的差值 (`read_count_diff`) 必須大於 0，代表標準讀取被正確計數。
     - Index 66 的差值 (`sticky_count_diff`) 必須等於 0，代表 Sticky Read 機制未觸發或未啟用，計數器未增加。

2. [Case02_Sticky_Read_Count_Increment_Check]：
   - 動作：
     1. 重置 LUN 配置與寫入記錄。
     2. 執行 `issue_D019` 啟用 Read Count 功能。
     3. 針對 Case `STICKY_READ_PASS_CASE`，執行 `set_sticky_read_precondition`：
        - 透過 `issue_D014` 設定 Read Last Table。
        - 透過 `issue_4066` 強制將當前 Read Last 設定為 Sticky Read Offset。
        - 透過 `issue_4066` 啟用 Sticky Read 功能。
     4. 透過 `issue_40BA` 讀取初始 EHS 狀態 (`ers_bk`)。
     5. 遍歷所有 Page Type，將 PBA 轉回 LBA 並執行 Host Read 4K 操作。
     6. 每次讀取後，透過 `issue_40BA` 讀取當前 EHS 狀態 (`ers`)。
     7. 呼叫 `compare_ers_entry` 計算 Index 65 與 Index 66 的差值。
   - 預期結果：
     - Index 65 的差值 (`read_count_diff`) 必須大於 0。
     - Index 66 的差值 (`sticky_count_diff`) 必須大於 0。
     - 且 `sticky_count_diff` 必須嚴格等於 `read_count_diff`，代表 Sticky Read 機制生效，且 Sticky Read 計數與標準讀取計數同步增加。

3. [Case03_Read_Count_Freeze_On_Disable_Check]：
   - 動作：
     1. 在 Case 01 或 Case 02 完成後，執行 `issue_D019` 關閉 Read Count 功能 (`STICKY_READ_SETTING.DISABLE`)。
     2. 記錄當前 EHS 狀態為 `ers_bk`。
     3. 遍歷所有 Page Type，將 PBA 轉回 LBA 並再次執行 Host Read 4K 操作。
     4. 讀取最終 EHS 狀態 (`ers`)。
     5. 呼叫 `compare_ers_entry` 計算 Index 65 與 Index 66 的差值。
   - 預期結果：
     - Index 65 的差值 (`read_count_diff`) 必須等於 0。
     - Index 66 的差值 (`sticky_count_diff`) 必須等於 0。
     - 代表關閉 Read Count 功能後，韌體停止更新相關統計暫存器，計數器值保持凍結。

4. [Case04_Power_Cycle_Reset_Check]：
   - 動作：
     1. 在 Case 02 (Sticky Read Enabled) 完成後，執行 `issue_D019` 啟用 Read Count (確保狀態一致)。
     2. 執行 `api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET)` 進行硬體重置 (Power Cycle)。
     3. 韌體恢復後，執行 `issue_40BA` 讀取初始 EHS 狀態 (`ers_bk`)。
     4. 若為 Sticky Read Case，重新執行 `set_sticky_read_precondition` 以恢復 Sticky Read 設定。
     5. 遍歷所有 Page Type，將 PBA 轉回 LBA 並執行 Host Read 4K 操作。
     6. 讀取最終 EHS 狀態 (`ers`)。
     7. 呼叫 `compare_ers_entry` 計算 Index 65 與 Index 66 的差值。
   - 預期結果：
     - Index 65 的差值 (`read_count_diff`) 必須等於 0。
     - Index 66 的差值 (`sticky_count_diff`) 必須等於 0。
     - 代表 HW_RESET 後，EHS 中的 Read Count 與 Sticky Read Count 暫存器已被韌體初始化為 0，驗證其易失性特性。