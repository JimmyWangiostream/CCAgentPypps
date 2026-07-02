# Test Spec: VC-31 (12.g) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇 Program/Erase Fail (PF) 時的 Bad Block Table (BBT) 更新機制與 Replacement Pool 選擇邏輯：
1. **Normal Area (L2) PF Handling**：當透過 Vendor Command `0xC012` (fail_type=1) 在 Normal L2 VB 注入 PF 後，韌體必須正確將該 Block 標記為 Bad Block，並從 Latereplacement Pool (Shared for Dynamic) 中選取一個新的 Replacement Block。驗證目標是確保新選取的 Replacement Block **不屬於** Revoke Group，且 BBT 計數準確增加。
2. **LIST Area PF Handling**：當透過 Vendor Command `0xC012` (fail_type=0) 在 LIST VB 注入 PF 後，韌體必須正確將該 Block 標記為 Bad Block，並驗證 BBT 計數準確增加且該 Block 被正確記錄在 BBT 中。
3. **BBT Consistency**：兩次操作後，透過 Vendor Command `0x405E` 讀取的 Bad Block Count 必須嚴格等於初始 Count + 2，且計算出的 BBT 數據中必須包含被注入 PF 的具體物理地址 (CE/Plane/Block)。

## Test Case (TC) Checkpoints

1. **[Case01_Normal_L2_PF_Replacement_Check]**：
   - 動作：
     1. 透過 `get_VB_group` 獲取當前 Revoke Group 列表。
     2. 透過 Vendor Command `0x40C1` 獲取當前 Open L2 VB (`L2_vb`)，並透過 `0x40DC` 獲取下一個 Open L2 VB (`L2_vb_next`)。
     3. 透過 Vendor Command `0x405E` 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 Vendor Command `0x40D6` 獲取預測的下一個 Replacement Block (`next_replacement_block`)。
     5. **循環檢查**：若 `next_replacement_block` 位於 Revoke Group 內，則透過 Vendor Command `0xC012` (fail_type=1) 在 `L2_vb_next` 注入 Program Fail，隨後執行連續 Write10 操作直到 L2 VB 切換，然後重複步驟 2-5 直到獲取到一個**不在** Revoke Group 內的 Replacement Block。
     6. 針對最終選定的 `L2_vb_next`，透過 Vendor Command `0xC012` (fail_type=1) 注入 Program Fail。
     7. 執行連續 Write10 操作直到 L2 VB 發生切換 (`L2_vb_new != L2_vb`)。
     8. 透過 Vendor Command `0x4013` 獲取 BE Fail Status。
     9. 透過 Vendor Command `0x405E` 獲取新的 Bad Block Count (`BB_count_new`) 及 BBT 數據 (`BB_data_new`)。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`。
     - `BB_data_new` 中必須能找到包含目標 Block 資訊 (`Block=L2_vb_next`, `CE=0`, `Plane=0`) 的條目。
     - 在循環過程中，最終選取的 Replacement Block 必須確認不在 Revoke Group 中，驗證韌體在 Normal Area 的 Replacement 邏輯會避開 Revoke Block。

2. **[Case02_LIST_PF_BBT_Update_Check]**：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 獲取當前 LIST VB (`LIST_vb`)，並透過 `0x40DC` 獲取下一個 LIST VB (`LIST_vb_next`)。
     2. 透過 Vendor Command `0x405E` 記錄當前 Bad Block Count (`BB_count`)。
     3. 透過 Vendor Command `0xC012` (fail_type=0) 在 `LIST_vb_next` (CE=0, Plane=0) 注入 Program Fail。
     4. 執行隨機 Write10 操作直到 LIST VB 發生切換 (`LIST_vb_new != LIST_vb`)。
     5. 透過 Vendor Command `0x4013` 獲取 BE Fail Status。
     6. 透過 Vendor Command `0x405E` 獲取新的 Bad Block Count (`BB_count_new`) 及 BBT 數據 (`BB_data_new`)。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1` (相對於 Case 01 結束後的狀態)。
     - `BB_data_new` 中必須能找到包含目標 Block 資訊 (`Block=LIST_vb_next`, `CE=0`, `Plane=0`) 的條目。
     - 驗證韌體在 LIST Area 遭遇 PF 時，能正確更新 BBT 並反映在 `0x405E` 的統計數據中。