# Test Spec: VC-34 (13.f) Program Fail Replacement & BBT Update Verification

## Verification Criterion (VC)
驗證韌體在正常區域（Normal Area）發生 Program Fail 且觸發早期替換池（Early Replacement Pool）機制時的硬體行為與韌體狀態一致性：
1. **替換邏輯驗證**：確認當 L2 VB（邏輯區塊）寫入失敗時，韌體能正確識別並標記其預測的下一個替換區塊（Next Replacement Block）為失效，並將其納入 Bad Block Table (BBT)。
2. **BBT 完整性驗證**：確認執行 `VU 405E` 讀取的 BBT 數據中，原始 L2 VB 與被選中的替換區塊均被正確標記為 Bad Block，且總 Bad Block 計數器（BB Count）精確增加 2。
3. **韌體穩定性驗證**：確認在此異常寫入情境下，韌體能正確更新內部 BB Table 且未觸發 Assert 或系統崩潰，證明韌體對 Program Fail 的錯誤處理路徑（Error Handling Path）是健壯的。

## Test Case (TC) Checkpoints
1. [Case01_BBT_Update_and_Replacement_Check]：
   - 動作：
     1. 透過 `VU 40C1` 獲取當前 Open VB 資訊，提取 L2 邏輯 VB 號碼 (`L2_vb`)。
     2. 透過 `VU 405E` 記錄初始 Bad Block 計數 (`BB_count`)。
     3. 透過 `VU 40D6` (參數: `pool_type=1`, `next_n=1`) 獲取預測的下一個替換區塊號碼 (`next_replacement_block`)。
     4. 建構 `PhysicalAddressInformation`，指定 CE=0, Plane=0，並同時設定 `BlockInfoList_0` 為 `L2_vb`，`BlockInfoList_1` 為 `next_replacement_block`。
     5. 發送 `VU C012` (參數: `fail_type=0`) 強制在 L2 VB 與其替換區塊上創建 Program Fail 狀態。
     6. 對 LUN 0 的 LBA 0 執行 `Write10` 命令（長度 `WRITE_10_MAX_BLOCK_LEN`），並透過 `ExecuteCMD.send` 發送且跳過回應檢查 (`skip_response_check=True`) 以模擬真實寫入流程中的失敗觸發。
     7. 發送 `VU 4013` 獲取 BE (Backend) Fail 狀態。
     8. 再次發送 `VU 405E` 獲取新的 Bad Block 資訊，計算新的 BB 計數 (`BB_count_new`) 並解析 BBT 數據 (`BB_data_new`)。
     9. 驗證 `BB_count_new` 是否等於 `BB_count + 2`。
     10. 在 `BB_data_new` 中搜尋是否包含原始 L2 VB 資訊 (`target_data_L2`) 以及替換區塊資訊 (`target_data_replace`)。
   - 預期結果：
     1. `BB_count_new` 必須嚴格等於 `BB_count + 2`，證明兩個區塊均被識別為失效。
     2. `BB_data_new` 中必須存在包含 `target_data_L2` (CE=0, Plane=0, Block=L2_vb) 的條目。
     3. `BB_data_new` 中必須存在包含 `target_data_replace` (CE=0, Plane=0, Block=next_replacement_block) 的條目。
     4. 整個流程執行完畢後無 Assert 異常，證明韌體成功處理了 Program Fail 並正確更新了 BB Table。