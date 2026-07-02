# Test Spec: UFS Host Controller Command Queue Depth & Unmap Atomicity Stress Test

## Verification Criterion (VC)
驗證 UFS 主機端命令序列器（Command Sequence Executor）在極高並發與混合指令（Write + Unmap）壓力下的行為：
1. **命令隊列溢出處理**：確認當連續發送的 Write10 與 Unmap 命令總數超過硬體命令隊列深度限制時，執行器能正確拋出 `PATTERN_ASSERT_EXECUTOR_CMD_LIST_IS_FULL` 異常，且不導致系統崩潰。
2. **FUA (Force Unit Access) 持久化驗證**：確認所有寫入操作均設置 `fua=1`，強制控制器在返回成功前將資料物理寫入 Flash，驗證資料完整性（Data Integrity）。
3. **Unmap 與 Write 的原子性與 LBA 衝突測試**：驗證在單一命令序列中，針對 LBA 0-2 的 12KB 寫入與 LBA 0-1 的 Unmap 操作並存時，韌體是否能正確處理邏輯區塊地址（LBA）的重疊與釋放，並確保 `data1` 與 `data2` 的特定標記位元（0x66, 0x77, 0x88, 0x99）在寫入後可被正確讀取或驗證（若後續有讀取步驟，此處主要驗證寫入路徑的穩定性與無死鎖）。
4. **循環穩定性**：確認在 1000 次循環中，命令隊列的清空（`ExecuteCMD.clear()`）與重新填充機制正常，無記憶體洩漏或狀態殘留。

## Test Case (TC) Checkpoints
1. [Case01_Command_Queue_Full_Handling_Check]：
   - 動作：在 `while True` 迴圈內，連續 enqueue 三個 Write10 命令（LBA 0-2, 12KB, FUA=1）與一個 Unmap 命令（LBA 0-1, 4KB, FUA=1），總計 4 個命令。由於硬體命令隊列深度有限（通常小於 4 或剛好為 4 但需考慮內部處理延遲），當隊列滿時，程式碼預期會觸發 `api.PATTERN_ASSERT_EXECUTOR_CMD_LIST_IS_FULL` 異常。記錄異常發生時的隊列大小 `len(ExecuteCMD._cmd_list)`。
   - 預期結果：程式碼必須成功捕獲異常，且 `logger.warning` 輸出的隊列大小應等於或接近硬體定義的最大命令隊列深度（Max Command Queue Depth）。這證明測試框架能正確識別硬體資源瓶頸，且異常處理機制未導致腳本終止。

2. [Case02_FUA_Data_Integrity_Persistence_Check]：
   - 動作：執行 `ExecuteCMD.send(clear_on_success=False)` 發送命令序列。針對 `data1`（長度 12KB，由 3 個 4KB 塊組成，首字節 0x66，末字節 0x77）寫入 LBA 0-2；針對 `data2`（長度 4KB，首字節 0x88，末字節 0x99）寫入 LBA 3。所有命令均設置 `fua=1`。隨後通過 `ExecuteCMD.read_response(idx)` 讀取每個命令的響應狀態。
   - 預期結果：所有 Write10 命令的響應狀態碼（Status Byte）必須為 0x00（Good Status）。由於設置了 FUA，控制器保證資料已持久化至 Flash。雖然腳本未直接執行 Read10 驗證內容，但此步驟驗證了在高負載下 FUA 命令的提交與完成機制正常，無超时或錯誤返回。

3. [Case03_Unmap_Atomicity_and_LBA_Overlap_Check]：
   - 動作：在同一命令序列中，對 LBA 0-2 執行 Write10，同時對 LBA 0-1 執行 Unmap。Unmap 命令指定 `lun=0, lba=0, length=1`（即釋放 LBA 0 對應的 4KB 區塊）。檢查 Unmap 命令的響應狀態。
   - 預期結果：Unmap 命令的響應狀態碼必須為 0x00。這驗證了 UFS 控制器能夠正確處理寫入與 Unmap 在同一時間窗口內的 LBA 重疊情況。韌體應優先處理寫入的持久化，並正確標記 LBA 0 為未映射狀態，而不引發邏輯錯誤或硬體掛起。

4. [Case04_1000_Cycle_Stability_Check]：
   - 動作：重複上述命令序列 1000 次。每次循環結束後執行 `ExecuteCMD.clear()` 清空命令列表。監控整個過程中的異常拋出次數與隊列大小變化。
   - 預期結果：1000 次循環必須全部完成，無未捕獲的異常（Unhandled Exception）。`ExecuteCMD.clear()` 必須確保 `ExecuteCMD._cmd_list` 在每次 `send` 後歸零，為下一次循環準備空隊列。這驗證了測試腳本在長期壓力測試下的記憶體管理與狀態機恢復能力。