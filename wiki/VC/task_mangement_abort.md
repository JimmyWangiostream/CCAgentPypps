# Test Spec: UFS Task Management Abort Mechanism Verification

## Verification Criterion (VC)
驗證 UFS 主機控制器與裝置間的 Task Management (TM) 機制在特定命令序列下的行為：確認在 LUN 0 的 LBA 0 處執行 Write10 (256 LBA) 並觸發 FUA (Force Unit Access) 後，緊接著發送多個 Read10 (10 LBA) 命令。透過 `push_abort_task` 將其中一個 Read10 標記為 Abort Target，並由 Host 發送 TM 請求（隱含於 `send` 與 `check_if_target_is_aborted` 的邏輯中，通常對應 TM Function 0x03 ABORT TASK），驗證該特定 Target 命令是否被裝置正確終止，且後續命令或狀態機是否恢復正常或符合預期錯誤碼。此測試旨在驗證 UFS 協議層級中，Host 主動干預並中止特定 I/O 請求的硬體/韌體響應邏輯。

## Test Case (TC) Checkpoints
1. [TM_Abort_Task_Execution_Check]：
   - 動作：
     1. 初始化命令序列：針對 LUN 0, LBA 0 發送 Write10 命令，長度為 256 LBA，並設定 FUA=1（強制單元訪問，確保資料寫入非揮發性記憶體）。
     2. 發送多個 Read10 命令：針對 LUN 0, LBA 0 發送長度為 10 LBA 的讀取命令。
     3. 標記 Abort Target：在命令隊列中，將第三個發送的 Read10 命令（索引為 `target_idx`）標記為待中止的目標。
     4. 觸發 TM 請求：呼叫 `api.push_abort_task(target_idx)` 獲取 TM 請求的索引 `tm_idx`，並透過 `ExecuteCMD.send(clear_on_success=False)` 將整個命令序列（包含 Write, 多個 Read, 以及隱含的 TM 請求）發送給 UFS 裝置。
     5. 驗證結果：呼叫 `api.check_if_target_is_aborted` 檢查 `target_idx` 對應的命令是否被正確中止，並驗證 `tm_idx` 對應的 TM 請求是否成功執行。
   - 預期結果：
     - `target_idx` 對應的 Read10 命令狀態必須為 ABORTED（通常對應 SCSI Sense Key 為 ABORTED COMMAND 或 UFS 狀態碼為 TASK_SET_FULL/ABORTED）。
     - TM 請求本身必須成功執行，無返回錯誤。
     - 其他未標記為 Abort 的命令（如 Write10 和其他 Read10）應根據裝置內部調度繼續執行或返回正常狀態，具體取決於裝置對 TM 請求的實現（例如是否清除整個 Task Set 或僅中止特定 Tag）。
     - 此驗證確保 Host 能夠精確控制並終止特定的 I/O 請求，防止懸掛或錯誤狀態的 I/O 影響系統穩定性。