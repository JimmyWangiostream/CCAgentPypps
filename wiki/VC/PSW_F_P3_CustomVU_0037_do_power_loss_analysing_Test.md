# Test Spec: UFS APL (0007) Power Loss Analysis & RPMB Integrity Verification

## Verification Criterion (VC)
驗證 UFS 韌體在異常掉電（SPOR）情境下的 LWP (Last Written Page) 狀態一致性、APL 參數持久化能力，以及 RPMB 區域在 Key 清除與重設過程中的資料完整性與安全機制：
1. **LWP 一致性檢查**：確認在 TLC L2 區塊寫入後，各 CE/Plane 的 LWP 狀態碼必須一致且非 0xFFFF，確保硬體層級寫入狀態追蹤正確。
2. **APL 參數持久化**：驗證 Vendor Command 0x409D 的參數寫入（Opcode 1）與讀取（Opcode 2）機制，並確認在無 SSU 的 HW_RESET 後，參數值仍保留於非揮發性記憶體中。
3. **SPOR 後狀態恢復**：確認 HW_RESET 後，透過 Blank Check (Opcode 3) 驗證已寫入頁面狀態為 0xE (Programmed)，未寫入頁面為 0x0 (Blank)；透過 Power Loss Check (Opcode 4) 驗證 LWP 狀態為 0x0 (Good/Valid)，FEP 狀態為 0x2，證明韌體能正確識別掉電前的最後寫入點。
4. **RPMB 安全機制**：驗證 RPMB Key 清除後，寫入資料不會被意外清零（資料保留），且 Key 重設後讀取特定偏移（LBA 0, Offset 228-484）的資料應為 0x00，確保安全區域的初始化邏輯符合規範。

## Test Case (TC) Checkpoints

1. [LWP_Consistency_Check_TLC_L2]:
   - 動作：配置 LUN 0 (Normal) 與 LUN 1 (EM1)，針對 LUN 0 寫入一個 TLC CE Page Size 的資料（長度為 `Plane_Per_Die * 4 * 3`）。取得 Open VB 資訊後，針對該 VB 執行 `issue_409D_to_do_power_loss_analysing` (Opcode 0) 進行 LWP 檢查。遍歷所有 CE 與 Plane，記錄每個 Plane 的 LWP 值。
   - 預期結果：
     - 同一 CE 下所有 Plane 的 LWP 值必須完全相同（`lwp == fisrtlwp`）。
     - 所有 Plane 的 LWP 值不得為 0xFFFF。
     - 若任一 Plane LWP 不一致或為 0xFFFF，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [APL_Parameter_Persistence_Check]:
   - 動作：
     1. 使用 Opcode 2 查詢 APL 參數最大索引值，預期返回值為 27。
     2. 迴圈讀取索引 0 到 27 的所有參數值並儲存。
     3. 迴圈寫入索引 0 到 27 的參數值（若原值為 0 則寫入 1，否則寫入原值），隨後立即讀取驗證寫入是否成功。
     4. 執行 `api.init_tester_to_unit_ready` 進行 HW_RESET，且 `powerdown = False`（即無 SSU 保護的硬體重啟）。
   - 預期結果：
     - 最大參數索引必須等於 27。
     - 寫入後的讀取值必須與寫入值 `m_val` 完全一致。
     - HW_RESET 後韌體應能正常初始化並進入 Ready 狀態，不發生崩潰。

3. [SPOR_Blank_Check_Verification]:
   - 動作：在 HW_RESET 後，使用 Opcode 3 (Blank Check) 針對之前寫入的 LWP 頁面範圍（`startpage` 到 `startpage + 1`）進行檢查。
     - 檢查索引 0 (LWP 頁面) 的 `blank_result`。
     - 檢查索引 1 (FEP 頁面) 的 `blank_result`。
   - 預期結果：
     - LWP 頁面 (`idx-startpage == 0`) 的 `blank_result` 必須等於 **0x0E** (代表已 Programming)。
     - FEP 頁面 (`idx-startpage == 1`) 的 `blank_result` 必須等於 **0x00** (代表 Truly Blank)。
     - 若不符合，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

4. [SPOR_PowerLoss_Check_Verification]:
   - 動作：在 HW_RESET 後，使用 Opcode 4 (Power Loss Check) 針對相同頁面範圍進行檢查。
     - 檢查索引 0 (LWP 頁面) 的 `blank_result`。
     - 檢查索引 1 (FEP 頁面) 的 `blank_result`。
   - 預期結果：
     - LWP 頁面 (`idx-startpage == 0`) 的 `blank_result` 必須等於 **0x00** (代表 Good/Valid)。
     - FEP 頁面 (`idx-startpage == 1`) 的 `blank_result` 必須等於 **0x02** (代表特定的 Power Loss 狀態標記)。
     - 若不符合，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

5. [RPMB_Key_Cleared_Data_Integrity_Check]:
   - 動作：
     1. 呼叫 `access_vendor_mode` 進入 Vendor 模式。
     2. 呼叫 `vuc_clear_rpmb_key` 清除 RPMB Region 0 的 Key。
     3. 初始化 RPMB 物件，嘗試讀取 Counter，若拋出 `SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET` 則確認 Key 已清除。
     4. 執行 `rpmb.rpmb_key_programming()` 重新設定 Key。
     5. 執行 `rpmb.rpmb_write_data(0, 4)` 寫入測試資料。
     6. 執行 `rpmb.rpmb_read_data(0, 4)` 讀取資料，並提取 LBA 0 中 Offset 228 到 484 的區段。
   - 預期結果：
     - 讀取到的資料區段 (`data_payload`) **不得全為 0x00**。若全為 0，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，證明 Key 清除後資料未被意外覆寫或擦除。

6. [RPMB_Post_Reset_Zero_Check]:
   - 動作：
     1. 再次呼叫 `vuc_clear_rpmb_key` 清除 Key。
     2. 重新初始化 RPMB 並執行 Key Programming。
     3. 執行 `rpmb.rpmb_read_data(0, 4)` 讀取資料。
     4. 提取 LBA 0 中 Offset 228 到 484 的區段。
   - 預期結果：
     - 讀取到的資料區段 (`data_payload`) **必須全為 0x00**。若存在非零值，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，證明 Key 重設後安全區域處於預期的初始化/空白狀態。