# Test Spec: UFS Pre-Read Abort Mechanism & Statistics Reset Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Pre-Read (預讀) 機制在不同中斷情境下的狀態機行為與統計計數器（Statistics Counters）的準確性：
1. **Write Abort Check**：確認當 Pre-Read 進行中遭遇 Write 命令時，`pre_read_enter_counter` 與 `pre_read_exit_counter` 同步遞增，且 `pre_read_exit_cause` 明確標記為 `3` (Write Abort)，並正確記錄觸發的 LUN ID。
2. **SSU Abort Check**：確認當 Pre-Read 進行中遭遇 Start/Stop Unit (SSU) 電源狀態切換（Sleep/Active）時，計數器同步遞增，驗證韌體能正確處理電源管理事件對預讀緩衝區的強制終止。
3. **ATS Abort Check**：確認當 Pre-Read 進入 ATS (Auto-Transition State) 閒置狀態時，計數器遞增且 `pre_read_exit_cause` 為 `2` 或 `3`，驗證閒置狀態轉換能正確中斷預讀。
4. **Reset Clear Check**：確認執行 HW_RESET 後，所有 Pre-Read 相關統計欄位（Enter/Exit Counter, Cause, Buffer Counter, LBA, LUN）必須被硬體或韌體強制清零，確保狀態機重置。
5. **Feature Disable Check**：確認透過 Vendor Command `0xC0F4` 禁用 Pre-Read 偵測模組後，即使執行序列讀取，所有統計欄位必須保持為 `0`，驗證功能開關的有效性。

## Test Case (TC) Checkpoints

1. **[Case01_Write_Abort_PreRead_Check]**：
   - 動作：針對指定 LUN (Normal/EM1/BootA/BootB) 發送 32 個連續的 `Read10` 命令 (QD=1, 每次 32 LBA)，在隊列中插入一個 `Write10` 命令以中斷 Pre-Read 流程。發送命令後，透過 Vendor Command `0x4090` 讀取 Pre-Read Statistics。
   - 預期結果：
     - `pre_read_enter_counter` 必須等於當前 Loop 次數 (例如 Loop 1 時為 1)。
     - `pre_read_exit_counter` 必須等於當前 Loop 次數。
     - `pre_read_exit_cause` 必須嚴格等於 `3` (代表 Write Abort)。
     - `pre_read_lun` 必須等於當前測試的 LUN ID (若測試 LUN 為 0xB0 則預期為 BootA LUN ID)。

2. **[Case02_SSU_Abort_PreRead_Check]**：
   - 動作：在 Pre-Read 序列讀取過程中，發送 `StartStopUnit` 命令將 UFS Device 進入 Sleep 狀態 (`power_condition=0x02`)，隨後立即發送 `StartStopUnit` 命令喚醒 Device (`power_condition=0x01`)。發送命令後，透過 `0x4090` 讀取統計數據。
   - 預期結果：
     - `pre_read_enter_counter` 必須比上一次讀取值增加 1。
     - `pre_read_exit_counter` 必須比上一次讀取值增加 1。
     - 驗證計數器在電源狀態切換事件中正確記錄了一次 Pre-Read 的進入與退出。

3. **[Case03_ATS_Abort_PreRead_Check]**：
   - 動作：發送序列 `Read10` 命令觸發 Pre-Read，隨後執行 `time.sleep(2)` 讓系統進入 ATS (Auto-Transition State) 閒置模式。等待後透過 `0x4090` 讀取統計數據。
   - 預期結果：
     - `pre_read_enter_counter` 必須遞增 1。
     - `pre_read_exit_counter` 必須遞增 1。
     - `pre_read_exit_cause` 必須等於 `2` (ATS Transition) 或 `3` (Write/Other Abort)，驗證 ATS 狀態轉換能作為有效的 Pre-Read 終止條件。

4. **[Case04_Reset_Clear_Statistics_Check]**：
   - 動作：在 Pre-Read 觸發後，執行 `api.init_tester_to_unit_ready` 進行 HW_RESET (Hard Reset)。重置完成後，立即透過 `0x4090` 讀取 Pre-Read Statistics。
   - 預期結果：
     - `pre_read_enter_counter` 必須為 `0`。
     - `pre_read_exit_counter` 必須為 `0`。
     - `pre_read_exit_cause` 必須為 `0`。
     - `pre_read_avail_buffer_counter` 必須為 `0`。
     - `pre_read_start_lba` 必須為 `0`。
     - `pre_read_lun` 必須為 `0`。
     - 驗證硬體重置能徹底清除 Pre-Read 狀態機與相關計數器。

5. **[Case05_Disable_PreRead_Module_Check]**：
   - 動作：透過 Vendor Command `0xC0F4` 發送參數 `rr_enable=1, pre_read_en=0` 以禁用 Pre-Read 偵測模組。隨後執行與 Case01 相同的序列 `Read10` 命令觸發讀取。最後透過 `0x4090` 讀取統計數據。
   - 預期結果：
     - `pre_read_enter_counter` 必須為 `0`。
     - `pre_read_exit_counter` 必須為 `0`。
     - `pre_read_exit_cause` 必須為 `0`。
     - `pre_read_avail_buffer_counter` 必須為 `0`。
     - `pre_read_start_lba` 必須為 `0`。
     - `pre_read_lun` 必須為 `0`。
     - 驗證當 Pre-Read 功能被軟體禁用時，韌體不會記錄任何 Pre-Read 事件，即使硬體層面可能仍有預讀行為，但統計模組必須保持靜默。