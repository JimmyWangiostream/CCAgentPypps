# Test Spec: VC-34 (13.f) Program Fail with Early Replacement Pool Recovery

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇連續 Program Fail 情境下的錯誤處理與備用區塊管理機制：
1. **錯誤注入與狀態確認**：透過 Vendor Command (VU C012) 強制在 L2 VB (Logical 2 Virtual Block) 及其預測的下一個備用區塊 (Next Replacement Block) 製造 Program Fail，確認韌體能正確識別並記錄這兩個區塊為 Bad Block。
2. **BBT 更新驗證**：在執行實際寫入觸發 Fail 後，透過 VU 405E 讀取 Bad Block Table (BBT)，驗證 Bad Block 計數器 (BB Count) 是否精確增加 2，且 L2 VB 與 Next Replacement Block 的物理地址 (CE/Plane/Block) 均正確登錄於 BBT 中。
3. **韌體穩定性**：確認在上述複雜的 Fail 注入與 BBT 更新流程中，韌體未發生 Assert 或崩潰，系統保持正常運作。

## Test Case (TC) Checkpoints
1. [Case01_BBTable_Update_and_Replacement_Check]：
   - 動作：
     1. 配置 LUN 1 為 EM1 LUN，並預先寫入 4KB 資料以初始化該 LUN。
     2. 透過 VU 40C1 取得 EM1 LUN 的 L2 VB 號碼 (`L2_vb`)。
     3. 透過 VU 405E 讀取初始 Bad Block 計數 (`BB_count`)。
     4. 透過 VU 40D6 查詢 CE=0, Plane=0 下，Pool Type=1 (Early Replacement Pool) 的下一個預測備用區塊號碼 (`next_replacement_block`)。
     5. 透過 VU C012 發送 `PhysicalAddressInformation`，針對 `L2_vb` (Block 0) 與 `next_replacement_block` (Block 0) 同時注入 `fail_type=0` (Program Fail)。
     6. 對 LUN 1 執行 Write10 (LBA 0, Length 4KB)，並設定 `skip_response_check=True` 以允許寫入失敗。
     7. 透過 VU 4013 讀取 BE (Block Error) Fail 狀態。
     8. 再次透過 VU 405E 讀取新的 Bad Block 資訊，解析出新的 BB 計數 (`BB_count_new`) 與 BBT 數據 (`BB_data_new`)。
     9. 驗證 `BB_count_new` 是否等於 `BB_count + 2`。
     10. 在 `BB_data_new` 中搜尋是否存在包含 `target_data_L2` (CE=0, Plane=0, Block=`L2_vb`) 的條目。
     11. 在 `BB_data_new` 中搜尋是否存在包含 `target_data_replace` (CE=0, Plane=0, Block=`next_replacement_block`) 的條目。
   - 預期結果：
     1. `BB_count_new` 必須精確等於 `BB_count + 2`，代表韌體成功將兩個被注入 Fail 的區塊標記為 Bad Block。
     2. `BB_data_new` 中必須能找到對應 `L2_vb` 的條目，確認 L2 區塊已被正確標記。
     3. `BB_data_new` 中必須能找到對應 `next_replacement_block` 的條目，確認預測的備用區塊也被正確標記。
     4. 整個流程中未觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，代表韌體 BBT 更新邏輯正確且無 Assert。