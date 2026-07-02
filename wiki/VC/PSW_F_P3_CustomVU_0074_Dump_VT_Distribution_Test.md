# Test Spec: UFS NAND Trim & VT Distribution Consistency Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 SLC (LUN 1) 與 TLC (LUN 0) 不同記憶體類型下，透過 Vendor Command 0xC084 動態調整 NAND Trim 值（DAC）時，底層 Raw Data 讀取的比特翻轉計數（Bit One Count）與 Vendor Command 0x401D 回報的 VT (Threshold Voltage) 分佈統計數據之間的一致性。測試涵蓋 POR DSLC、TLC LP、MLC LP、SLC LP 等多種 Page Type，確認韌體對 NAND 物理特性的監控機制（0x401D）與直接硬體讀取（0x4060）的結果誤差控制在 ±10% 以內，確保韌體內部 VT 模型與實際 NAND 電壓閾值行為吻合。

## Test Case (TC) Checkpoints
1. [LUN_Configuration_and_Data_Warmup]：
   - 動作：透過 Configuration Descriptor 啟用 LUN 0 (Normal, TLC) 與 LUN 1 (Enhanced 1, SLC)，配置各分配 50% 容量。執行 Sequential Write 寫入 TLC VB Size 至 LUN 0 及 SLC VB Size 至 LUN 1，確保目標 Page 區域有有效資料。透過 Issue C088 停止 Refresh 機制，並設定 Power Saving Ctrl Enable 為 0x3A 以固定電源管理狀態。
   - 預期結果：LUN 0 與 LUN 1 均處於 Ready 狀態，且目標 LBA 區域已寫入有效資料，為後續的 Raw Data 讀取與 VT 分佈測試建立穩定的物理基礎。

2. [SLC_LUN1_POR_DSLC_Trim_VT_Consistency]：
   - 動作：針對 LUN 1 (SLC)，選取 PAGE_TYPE.PAGE_POR_DSLC。隨機生成 DAC 範圍（長度為 3），透過 Issue 4051 取得目標 LBA 對應的 Die/Plane/Block/Page 物理地址。先讀取原始 Trim 值備份。針對每個 DAC 值，透過 Issue C084 設定 NAND Trim 值（針對 POR DSLC 為地址 0x11E, 0x114）。接著透過 Issue 4060 讀取該 Page 的 Raw Data，計算特定 Offset 範圍內（Node 4588 bits）的 '1' 比特數量。最後透過 Issue 401D 取得相同 Die/Plane/Block/Page 的 VT 分佈統計數據。
   - 預期結果：Issue 401D 回報的 VT 分佈計數列表（diff_list）與 Issue 4060 讀取 Raw Data 計算出的 bit_one_count 列表，兩者對應數值必須落在彼此數值的 ±10% 範圍內（即 $0.9 \times Y \le X \le 1.1 \times Y$）。若超出此範圍，觸發 SIGHTING_FAIL_DATA_COMPARE_FAIL。

3. [TLC_LUN0_LP_Trim_VT_Consistency_with_Pre_Set]：
   - 動作：針對 LUN 0 (TLC)，依序測試 PAGE_TYPE.PAGE_TLC_LP, PAGE_MLC_LP, PAGE_SLC_LP。對於 PAGE_TYPE.PAGE_TLC_LP，在設定目標 DAC 前，先透過 Issue C084 預設地址 0xD8 為 0xDA（最大 Trim 值）。隨後對每個 DAC 值，透過 Issue C084 設定對應的 Trim 地址（TLC LP 為 0xB0；MLC LP 為 0x110；SLC LP 為 0x126）。執行與 Case 2 相同的 Issue 4060 讀取 Raw Data 計數與 Issue 401D 讀取 VT 分佈比對。
   - 預期結果：在所有測試的 Page Type 下，VT 分佈統計與 Raw Data 比特計數的一致性誤差必須維持在 ±10% 以內。特別注意 TLC LP 在預設最大 Trim 值的情境下，韌體應能正確反映 NAND 電壓閾值的變化，確保 VT 模型在極端 Trim 設定下仍具準確性。

4. [Trim_Value_Recovery_and_Refresh_Restart]：
   - 動作：在所有 LUN 與 Page Type 測試完成後，透過 Issue C084 將所有修改過的 Trim 地址恢復至測試前的原始值（org_trim）。最後透過 Issue C088 重新啟動 Refresh 機制，並透過 post_process 恢復硬體設定。
   - 預期結果：NAND Trim 寄存器恢復至初始狀態，確保測試不會對裝置造成永久性配置影響；Refresh 機制正常運作，裝置回到標準待命狀態。