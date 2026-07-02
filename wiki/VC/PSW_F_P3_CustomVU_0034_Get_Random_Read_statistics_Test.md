# Test Spec: UFS Random Read (RR) Detection & Abort Mechanism Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Random Read (RR) 檢測模組的觸發、中斷與重置行為：
1. **RR 觸發與中斷機制**：確認在 Normal、EM1、Boot A/B LUN 上，當觸發小區塊隨機讀取（Small Chunk RR）時，韌體能正確計數 `Small_chunk_RR_enter_counter` 與 `Small_chunk_RR_exit_counter`。
2. **SSU 電源循環中斷**：確認透過 `StartStopUnit` (SSU) 執行 Sleep (0x02) 與 Active (0x01) 電源循環時，能強制中斷正在進行的 RR 流程，並使 RR 統計計數器正確遞增（代表一次完整的 Enter/Exit 週期完成）。
3. **ATS 自動中斷**：確認在 Idle 狀態下觸發 ATS (Auto-Transition State) 時，RR 流程被中斷，且 `Random_Read_exit_cause` 必須為 3 (ATS Abort) 或 1 (SSU Abort)，並伴隨計數器遞增。
4. **Reset 重置行為**：確認執行 HW_RESET、Reset-N、Endpoint Reset 或 UniPro Reset 後，RR 統計計數器（Enter/Exit Counter 及 Exit Cause）必須全部歸零，代表韌體狀態機已完全重置。
5. **RR 模組開關控制**：確認透過 Vendor Command `0xC0F4` 禁用 RR 檢測模組後，即使觸發隨機讀取事件，統計計數器仍保持為 0，驗證模組開關功能的正確性。

## Test Case (TC) Checkpoints

1. [Case01_RR_Abort_By_Write_Check]：
   - 動作：針對指定 LUN (Normal/EM1/BootA/BootB) 執行 `rand_read_event` 觸發隨機讀取，隨後立即發送 `Write10` (LUN0, LBA0, Length1) 寫入命令以強制中斷讀取。透過 Vendor Command `0x409F` 讀取隨機讀取統計資訊。
   - 預期結果：在 Loop 1 到 15 的循環中，`getrandread.Small_chunk_RR_enter_counter.value` 必須嚴格等於當前 Loop 數值；`getrandread.Small_chunk_RR_exit_counter.value` 必須嚴格等於當前 Loop 數值。這代表每次寫入中斷都成功終止了一次 RR 事件，且計數器同步更新。

2. [Case02_RR_Abort_By_SSU_Check]：
   - 動作：在當前 RR 計數基礎上，再次執行 `rand_read_event` 觸發 RR，隨後發送 `StartStopUnit` 命令將 UFS Device 進入 Sleep 狀態 (`power_condition=0x02`)，接著發送 `StartStopUnit` 命令喚醒 Device (`power_condition=0x01`)。透過 `0x409F` 讀取統計資訊。
   - 預期結果：`getrandread.Small_chunk_RR_enter_counter.value` 必須等於上一次記錄值加 1；`getrandread.Small_chunk_RR_exit_counter.value` 必須等於上一次記錄值加 1。這代表 SSU 電源循環成功中斷了 RR 流程，並被韌體識別為一次有效的 Exit 事件。

3. [Case03_RR_Abort_By_ATS_Check]：
   - 動作：在當前 RR 計數基礎上，執行 `rand_read_event` 觸發 RR，隨後執行 `time.sleep(2)` 讓系統進入 Idle 狀態以觸發 ATS (Auto-Transition State)。透過 `0x409F` 讀取統計資訊。
   - 預期結果：
     1. `getrandread.Small_chunk_RR_enter_counter.value` 必須等於上一次記錄值加 1。
     2. `getrandread.Small_chunk_RR_exit_counter.value` 必須等於上一次記錄值加 1。
     3. `getrandread.Random_Read_exit_cause.value` 必須等於 3 (代表 ATS 中斷) 或 1 (代表 SSU 中斷，視具體實作而定，但代碼邏輯允許這兩種值)。這確認 ATS 機制能正確中斷 RR 並記錄退出原因。

4. [Case04_RR_Reset_By_Hardware_Reset_Check]：
   - 動作：針對 `api.Dcmd5ResetType.HW_RESET` 類型，執行 `rand_read_event` 觸發 RR，隨後呼叫 `api.init_tester_to_unit_ready(resetmode=HW_RESET, powerdown=True)` 執行硬體重啟。待 Device 恢復 Unit Ready 後，透過 `0x409F` 讀取統計資訊。
   - 預期結果：`getrandread.Small_chunk_RR_enter_counter.value` 必須等於 0；`getrandread.Small_chunk_RR_exit_counter.value` 必須等於 0；`getrandread.Random_Read_exit_cause.value` 必須等於 0。這確認 HW_RESET 能完全清除 RR 模組的內部狀態與計數器。

5. [Case05_RR_Module_Disable_Check]：
   - 動作：在 HW_RESET 確保計數器為 0 後，發送 Vendor Command `0xC0F4` 設定 `rr_enable=0` (禁用 RR 檢測) 與 `pre_read_en=1`。隨後執行 `rand_read_event` 觸發隨機讀取事件。最後透過 `0x409F` 讀取統計資訊。
   - 預期結果：`getrandread.Small_chunk_RR_enter_counter.value` 必須等於 0；`getrandread.Small_chunk_RR_exit_counter.value` 必須等於 0；`getrandread.Random_Read_exit_cause.value` 必須等於 0。這確認當 RR 檢測模組被禁用時，即使發生隨機讀取行為，韌體也不會記錄任何 RR 統計數據。