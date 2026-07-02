# Test Spec: UFS Host Controller Command Queue Depth & Unmap Atomicity Stress Test

## Verification Criterion (VC)
驗證 UFS 主機端控制器（Host Controller）在極端高負載與混合 I/O 情境下的命令佇列管理與邏輯區塊地址（LBA）映射一致性：透過 1000 次循環執行「寫入 12KB (3x 4KB) + 寫入 4KB + Unmap 1 LBA + 讀取 3 LBA」的原子性命令序列，並強制觸發 `cmd_seq` 佇列滿（Full）異常以測試韌體對佇列溢出的容錯機制。核心驗證點在於確認 `Unmap` 操作在 `Write` 之後、`Read` 之前執行時，針對 LBA 0 的 Unmap 是否正確導致後續對 LBA 0 的 `Read10` 返回錯誤（或特定狀態碼），同時驗證 LBA 1 與 LBA 3 的資料完整性不受 Unmap 影響，且 `clear_on_success=False` 設定下佇列狀態能正確重置以支援連續循環。

## Test Case (TC) Checkpoints
1. [Case01_QueueOverflow_FaultTolerance_Check]：
   - 動作：進入 1000 次循環，每次循環構建包含 2 個 `Write10`、1 個 `Unmap` 和 3 個 `Read10` 的命令序列。當 `ExecuteCMD._cmd_list` 長度達到硬體限制觸發 `PATTERN_ASSERT_EXECUTOR_CMD_LIST_IS_FULL` 異常時，捕獲該異常並記錄警告，隨後執行 `ExecuteCMD.send(clear_on_success=False)` 發送當前佇列，接著遍歷讀取所有回應並執行 `ExecuteCMD.clear()` 清空佇列，確保下一次循環能重新填充佇列。
   - 預期結果：系統不應崩潰或進入死鎖；異常捕獲機制必須成功攔截佇列滿事件；`send` 指令必須成功將已排程的命令發送給 UFS 裝置；`clear` 指令必須成功重置內部命令列表狀態，使得下一次循環能正常 enqueue 新命令，證明韌體具備佇列滿時的優雅降級與恢復能力。

2. [Case02_Unmap_After_Write_Data_Corruption_Check]：
   - 動作：在佇列未滿的正常循環中，寫入 `data1` (0x5B..., 首字節 0x66, 尾字節 0x77) 至 LBA 0-2 (長度 3)，寫入 `data2` (0xAB..., 首字節 0x88, 尾字節 0x99) 至 LBA 3 (長度 1)。緊接著執行 `Unmap` 操作，指定 LBA 0 長度 1。最後執行讀取：LBA 0 (長度 1)、LBA 1 (長度 1)、LBA 3 (長度 1)。檢查 `Read10` 對 LBA 0 的回應狀態碼及資料內容，以及 LBA 1 和 LBA 3 的資料內容。
   - 預期結果：
     - 針對 LBA 0 的 `Read10`：由於在讀取前執行了 Unmap，該 LBA 應被標記為未映射或無效。預期回應狀態碼應為錯誤狀態（如 CHECK CONDITION, Sense Key 為 ILLEGAL REQUEST 或 NOT READY），或者若韌體允許讀取未映射區塊，其返回的 payload 應為全 0 或特定填充值（取決於 UFS 規範實現），但絕不可能是之前寫入的 `data1` 內容。
     - 針對 LBA 1 的 `Read10`：該 LBA 未被 Unmap 影響，預期返回的 payload 首字節必須等於 0x5B (data1 的填充值)，尾字節必須等於 0x77 (data1 的尾字節)，驗證寫入資料的完整性。
     - 針對 LBA 3 的 `Read10`：該 LBA 未被 Unmap 影響，預期返回的 payload 首字節必須等於 0x88 (data2 的首字節)，尾字節必須等於 0x99 (data2 的尾字節)，驗證不同資料模式的寫入正確性。

3. [Case03_Stress_Cycle_Continuity_Check]：
   - 動作：執行完整的 1000 次循環，監控每次循環結束時 `ExecuteCMD.clear()` 後的佇列狀態，並確保下一次循環的 `enqueue` 操作不會因為殘留狀態而失敗。特別關注在觸發過 `cmd_seq is full` 警告後的後續循環，確認命令序列的構建邏輯（Write10 -> Write10 -> Unmap -> Read10 x3）能穩定重複執行。
   - 預期結果：所有 1000 次循環均應成功完成，無累積性錯誤；`clear_on_success=False` 的設定確保即使命令發送成功，佇列資源也能被正確釋放以供下一次重用；證明測試腳本在長時間高頻命令提交下，記憶體與命令佇列狀態管理是穩定且無洩漏的。