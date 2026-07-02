# Test Spec: VC-30 (12.f) Write Booster Program Fail & BBT Update Verification

## Verification Criterion (VC)
驗證韌體在 Write Booster (WB) L2 區塊遭遇 Program Fail 時的錯誤處理與 Bad Block Table (BBT) 更新機制：
1. **錯誤注入與狀態確認**：透過 Vendor Command (VU) `0xC012` 強制在 L2 VB 對應的 Block/Page 注入 Program Fail，確認韌體能正確識別該物理區塊為失效。
2. **BBT 一致性檢查**：比較注入前後透過 VU `0x405E` 讀取的 Bad Block Count，驗證注入後計數器必須嚴格增加 1，且新的 BBT 數據中必須包含被標記為失效的 L2 物理地址資訊。
3. **韌體穩定性**：在執行上述寫入與錯誤檢查流程後，系統不得觸發 Assert 或崩潰，確認韌體在處理 WB 區域 Program Fail 時的邏輯完整性。

## Test Case (TC) Checkpoints
1. [Case01_WB_L2_ProgramFail_BBT_Update_Check]：
   - 動作：
     1. 初始化 LUN 配置，設定 Normal LUN 為 0, EM1 LUN 為 1, WB LUN 為 2。
     2. 透過 VU `0x40C1` 獲取 Open VB 資訊，提取 `open_logical_VB_number_for_Write_Booster_WB_L2` 作為目標 L2 VB 號碼。
     3. 透過 VU `0x405E` 讀取初始 Bad Block Count (`BB_count`) 並記錄。
     4. 建構 `PhysicalAddressInformation`，指定 CE=0, Plane=0, Block=L2_vb, Page=0，並透過 VU `0xC012` 以 `fail_type=0` 在該 L2 物理位置強制注入 Program Fail。
     5. 啟用 Write Booster 標誌 (`api.FlagIDN.WRITEBOOSTER_EN`)。
     6. 向 LUN 2 (WB LUN) 發送 Write10 命令寫入 `WRITE_10_MAX_BLOCK_LEN` 長度資料，並透過 VU `0x4013` 讀取 BE (Block Error) Fail 狀態。
     7. 再次透過 VU `0x405E` 讀取更新後的 Bad Block Count (`BB_count_new`) 及完整 BBT 數據 (`BB_data_new`)。
     8. 驗證 `BB_count_new` 是否等於 `BB_count + 1`，並檢查 `BB_data_new` 中是否存在與目標物理地址 (`target_data_L2`) 完全匹配的條目。
   - 預期結果：
     1. `BB_count_new` 必須精確等於 `BB_count + 1`，證明失效區塊已被計入。
     2. `BB_data_new` 列表中必須包含一個條目，其 Block, CE, Plane 欄位分別等於注入時的 L2_vb, 0, 0。
     3. 整個流程執行期間，韌體未發生 Assert 或系統崩潰，確認 BBT 更新邏輯在 WB 情境下運作正常。