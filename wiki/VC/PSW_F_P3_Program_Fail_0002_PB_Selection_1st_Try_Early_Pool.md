# Test Spec: VC-30 (12.f) Program Fail Early Replacement Pool Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Normal Area 發生 Program Fail 時，硬體錯誤處理機制（Early Replacement Pool）與韌體 Bad Block Table (BBT) 更新的一致性：
1. 確認透過 Vendor Command (VU C012) 強制在 L2 VB 對應的 Block/Page 注入 Program Fail 錯誤後，後續的 Host Write10 指令能成功執行（代表韌體成功將該 LUN 的壞塊替換為 Early Replacement Pool 中的新 Block，即 "selection new PB succeed"）。
2. 確認韌體內部狀態機未因該錯誤觸發 Assert（系統未崩潰）。
3. 確認透過 VU 405E 讀取的 Bad Block 計數器（BB Count）精確增加 1。
4. 確認透過 VU 405E 解析出的 Bad Block Table (BBT) 資料中，確實包含了被標記為壞塊的 L2 VB 資訊（CE, Plane, Block），證明韌體已正確更新 BB Table 並記錄該 LUN 的壞塊位置。

## Test Case (TC) Checkpoints
1. [VC30_EarlyReplacement_BBT_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 讀取 Open VB 資訊，提取 L2 邏輯 VB 號碼 (`L2_vb`)。
     2. 透過 VU 405E 讀取初始 Bad Block 計數 (`BB_count`) 並記錄。
     3. 建構 `PhysicalAddressInformation`，指定 CE=0, Plane=0, Block=`L2_vb`, Page=0，並透過 VU C012 注入 `fail_type=0` (Program Fail) 至該特定 LWP。
     4. 記錄目標壞塊資訊 (`target_data_L2`)。
     5. 對 LUN 0 執行 Write10 指令（寫入 `WRITE_10_MAX_BLOCK_LEN` 長度，LBA 0），並發送指令（`clear_on_success=False` 以確保即使有錯誤也能檢查狀態，但預期應成功）。
     6. 透過 VU 4013 讀取 BE (Block Error) Fail 狀態。
     7. 再次透過 VU 405E 讀取新的 Bad Block 計數 (`BB_count_new`) 及完整 BBT 資料 (`BB_data_new`)。
     8. 驗證 `BB_count_new` 是否等於 `BB_count + 1`。
     9. 在 `BB_data_new` 中搜尋是否包含 `target_data_L2` (CE, Plane, Block) 的項目。
   - 預期結果：
     1. Write10 指令執行期間韌體未 Assert（測試腳本未拋出異常）。
     2. `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明壞塊計數器正確遞增。
     3. 搜尋結果 `find` 必須非空（`if not find` 不成立），證明 BBT 中確實存在該 L2 VB 對應的壞塊記錄。
     4. 綜合上述，驗證韌體在 Normal Area 發生 Program Fail 時，成功從 Early Replacement Pool 選取新 Block 替換（Write10 成功），並正確更新了 BB Table 與 Bad Block Count，無 Assert 發生。