# Test Spec: REH (Read Error Handling) Buffer Lifecycle & State Consistency Verification

## Verification Criterion (VC)
驗證韌體中 Read Error Handling (REH) 模組的資源管理與狀態追蹤機制：
1. **資源釋放保護**：確認在 REH 緩衝區未分配時，強制執行釋放操作 (D014 Option 7, Action=1) 會觸發硬體錯誤狀態 (TARGET_FAILURE/CHECK_CONDITION)，防止非法記憶體操作。
2. **狀態初始化檢查**：確認在分配緩衝區前，M_RAM 中的 REH Tracing 數據與 SURE ARC 數據均為全零 (Empty)，確保無殘留狀態干擾。
3. **錯誤注入與追蹤**：確認在特定 LUN/LBA 頁面注入 UECC 錯誤後，REH 模組能正確記錄 Tracing 資訊與 ARC 數據，且數據非零 (Non-empty)。
4. **資源釋放與狀態清除**：確認執行釋放緩衝區操作 (D014 Option 7, Action=0x1) 後，M_RAM 中的 REH Tracing 與 SURE ARC 數據必須被硬體自動清除為全零，驗證資源回收機制的有效性。

## Test Case (TC) Checkpoints

1. [Case01_Illegal_Release_Check]：
   - 動作：在 LUN 配置完成且尚未分配 REH 緩衝區的情境下，發送 Vendor Command `D014` Option 7，設定 `action = 0x1` (Release Codeword Buffer)。
   - 預期結果：UFS 協議回應必須為 `UPIUResponse.TARGET_FAILURE` 且 SCSI Status 必須為 `CHECK_CONDITION`。此驗證硬體/韌體具備保護機制，拒絕在無有效緩衝區指針時執行釋放動作。

2. [Case02_Pre_Allocation_Clean_State_Check]：
   - 動作：針對 Normal LUN (LUN0, TLC) 與 EM1 LUN (LUN1, SLC)，分別隨機選取 LBA 並透過 VU `4051` 轉換為物理地址 (PBA: Die, Plane, Block, Page)。針對該物理頁面的所有區塊類型 (TLC/MLC/SLG Page) 與頁面類型，發送 VU `D014` Option 7 設定 `action = 0x0` (Allocate Codeword Buffer)。隨後發送 VU `4014` Option 1 讀取 M_RAM 中的 REH Tracing 數據，並發送 VU `4014` Option 5 讀取 SURE ARC 數據。
   - 預期結果：REH Tracing 數據陣列中的所有元素必須等於 `0`；SURE ARC 數據陣列中的所有元素必須等於 `0`。驗證在分配緩衝區後，追蹤狀態機處於初始空閒狀態。

3. [Case03_PBA_LBA_Roundtrip_Check]：
   - 動作：針對上述選定的物理地址，發送 VU `4052` 將 PBA (Die, Plane, Block, Page, Offset) 轉換回邏輯地址 (LBA)。
   - 預期結果：回傳的 `la.lun.value` 必須等於原始測試 LUN；回傳的 `la.lba.value` 必須大於等於 0 且小於該 LUN 的總容量長度。驗證物理地址與邏輯地址映射表的正確性，確保後續錯誤注入目標無誤。

4. [Case04_Error_Injection_Tracing_Check]：
   - 動作：針對 Normal LUN (TLC) 或 EM1 LUN (SLC)，根據 REH 步驟列表 (`reh_steps`)，發送 VU `D014` 設定 Read Recovery Module 參數。隨後發送 SCSI `READ10` 命令讀取目標 LBA (長度 1 Block)。對於 SLC LUN，此步驟會額外觸發 `flipbit_on_SLC_single_page` 函數，在特定頁面隨機翻轉 150 個位元 (Bit Flip) 以產生 UECC 錯誤。
   - 預期結果：讀取命令執行完畢後，硬體應檢測到錯誤並觸發 REH 機制。

5. [Case05_Post_Injection_NonEmpty_State_Check]：
   - 動作：在錯誤注入完成後，立即發送 VU `4014` Option 1 讀取 M_RAM 中的 REH Tracing 數據，並發送 VU `4014` Option 5 讀取 SURE ARC 數據。
   - 預期結果：REH Tracing 數據陣列中**至少有一個元素不為 0**；SURE ARC 數據陣列中**至少有一個元素不為 0**。驗證韌體成功捕捉錯誤事件並寫入追蹤資訊與 ARC (Adaptive Read Compensation) 數據。

6. [Case06_Post_Release_Clean_State_Check]：
   - 動作：發送 VU `D014` Option 7 設定 `action = 0x1` (Release Codeword Buffer) 以釋放 REH 緩衝區。隨後再次發送 VU `4014` Option 1 讀取 REH Tracing 數據，並發送 VU `4014` Option 5 讀取 SURE ARC 數據。
   - 預期結果：REH Tracing 數據陣列中的所有元素必須恢復為 `0`；SURE ARC 數據陣列中的所有元素必須恢復為 `0`。驗證釋放緩衝區時，硬體會自動清除相關的追蹤狀態與 ARC 數據，確保下一次分配時的狀態乾淨。