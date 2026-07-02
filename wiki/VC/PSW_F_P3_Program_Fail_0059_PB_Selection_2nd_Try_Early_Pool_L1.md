# Test Spec: VC-34 (13.f) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在正常區域（Normal Area）發生 Program Fail 且初始替換區塊（PB）失效時，硬體與韌體的錯誤處理機制：
1. **替換邏輯驗證**：確認當 L1 當前 VB 區塊（L1 VB）與預選的下一個替換區塊（Next Replacement Block）同時被注入 Program Fail 時，韌體能正確識別 L1 VB 失效，並成功將 L1 切換至下一個可用的 VB（L1 VB 號碼改變）。
2. **BB Table 更新驗證**：確認韌體在處理上述雙重 Program Fail 情境後，Bad Block Table (BBT) 已正確更新。具體表現為：Bad Block Count (BB Count) 必須精確增加 2（分別對應 L1 VB 與 Next Replacement Block 兩個失效區塊），且透過 Vendor Command 405E 讀取的 BBT 數據中，必須包含這兩個特定 CE/Plane/Block 地址的失效標記。
3. **系統穩定性驗證**：確認在此複雜錯誤注入流程中，韌體未觸發 Assert 或崩潰，能夠正常完成 VB 切換與 BBT 維護。

## Test Case (TC) Checkpoints
1. [Case01_Double_PF_BBT_Update_Check]：
   - 動作：
     1. 透過 Vendor Command 40C1 讀取當前 L1 開啟的 VB 號碼（L1_vb），並透過 40DC 讀取下一個預設的 L1 VB 號碼（L1_vb_next）。
     2. 透過 Vendor Command 405E 記錄初始 Bad Block Count (BB_count)。
     3. 透過 Vendor Command 40D6 查詢 CE=0, Plane=0 下，Early Replacement Pool 中的下一個預測替換區塊號碼（next_replacement_block）。
     4. 使用 Vendor Command C012 建立 Program Fail 情境：同時針對 L1_vb_next（作為目標 L1 區塊）與 next_replacement_block（作為預設替換區塊）注入 fail_type=0 的 Program Fail。
     5. 執行連續的 Write10 操作（長度為 WRITE_10_MAX_BLOCK_LEN），直到透過 40C1 讀取的 L1_vb 發生改變（代表韌體成功切換 VB）。
     6. 透過 Vendor Command 4013 獲取 BE (Bad Endurance) Fail Status。
     7. 再次透過 Vendor Command 405E 讀取更新後的 Bad Block Information，計算新的 BB_count_new 與 BBT 數據。
     8. 驗證 BB_count_new 是否等於 BB_count + 2，並檢查 BBT 數據中是否包含原 L1_vb_next 與 next_replacement_block 的地址資訊。
   - 預期結果：
     1. L1_vb 號碼必須發生改變，代表韌體成功處理了 Program Fail 並切換至新的 VB。
     2. BB_count_new 必須精確等於 BB_count + 2，證明兩個被注入 Program Fail 的區塊已被正確標記為 Bad Block。
     3. BBT 數據中必須能找到包含 `Block=L1_vb_next` 與 `Block=next_replacement_block` 的條目，證明 Bad Block Table 已正確更新這兩個特定物理地址的失效狀態。
     4. 整個流程中未拋出 Assert 異常，系統保持穩定。