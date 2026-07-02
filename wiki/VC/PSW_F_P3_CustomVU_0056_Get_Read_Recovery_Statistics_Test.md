# Test Spec: UFS REH (Read Error Handling) ERS Incremental Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Read Error Handling (REH) 機制下，針對特定 LBA 執行讀取恢復流程時，Error Recovery Statistics (ERS) 計數器的正確性與遞增行為：
1. **基線確認**：確認初始狀態下 ERS 所有相關欄位均為 0，確保測試環境乾淨。
2. **狀態同步**：確認透過 Vendor Command (D014) 設定 Read Last Table 後，韌體內部狀態與 Host 讀取的 Read Last Table 偏移量完全一致。
3. **ERS 遞增驗證**：針對寫入資料後隨機選取的 LBA，透過 D014 觸發特定 Die/Plane/Block/Page 的 REH 恢復動作，並透過 40F9 獲取錯誤位元資訊。驗證在每次 D014 操作後，對應的 ERS 統計記錄值必須嚴格大於操作前的備份值，證明韌體正確追蹤並記錄了該次恢復嘗試，且未發生計數器回繞或靜默失敗。

## Test Case (TC) Checkpoints
1. [Baseline_ERS_Zero_Check]：
   - 動作：配置 LUN 0 為 Normal LU 並啟用，執行一次 `issue_40BA_to_get_error_recovery_statistics` 獲取初始 ERS payload。檢查 payload 第 4 位元起的所有位元（`payload[4:]`）。
   - 預期結果：所有檢查位元必須等於 0。若發現任何位元大於 1，則判定為驗證失敗，代表韌體在測試前存在未清除的錯誤統計狀態。

2. [Write_and_PBA_Mapping_Check]：
   - 動作：針對 LUN 0 從 LBA 0 開始順序寫入 1 個 VB (Virtual Block) 大小的資料（大小由 `tlc_vb_size` 決定，即 `fw_geometry.l88_vb_size_u1 * 512 // 4096`）。寫入完成後，隨機選取一個 LBA (`lba`)，並透過 `issue_4051_to_get_physical_address` 將其轉換為 PBA，獲取對應的 Die、Plane、Virtual Block Number 及 Page Number。
   - 預期結果：LBA 到 PBA 的映射必須成功返回有效的 Die、Plane 及 Block/Page 資訊，確保後續 REH 操作能精確指向硬體實體位置。

3. [Read_Last_Table_Sync_Check]：
   - 動作：建立空的 `read_last_ref_table` 並透過 `set_read_last_table` 初始化韌體狀態。接著透過 `issue_4014_to_get_read_recovery_info_read_last` 讀取所有 Die (0 至 `Max_Fdevice`)、所有 PAGE_TYPE 及 READ_LAST_TABLE 索引的偏移量 (`offset1`, `offset2`, `offset3`)。將讀回的值與 `read_last_ref_table` 中的參考值進行比對。
   - 預期結果：所有讀回的偏移量列表 `[offset1, offset2, offset3]` 必須與參考表中的預期值完全相等。若有任何不相等，代表韌體內部 Read Last Table 狀態與 Host 預期不同步，驗證失敗。

4. [REH_ERS_Incremental_Verification]：
   - 動作：
     a. 在執行 REH 前，再次透過 `issue_40BA` 獲取 ERS 備份值 (`bk_ers`)。
     b. 遍歷所有 REH 步驟組合 (`bigIndex`, `smallIndex`)，針對步驟 4 中獲取的 PBA 位置，透過 `issue_D014_to_set_read_recovery_module` 設定 REH 模組（指定 Die, Block, Page, TLC Mode 等參數）。
     c. 透過 `issue_40F9` 獲取該位置的錯誤恢復資訊 (`rr_number_raw_data`)。
     d. 透過 `issue_40BA` 獲取當前 ERS 值 (`ers`)。
     e. 使用 `get_ers_value` 函數解析 payload，計算當前 Die/Plane 下對應 REH 步驟的 ERS 記錄值 (`val`)，並與備份值 (`org_val`) 比較。
   - 預期結果：對於每一個遍歷的 REH 步驟，當前 ERS 值 (`val`) 必須嚴格大於備份值 (`org_val`)。若 `val <= org_val`，則記錄錯誤訊息並最終拋出 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH`，代表韌體未正確遞增錯誤恢復統計計數器，或 REH 機制未生效。