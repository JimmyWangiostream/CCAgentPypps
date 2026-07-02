# Test Spec: VC-16 (4.a) Erase Fail with Hidden Area Spare Exhaustion Test

## Verification Criterion (VC)
驗證當韌體在執行 L2 VB 切換過程中遭遇 Erase Fail，且同時導致 L2 區塊與 BBT (Bad Block Table) 區塊均標記為失效時，若 Hidden Area 中無剩餘的 Spare Block 可供替換，韌體必須進入死鎖狀態（Stuck）。具體行為為：Host 發送 Write10 指令時韌體不應回應成功或標準錯誤碼，而是觸發內部 Assert 0xB7 並掛起，同時確認 Bad Block 計數器正確增加 2，且 L2 與 BBT 的物理地址資訊已正確記錄於 BBT 表中。

## Test Case (TC) Checkpoints
1. [Case01_Preparation_and_Fail_Injection]：
   - 動作：
     1. 透過 Vendor Command (VC) 40C1 讀取當前 L2 Open Logical VB (L2_vb)。
     2. 透過 VC 40DC 讀取下一個待分配的 L2 VB (L2_vb_next)。
     3. 透過 VC 405E 讀取初始 Bad Block 計數 (BB_count)。
     4. 透過 VC 40D6 查詢 Hidden Area (pool_type=2) 中預測的下一個替換區塊 (next_replacement_block/ce/plane)。
     5. 透過 VC C012 注入 Erase Fail (fail_type=1)，目標為兩個物理區塊：
        - Block 0: L2_vb_next (CE=0, Plane=0)
        - Block 1: next_replacement_block (從 VC 40D6 解析出的 CE/Plane/Block)
     6. 從 LBA 0 開始發送連續 Write10 指令，每次寫入 WRITE_10_MAX_BLOCK_LEN 長度，並持續透過 VC 40C1 監控 L2_vb 是否發生切換。
   - 預期結果：
     - 初始 BB_count 被正確記錄。
     - VC C012 成功注入 Erase Fail，使得 L2_vb_next 與 Hidden Area 的替換區塊均處於失效狀態。
     - 在 L2_vb 發生切換前，韌體應正常處理寫入請求。

2. [Case02_Firmware_Stuck_Verification]：
   - 動作：
     1. 持續發送 Write10 指令直到 L2_vb 發生切換（觸發韌體嘗試將 L2_vb_next 標記為 Active 並進行 Erase 操作）。
     2. 由於 L2_vb_next 已被注入 Erase Fail，且其對應的替換區塊（Hidden Area Spare）也已被標記為失效（或即將被使用但無法完成替換邏輯），韌體應嘗試尋找新的 Spare Block。
     3. 由於 Hidden Area 無可用 Spare Block（由 VC 40D6 預判及注入邏輯確保），韌體應觸發 Assert 0xB7。
     4. 捕獲 Write10 指令的回應，預期會拋出 `G_TIMEOUT_ALL` 異常。
     5. 檢查韌體 Assert 號碼是否為 0xB7。
   - 預期結果：
     - Write10 指令超時，拋出 `G_TIMEOUT_ALL`。
     - `api.get_fw_assert_number()` 返回值必須等於 `0xB7`。
     - L2_vb 號碼在超時後必須保持不變（未發生切換），證明韌體在切換過程中死鎖。

3. [Case03_BBT_and_BB_Count_Integrity_Check]：
   - 動作：
     1. 在韌體死鎖前（或在 pre_process 中模擬正常流程以驗證數據一致性，若死鎖發生則需依賴 pre_process 中的驗證邏輯或重新啟動後的狀態檢查，此處依據代碼邏輯，pre_process 中未捕獲異常，故此檢查點基於代碼中 `pass` 前的驗證邏輯，即假設韌體在死鎖前或特定測試模式下完成了狀態更新）。
     2. 透過 VC 405E 再次讀取 Bad Block 計數 (BB_count_new)。
     3. 透過 `program_fail_api.calculate_bbt` 解析 VC 405E 返回的 BBT 數據。
     4. 檢查 BBT 中是否包含目標 L2 區塊 (L2_vb_next) 和目標 BBT 替換區塊 (next_replacement_block) 的物理地址資訊。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 2`。
     - BBT 數據中必須能找到與 `target_data_L2` (L2_vb_next 的 CE/Plane/Block) 完全匹配的條目。
     - BBT 數據中必須能找到與 `target_data_BBT` (next_replacement_block 的 CE/Plane/Block) 完全匹配的條目。
     - 這證明在觸發死鎖前，韌體已正確將這兩個區塊標記為 Bad Block 並更新計數器。