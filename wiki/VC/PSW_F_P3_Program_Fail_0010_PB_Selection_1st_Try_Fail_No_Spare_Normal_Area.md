# Test Spec: VC-24 (9.b) Program Fail Spare Block Exhaustion & FW Stuck Verification

## Verification Criterion (VC)
驗證當 UFS 韌體在 Normal Area 中 Spare Block 耗盡且無法選取新的 Replacement Block 時，系統進入死鎖（Stuck）狀態的硬體行為與韌體異常處理機制：
1. **Pre-process 階段**：確認在正常運作下，透過 Vendor Command (VU) 監控 L2 VB 遷移與 Bad Block Table (BBT) 更新，並驗證在注入 Erase Fail 後，目標 Block 能正確被標記為 Bad Block 且 BB Count 增加。
2. **Step1 階段**：針對當前 Open L2 VB 所在的 Block 注入 Program Fail，隨後執行 Write10 指令。預期韌體因無法處理該 Fail 且無 Spare Block 可用，導致 Host 端收到 `G_TIMEOUT_ALL` 異常，並確認韌體內部觸發特定的 Assert 編號 `0x202`，代表韌體已進入預期中的錯誤停滯狀態。

## Test Case (TC) Checkpoints

1. [PreProcess_BBManagement_and_FailInjection_Check]：
   - 動作：
     1. 透過 `issue_40C1` 讀取當前 L2 Open VB (`L2_vb`)，並透過 `issue_40DC` 讀取下一個預期的 L2 VB (`L2_vb_next`)。
     2. 透過 `issue_405E` 記錄初始 Bad Block Count (`BB_count`) 與 BBT 資料。
     3. 透過 `issue_40D6` 檢查下一個 Replacement Block，若為 `0xFFFF` 則代表 Spare Block 池可能已空或無法預測，此為測試前置條件檢查。
     4. 使用 `issue_C012` 針對 `L2_vb_next` 所在的 Block (CE=0, Plane=0) 注入 `fail_type=1` (Erase Fail)。
     5. 執行連續 Write10 寫入，直到 L2 VB 發生遷移（`L2_vb_new != L2_vb`），確保目標 Block 已被 LVM 映射為 Open VB 或即將被使用。
     6. 再次透過 `issue_405E` 讀取新的 BB Count (`BB_count_new`) 並計算 BBT。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`，證明 Erase Fail 注入成功且韌體已將該 Block 標記為 Bad Block。
     - BBT 資料中必須包含目標 Block 資訊 (`target_data_L2`)，驗證 BBT 更新機制正常運作。
     - 若 `next_replacement_block` 為 `0xFFFF`，則跳過後續注入邏輯或視為 Spare Block 不足的前置狀態（根據代碼邏輯，若為 0xFFFF 則 break，但後續 Step1 仍會執行，此處主要驗證正常流程下的 BB 管理）。

2. [Step1_ProgramFail_and_FWStuck_Assert_Check]：
   - 動作：
     1. 透過 `issue_40C1` 獲取當前 L2 VB (`L2_vb`)。
     2. 使用 `issue_C012` 針對當前 `L2_vb` 所在的 Block (CE=0, Plane=0) 注入 `fail_type=0` (Program Fail)。
     3. 發送一個 Write10 指令（長度為 `WRITE_10_MAX_BLOCK_LEN`，LUN=0, LBA=0, FUA=1）至裝置。
     4. 捕獲 Host 端回應，預期會拋出 `G_TIMEOUT_ALL` 異常。
     5. 在異常捕獲區塊中，呼叫 `api.get_fw_assert_number()` 讀取韌體 Assert 編號。
   - 預期結果：
     - Host 端必須拋出 `G_TIMEOUT_ALL`，表示韌體未能在預期時間內回應 Write10 指令，處於無回應狀態。
     - `api.get_fw_assert_number()` 返回的數值必須嚴格等於 `0x202`。
     - 這代表韌體在處理 Program Fail 且無法分配 Spare Block 時，觸發了特定的 Assert 機制（FW Stuck），而非隨機崩潰或恢復，驗證了韌體在資源耗盡時的錯誤處理路徑符合設計預期。