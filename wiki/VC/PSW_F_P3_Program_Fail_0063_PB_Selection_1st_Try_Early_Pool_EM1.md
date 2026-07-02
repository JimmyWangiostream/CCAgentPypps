# Test Spec: VC-30 (12.f) Program Fail Injection & BB Table Update Verification

## Verification Criterion (VC)
驗證在 EM1 LUN (LUN 1) 的 Normal Area 中，透過 Vendor Command (VU C012) 強制注入 Program Fail 錯誤後，韌體是否能正確識別該 L2 VB 為壞塊並更新 Bad Block Table (BBT)。具體驗證目標為：Case 01 確認注入前後的 Bad Block Count 嚴格增加 1；Case 02 確認新的 BBT 數據中確實包含被注入失敗的特定 L2 VB 區塊資訊（CE=0, Plane=0, Block=L2_vb, Page=0），且韌體無 Assert 崩潰，代表韌體成功處理了 Program Fail 事件並更新了內部 BB Table。

## Test Case (TC) Checkpoints
1. [Case01_EM1_L2_PF_BBT_Update_Check]：
   - 動作：
     1. 配置 LUN 0 為 Normal，LUN 1 (EM1) 為測試目標。
     2. 在 EM1 LUN (LUN 1) 的 LBA 0 寫入 4KB 資料以建立初始狀態。
     3. 執行 Vendor Command `VU 40C1` 獲取 Open VB 資訊，提取出 EM1 L2 的 Logical VB 號碼 (`L2_vb`)。
     4. 執行 Vendor Command `VU 405E` 獲取初始 Bad Block Count (`BB_count`) 及 BBT 數據。
     5. 構造 `PhysicalAddressInformation`，指定 CE=0, Plane=0, Block=`L2_vb`, Page=0。
     6. 執行 Vendor Command `VU C012` (fail_type=0) 針對上述地址強制注入 Program Fail 錯誤。
     7. 再次對 EM1 LUN (LUN 1) 的 LBA 0 執行 Write10 操作以觸發韌體處理機制。
     8. 執行 Vendor Command `VU 4013` 獲取 BE (Block Error) Fail Status。
     9. 再次執行 Vendor Command `VU 405E` 獲取新的 Bad Block Count (`BB_count_new`) 及 BBT 數據 (`BB_data_new`)。
     10. 比對 `BB_count_new` 與 `BB_count` 的差異，並檢查 `BB_data_new` 中是否包含目標區塊資訊 (`target_data_L2`)。
   - 預期結果：
     1. `BB_count_new` 必須嚴格等於 `BB_count + 1`，代表韌體正確計數了新增的壞塊。
     2. 在 `BB_data_new` 列表中，必須能找到一筆數據其內容完全包含 `{'Block': L2_vb, 'CE': 0, 'Plane': 0}`，代表被注入 Program Fail 的 L2 VB 區塊已被正確標記為壞塊並記錄在 BBT 中。
     3. 整個流程中韌體未發生 Assert 或崩潰，證明韌體在處理 Program Fail 並更新 BB Table 時的穩定性。