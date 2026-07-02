# Test Spec: FBO (Flash Block Optimization) Write Buffer Configuration & Execution Flow

## Verification Criterion (VC)
驗證 UFS 韌體中 FBO (Flash Block Optimization) 模組的寫入緩衝區 (Write Buffer) 配置機制與優化流程觸發行為：
1. **Pre-process 階段**：確認透過 Write10 命令對 LUN 0 進行特定 LBA 序列（倒序 44~0 及 0~100）的寫入操作，旨在建立特定的資料分佈以觸發 FBO 分析所需的條件。
2. **Step1 階段 - 配置與分析**：驗證透過 API 設定 `FboWriteBufferStruct0101` 時，韌體能否正確解析包含 10 個 Entry 的緩衝區結構（每個 Entry 定義 `start_lba` 與 `length`），並確認 `car=1` (Cache Area Reserved?) 標誌被正確寫入。接著，驗證 `START_FBO_ANALYSIS` 控制命令能否成功啟動 FBO 分析流程，並確認 `ProgressState` 狀態機進入分析中狀態。
3. **Step1 階段 - 優化與執行**：驗證在讀取當前 ReadBuffer 狀態後，透過 `set_fbo_execute_threshold(value = 0x0)` 將優化執行閾值重置為 0，隨後發送 `START_FBO_OPTIMIZATION` 命令，確認韌體能根據配置的 Write Buffer 資訊與閾值條件，啟動 Flash Block 的邏輯區塊到實體區塊映射優化流程，並最終確認 `ProgressState` 反映優化流程的啟動或完成狀態。

## Test Case (TC) Checkpoints
1. [PreProcess_DataPattern_Injection]：
   - 動作：針對 LUN 0 發送 Write10 命令，寫入 LBA 0 長度 101 的資料（FUA=1, delay=1ms）；隨後透過迴圈執行 45 次 Write10 命令，分別寫入 LBA 44, 43, ..., 0 各 1 個區塊（FUA=1, delay=1ms）。
   - 預期結果：所有 Write10 命令必須返回 Success 狀態碼；LUN 0 的 LBA 0 至 44 區域必須包含由測試腳本生成的特定寫入模式，為後續 FBO 分析提供基礎資料分佈。

2. [FBO_WriteBuffer_Configuration_Check]：
   - 動作：呼叫 `api.FboVersion0101().get_descriptor()` 更新描述符；建立包含 10 個 `FboWriteBufferEntry0101` 的列表，其中第 i 個 Entry 設定 `start_lba = i * 100` 且 `length = 100`；組裝 `FboWriteBufferStruct0101`，設定 `fbo_type=0`, `fbo_version=0`, `car=1`，並透過 `fbo.set_fbo_write_buffer()` 發送給韌體。
   - 預期結果：韌體必須接受該結構體，並在內部 FBO 模組中正確儲存這 10 個緩衝區條目；`car=1` 標誌必須被寫入至對應的韌體暫存器或記憶體結構中，表示啟用 Cache Area Reserved 相關功能。

3. [FBO_Analysis_Execution_Check]：
   - 動作：呼叫 `fbo.set_fbo_control(value = api.FboControlType.START_FBO_ANALYSIS)` 發送分析啟動命令；隨後呼叫 `fbo.get_fbo_progress_state()` 讀取當前進度狀態。
   - 預期結果：韌體必須啟動 FBO 分析流程；`get_fbo_progress_state()` 返回的狀態碼必須指示系統處於 "Analyzing" 或 "Busy" 狀態（非 Idle 或 Error），證明分析流程已正確觸發。

4. [FBO_Optimization_Threshold_Set_Check]：
   - 動作：呼叫 `fbo.get_fbo_read_buffer()` 讀取當前 ReadBuffer 結構；呼叫 `fbo.set_fbo_execute_threshold(value = 0x0)` 將優化執行閾值設定為 0。
   - 預期結果：韌體必須將內部 FBO 優化閾值暫存器更新為 0x0；讀取 ReadBuffer 的操作必須成功返回有效的結構體數據，無記憶體訪問錯誤。

5. [FBO_Optimization_Execution_Check]：
   - 動作：呼叫 `fbo.set_fbo_control(value = api.FboControlType.START_FBO_OPTIMIZATION)` 發送優化啟動命令；隨後呼叫 `fbo.get_fbo_progress_state()` 讀取當前進度狀態。
   - 預期結果：韌體必須根據之前設定的 Write Buffer 配置與閾值 0x0，啟動 FBO 優化流程；`get_fbo_progress_state()` 返回的狀態碼必須指示系統處於 "Optimizing" 或 "Busy" 狀態，證明優化流程已正確觸發並執行。