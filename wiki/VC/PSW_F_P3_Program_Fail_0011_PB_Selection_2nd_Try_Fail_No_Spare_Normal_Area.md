# Test Spec: VC-26 (10.b) Program Fail Spare Block Exhaustion & FW Stuck Test

## Verification Criterion (VC)
驗證當正常區域（Normal Area）備用區塊（Spare Block）耗盡時，韌體在遭遇連續寫入失敗情境下的錯誤處理機制：
1. **前置準備**：透過 Vendor Command (VU) 精確控制，將目標 L2 VB 及其預測的下一個備用區塊（Next Replacement Block）強制標記為 Program/Erase Fail，模擬正常區域備用資源枯竭且無可用替換區塊的狀態。
2. **故障觸發**：執行 Write10 命令寫入資料，由於目標區塊與替換區塊均被注入 Fail 狀態，預期寫入操作會觸發硬體層級的 Program Fail。
3. **韌體行為驗證**：確認韌體在無法透過替換區塊恢復資料完整性且無更多備用資源時，不會進入無限重試或崩潰，而是觸發特定的韌體 Assert 機制（Assert Number 0x202），代表系統進入保護性停滯（Stuck）狀態以阻止資料進一步損壞。

## Test Case (TC) Checkpoints

1. [PreProcess_SpareBlockDepletion_Setup]：
   - 動作：
     1. 透過 `issue_40C1` 讀取當前 L2 Open VB (`L2_vb`) 及透過 `issue_40DC` 讀取下一個 L2 VB (`L2_vb_next`)。
     2. 透過 `issue_405E` 記錄初始 Bad Block (BB) 計數。
     3. 透過 `issue_40D6` (pool_type=1, next_n=2) 獲取預測的兩個替換區塊地址 (`next_replacement_block_1`, `next_replacement_block_2`)。
     4. 若 `next_replacement_block_2` 不為 0xFFFF，則透過 `issue_C012` (fail_type=1) 對 `L2_vb_next` 注入 Erase Fail，強制其成為 Bad Block。
     5. 執行連續 Write10 寫入，直到 L2 VB 切換至新的 `L2_vb_next`（此時該區塊已因步驟 4 被標記為 Fail）。
     6. 驗證 BBT 更新：確認 BB 計數增加 1，且新的 Bad Block 列表中包含該目標區塊。
     7. 重複上述流程，直到 `issue_40D6` 返回的第二個替換區塊為 0xFFFF，表示正常區域備用區塊池已接近耗盡，僅剩一個有效替換區塊。
   - 預期結果：
     - 初始 BB 計數與後續 BB 計數差異為 1。
     - BBT 數據正確反映新產生的 Bad Block。
     - 循環終止條件滿足，確保測試進入 `step1` 時，系統處於「僅剩一個備用區塊」的臨界狀態。

2. [Step1_Critical_Spare_Exhaustion_Fail_Check]：
   - 動作：
     1. 透過 `issue_40C1` 獲取當前 L2 VB (`L2_vb`)。
     2. 透過 `issue_40D6` (next_n=1) 獲取最後一個可用的替換區塊地址 (`next_replacement_block_1`)。
     3. 透過 `issue_C012` (fail_type=0, block_info_list_count=2) 同時對 **當前 L2 VB** 與 **最後一個替換區塊** 注入 Program Fail。此動作模擬寫入時主區塊失敗，嘗試替換時替換區塊也失敗，且無其他備用區塊可用的極端情境。
     4. 執行 Write10 命令寫入 1 個 Block 長度資料 (LBA 0)。
     5. 捕獲執行結果，預期會拋出 `G_TIMEOUT_ALL` 異常。
     6. 在異常捕獲區塊中，檢查韌體 Assert 編號。
   - 預期結果：
     - Write10 命令執行超時並拋出 `G_TIMEOUT_ALL`。
     - `api.get_fw_assert_number()` 返回值必須嚴格等於 **0x202**。
     - 這證實韌體在備用區塊完全不可用且無法完成寫入時，觸發了特定的 Assert 機制（FW Stuck），而非無限期重試或返回錯誤碼。