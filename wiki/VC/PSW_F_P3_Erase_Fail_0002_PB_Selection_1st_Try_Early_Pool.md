# Test Spec: VC-7 (1.f) Erase Fail Injection & BBT Update Verification

## Verification Criterion (VC)
驗證韌體在遭遇強制 Erase Fail (EF) 情境下的 Bad Block Table (BBT) 更新機制與系統穩定性：
1. **錯誤注入有效性**：確認透過 Vendor Command `0xC012` 成功在指定的 L2 VB 對應之物理區塊（Block `L2_vb_next`）注入 Erase Fail 狀態。
2. **BBT 即時更新**：確認在 L2 VB 發生切換（L2 VB Change）後，韌體能正確識別該失效區塊，並將其標記為 Bad Block。具體表現為：Bad Block Count (`BB_count`) 必須精確增加 1，且該失效區塊的物理地址（CE, Plane, Block）必須出現在新的 BBT 數據中。
3. **系統穩定性**：確認在此異常流程中，韌體未觸發 Assert 或 Crash，且能透過 Vendor Command `0x4013` 正常讀取 BE (Bad Erase) Fail Status，證明韌體處於正常運作狀態。

## Test Case (TC) Checkpoints
1. [Case01_EF_Injection_and_BBT_Update_Check]：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 讀取當前 L2 VB (`L2_vb`)，並透過 `0x40DC` 讀取下一個待分配的 L2 VB (`L2_vb_next`)。
     2. 透過 Vendor Command `0x405E` 記錄初始 Bad Block Count (`BB_count`)。
     3. 建構 `PhysicalAddressInformation`，指定 CE=0, Plane=0, Block=`L2_vb_next`, Page=0，並透過 Vendor Command `0xC012` 以 `fail_type=1` (Erase Fail) 強制注入錯誤。
     4. 執行連續 Write10 指令（LBA 從 0 開始，長度為 `WRITE_10_MAX_BLOCK_LEN`），每次寫入後透過 `0x40C1` 檢查 L2 VB 是否發生變化。一旦 `L2_vb_new != L2_vb`，表示 L2 VB 已切換至包含注入 EF 的區塊，停止寫入。
     5. 透過 Vendor Command `0x4013` 讀取 BE Fail Status。
     6. 再次透過 Vendor Command `0x405E` 讀取新的 Bad Block Count (`BB_count_new`) 及 BBT 數據 (`BB_data_new`)。
     7. 驗證 `BB_count_new` 是否等於 `BB_count + 1`，並搜尋 `BB_data_new` 中是否包含目標區塊資訊 (`target_data_L2`: CE=0, Plane=0, Block=`L2_vb_next`)。
   - 預期結果：
     1. `BB_count_new` 必須嚴格等於 `BB_count + 1`，代表失效區塊已被計入 Bad Block。
     2. `find` 列表必須非空，代表目標區塊 (`L2_vb_next`) 已正確記錄在 BBT 中。
     3. 整個流程中未拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，且無 Assert 發生，代表韌體成功處理了 Erase Fail 並更新了內部結構。