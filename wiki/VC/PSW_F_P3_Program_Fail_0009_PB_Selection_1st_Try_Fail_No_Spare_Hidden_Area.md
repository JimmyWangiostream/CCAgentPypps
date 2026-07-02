# Test Spec: VC-23 (9.a) Program Fail Spare Block Exhaustion FW Stuck Test

## Verification Criterion (VC)
驗證 UFS 韌體在備用區塊（Spare Block）耗盡情境下的錯誤處理機制：
1. **Pre-process 階段**：確認透過 Vendor Command (VU C012) 強制注入 Erase Fail 後，韌體能正確將目標 L2 VB 區塊與預測的 Hidden Area 備用區塊標記為 Bad Block (BB)，並驗證 BBT (Bad Block Table) 中新增的 BB 數量精確增加 2 個，且包含這兩個特定物理地址。
2. **Step1 階段**：驗證當 L2 VB 本身被標記為 Program Fail 且無可用備用區塊時，執行 Write10 指令會觸發韌體 Assert。預期結果為韌體進入死鎖狀態（Stuck），並回報特定的 Assert Code `0xB7`，代表韌體無法處理「選擇新 PB 失敗」的極端錯誤情境。

## Test Case (TC) Checkpoints

1. [PreProcess_BBInjection_and_Verification]：
   - 動作：
     1. 透過 `issue_40C1` 讀取當前 L2 Open VB (`L2_vb`) 及透過 `issue_40DC` 讀取下一個 L2 VB (`L2_vb_next`)。
     2. 透過 `issue_405E` 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 `issue_40D6` (pool_type=2, hidden area) 預測下一個備用區塊地址 (`next_replacement_block/ce/plane`)。
     4. 呼叫 `issue_C012` (fail_type=1, Erase Fail) 對兩個物理地址進行錯誤注入：
        - Target 0: `L2_vb_next` (Die 0, Plane 0)
        - Target 1: `next_replacement_block` (Die `next_replacement_ce`, Plane `next_replacement_plane`)
     5. 執行連續 Write10 直到 L2 VB 切換至新的 `L2_vb`。
     6. 再次呼叫 `issue_405E` 獲取新的 BB 資訊，並計算 BBT 列表。
   - 預期結果：
     - 新的 BB 計數 (`BB_count_new`) 必須嚴格等於 `BB_count + 2`。
     - BBT 列表中必須包含 `L2_vb_next` 的完整物理地址資訊 (Block, CE, Plane)。
     - BBT 列表中必須包含 `next_replacement_block` 的完整物理地址資訊 (Block, CE, Plane)。
     - 若上述任一條件不符，測試應拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [Step1_L2_PF_NoSpare_FWAssert_Check]：
   - 動作：
     1. 透過 `issue_40C1` 獲取當前 L2 VB (`L2_vb`)。
     2. 透過 `issue_40D6` 獲取預測備用區塊地址。
     3. 呼叫 `issue_C012` (fail_type=0, Program Fail) 對以下兩個地址進行錯誤注入：
        - Target 0: 當前 L2 VB (`L2_vb`, Die 0, Plane 0)
        - Target 1: 預測備用區塊 (`next_replacement_block`, Die `next_replacement_ce`, Plane `next_replacement_plane`)
     4. 對 LUN 0 執行 Write10 指令 (LBA 0, Length `WRITE_10_MAX_BLOCK_LEN`, FUA=1)。
     5. 捕獲執行時的異常，預期會拋出 `G_TIMEOUT_ALL`。
     6. 在捕獲異常後，呼叫 `api.get_fw_assert_number()` 讀取韌體 Assert 編號。
   - 預期結果：
     - 寫入指令必須超時並拋出 `G_TIMEOUT_ALL`。
     - 韌體 Assert 編號必須嚴格等於 `0xB7`。
     - 若 Assert 編號不等於 `0xB7`，測試應拋出 `SIGHTING_RESPONSE_UNEXPECTED`，代表韌體未能在備用區塊耗盡且 L2 寫入失敗時正確進入預期的死鎖狀態。