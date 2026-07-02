# Test Spec: MDWLSV OpenVB Consistency & Power State Persistence Test

## Verification Criterion (VC)
驗證 UFS 控制器在多種電源狀態轉換（SSU Sleep/Active, ATS Idle, Hibernate, HW Reset）及不同寫入路徑（Normal LUN, EM1 LUN, Write Booster）下的 **MDWLSV (Multi-Die Write Leveling Status Vector)** 與 **OpenVB (Open Virtual Block)** 狀態的一致性與持久性：
1.  **寫入路徑驗證**：確認在 Normal LUN 寫入 TLC L2、EM1 LUN 寫入、以及開啟 Write Booster (WB) 寫入 SLC L2 後，對應的 MDWLSV Offset 欄位（如 `Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset`）必須與 NAND Feature 查詢回傳的 `P3` 值嚴格相等，且非預設零值。
2.  **電源狀態持久性**：確認在執行 SSU Sleep/Active、ATS Idle (2s)、以及 Hibernate 循環後，MDWLSV 表格（Table1 vs Table2/3）中的所有 Die 偏移量欄位必須保持完全一致，證明韌體在低功耗狀態下正確保存了寫入狀態向量。
3.  **重置後狀態清除**：確認在執行 HW_RESET 後，MDWLSV 相關資料必須被清零（All Zero），代表控制器恢復初始狀態。

## Test Case (TC) Checkpoints

1.  **[TC01_Preparation_LUN_Config]**：
    -   動作：透過 `WriteDescriptor` 配置 LUN 0 (Normal, MemoryType=Normal), LUN 1 (BootA, MemoryType=Enhanced1), LUN 2 (BootB, MemoryType=Enhanced1), LUN 3 (EM1, MemoryType=Enhanced1)。禁用 Write Booster 相關 Flag (`WRITEBOOSTER_EN`, `WRITEBOOSTER_BUFFER_FLUSH_EN`)。讀取 Flash Geometry 計算 SLC/TLC VB Size。
    -   預期結果：LUN 配置成功，`TestNormalLun=0`, `TestEM1Lun=3` 等變數正確初始化，為後續寫入測試建立環境。

2.  **[TC02_TLC_L2_Write_Verification]**：
    -   動作：在 Normal LUN (LUN 0) 寫入 1 個 TLC CE Page Size 的資料 (`length=tlc_ce_page`)。接著透過 Vendor Command (VU) `0x4022` 查詢 NAND Feature，解析回傳 Payload 中的 `P3` 欄位。同時透過 VU `0x4029` 查詢 MDWLSV Offset，取得 `Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset` 的值。
    -   預期結果：`Die0_MDWLSV_SM_OPEN_BLOCK_NOMAL_HOST_TLC_offset.value` 必須等於 `P3.value`，且兩者均不為 0。若不相等或為 0，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

3.  **[TC03_EM1_L2_Write_Verification]**：
    -   動作：在 EM1 LUN (LUN 3) 寫入 1 LBA 的資料。透過 VU `0x4022` 查詢 NAND Feature 取得 EM1 寫入後的 `P3` 值。透過 VU `0x4029` 查詢 MDWLSV Offset，取得 `Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset` 的值。
    -   預期結果：`Die0_MDWLSV_MM_OPEN_BLOCK_EM1_HOST_offset.value` 必須等於 EM1 寫入後的 `P3.value`，且兩者均不為 0。

4.  **[TC04_L1_Write_Verification]**：
    -   動作：在 Normal LUN (LUN 0) 再次寫入 1 LBA 的資料（觸發 L1 層級寫入）。透過 VU `0x4022` 查詢 NAND Feature 取得 L1 寫入後的 `P3` 值。透過 VU `0x4029` 查詢 MDWLSV Offset，取得 `Die0_MDWLSV_MM_OPEN_BLOCK_NOMAL_HOST_SLC_offset` 的值。
    -   預期結果：`Die0_MDWLSV_MM_OPEN_BLOCK_NOMAL_HOST_SLC_offset.value` 必須等於 L1 寫入後的 `P3.value`，且兩者均不為 0。

5.  **[TC05_WB_SLC_L2_Write_Verification]**：
    -   動作：啟用 Write Booster (`api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)`)。在 Normal LUN (LUN 0) 寫入 1 LBA 的資料。透過 VU `0x4029` 查詢 MDWLSV Offset，取得 `Die0_MDWLSV_MM_OPEN_BLOCK_WRITE_BOOSTER_offset` 的值，並記錄為 `table1`。
    -   預期結果：寫入成功，且 `Die0_MDWLSV_MM_OPEN_BLOCK_WRITE_BOOSTER_offset` 應反映 WB 寫入狀態。此 `table1` 將作為後續電源狀態測試的基準表。

6.  **[TC06_SSU_Power_Cycle_Conistency]**：
    -   動作：記錄當前 OpenVB 狀態 (`open_vb_1`)。執行 SSU (StartStopUnit) 將 Device 進入 Sleep 狀態 (`power_condition=0x02`)，隨後喚醒 (`power_condition=0x01`)。喚醒後，再次透過 VU `0x4029` 查詢 MDWLSV Offset，記錄為 `table2`。比較 `open_vb_1` 與喚醒後的 `open_vb_2` 是否有差異，並使用 `tables_equal` 函數比對 `table1` 與 `table2` 的所有 MDWLSV Offset 欄位。
    -   預期結果：`open_vb_1` 與 `open_vb_2` 應無差異（或差異在預期範圍內）；`table1` 與 `table2` 必須完全相同（所有 Die 的 Offset 值一致）。若不同，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

7.  **[TC07_ATS_Idle_Conistency]**：
    -   動作：保持 `table1` 為基準。讓系統 Idle 2 秒鐘以進入 ATS (Auto Transition State)。隨後再次透過 VU `0x4029` 查詢 MDWLSV Offset，記錄為 `table2`。使用 `tables_equal` 比對 `table1` 與 `table2`。
    -   預期結果：`table1` 與 `table2` 必須完全相同。證明 ATS Idle 狀態不會導致 MDWLSV 狀態丟失或錯誤更新。

8.  **[TC08_Hibernate_Cycle_Conistency]**：
    -   動作：執行 Hibernate 進入與退出循環 (`loopcount=10`)。退出後，透過 VU `0x4029` 查詢 MDWLSV Offset，記錄為 `table3`。使用 `tables_equal` 比對 `table1` 與 `table3`。
    -   預期結果：`table1` 與 `table3` 必須完全相同。證明 Hibernate 深層低功耗狀態下，MDWLSV 狀態向量被正確保留。

9.  **[TC09_HW_Reset_Clear_Verification]**：
    -   動作：執行 `HW_RESET` (`api.init_tester_to_unit_ready` with `resetmode=HW_RESET`)。重置完成後，透過 VU `0x4029` 查詢 MDWLSV Offset Payload。呼叫 `check_all_zero` 函數檢查整個 Payload 是否全為 0x00。
    -   預期結果：MDWLSV Payload 的所有位元組必須為 `0x00`。代表 HW_RESET 成功清除了所有暫存的寫入狀態向量，控制器恢復至初始空閒狀態。