# Test Spec: UFS Host Controller Command Queue Depth & Unmap Atomicity Stress Test

## Verification Criterion (VC)
驗證 UFS 主機端控制器（Host Controller）在極端高負載（High Load）情境下的命令佇列管理與非同步操作行為：
1. **佇列溢出處理機制**：確認當連續提交多個 Read10 與 Unmap 命令導致內部命令佇列（Command List/Descriptor Ring）滿載時，驅動層（Driver/Script API）能否正確捕獲 `PATTERN_ASSERT_EXECUTOR_CMD_LIST_IS_FULL` 異常並進行容錯處理，而非導致系統崩潰。
2. **命令執行順序與原子性**：確認在佇列未滿的情況下，Read10 (LBA 0, 1, 3) 與 Unmap (LBA 0, Length 1) 的提交順序嚴格遵循腳本邏輯，且 Unmap 操作不會因為並行讀取而導致資料一致性錯誤（Data Corruption）或狀態不一致。
3. **資源回收與重復執行穩定性**：確認 `ExecuteCMD.clear()` 能正確重置命令佇列狀態，使得在 1000 次循環中，每次循環都能成功提交並執行完整的命令序列，無記憶體洩漏或佇列狀態殘留。

## Test Case (TC) Checkpoints
1. [Case01_Queue_Full_Exception_Handling]：
   - 動作：在 `while True` 迴圈中連續呼叫 `ExecuteCMD.Read10()` 並分配三個 LBA (0, 1, 3) 的讀取請求，隨後呼叫 `ExecuteCMD.Unmap()` 分配 LBA 0 的解除映射請求。當內部命令佇列達到硬體或驅動定義的最大容量時，觀察是否觸發 `api.PATTERN_ASSERT_EXECUTOR_CMD_LIST_IS_FULL` 異常。
   - 預期結果：系統不應崩潰或進入死鎖；異常被 `try...except` 區塊正確捕獲，並記錄警告資訊 `cmd seq is full: size = {len}`。這證明驅動層具備佇列滿載時的保護機制，允許測試繼續執行後續的 `send` 或進入下一次迴圈。

2. [Case02_Normal_Execution_Sequence_Check]：
   - 動作：在佇列未滿的正常情況下，執行一次完整的命令序列提交：
     1. 提交 Read10 至 LUN 0, LBA 0, Length 1, FUA=1。
     2. 提交 Read10 至 LUN 0, LBA 1, Length 1, FUA=1。
     3. 提交 Read10 至 LUN 0, LBA 3, Length 1, FUA=1。
     4. 提交 Unmap 至 LUN 0, LBA 0, Length 1。
     接著呼叫 `ExecuteCMD.send(clear_on_success=False)` 發送命令，並透過 `ExecuteCMD.read_response(idx)` 讀取所有已提交命令的回應狀態。
   - 預期結果：所有四個命令（3個 Read, 1個 Unmap）均應成功發送並返回有效的回應狀態碼（Status Code 0x00 或符合 UFS 規範的成功狀態）。特別注意 Unmap 操作針對 LBA 0，而 Read10 也針對 LBA 0，需確認硬體層面能正確處理這種「讀取與解除映射重疊」的並行請求，且 Unmap 的生效不影響已提交但未完成的 Read10 資料完整性（取決於硬體實現的原子性保證）。

3. [Case03_Loop_Stability_1000_Cycles]：
   - 動作：重複執行上述命令序列總共 1000 次。每次循環結束時呼叫 `ExecuteCMD.clear()` 清空命令佇列緩衝區。
   - 預期結果：1000 次循環全部成功完成，無任何未捕獲的異常、記憶體錯誤或佇列狀態不一致。`ExecuteCMD.clear()` 必須確保每次循環開始時，命令佇列處於空閒狀態，避免舊命令殘留導致新的命令提交失敗或行為異常。