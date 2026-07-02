# Test Spec: VC-30 (12.f) Program Fail Early Replacement Pool Verification

## Verification Criterion (VC)
驗證韌體在 Normal Area 發生 Program Fail 且該 L1 VB 區塊被標記為 Bad Block 後，系統能否正確執行 Bad Block Table (BBT) 更新機制：Case 01 確認透過 Vendor Command (VU C012) 強制注入 Program Fail 至 L1 VB 的下一個可用區塊 (L1_vb_next) 後，系統能識別該錯誤並將其加入 BBT；Case 02 確認在後續的 Host Write 操作觸發 L1 VB 切換至新區塊時，BBT 中的 Bad Block 計數器 (BB Count) 必須精確增加 1，且目標區塊 (CE/Plane/Block) 必須明確存在於 BBT 數據中，代表韌體無 Assert 且狀態機恢復正常。

## Test Case (TC) Checkpoints
1. [Case01_ProgramFail_Injection_and_BBT_Update_Check]：
   - 動作：
     1. 透過 VU 40C1 讀取當前 L1 Open VB 號碼 (L1_vb)，並透過 VU 40DC 讀取下一個可用的 L1 VB 號碼 (L1_vb_next)。
     2. 透過 VU 405E 讀取初始 Bad Block Count (BB_count)。
     3. 建構 PhysicalAddressInformation，指定 CE=0, Plane=0, Block=L1_vb_next, Page=0，並透過 Vendor Command VU C012 以 fail_type=0 強制在該物理位置注入 Program Fail 錯誤。
     4. 執行迴圈寫入 16 Bytes 資料至隨機 LBA，持續監控 VU 40C1 回應，直到 L1 Open VB 號碼發生改變 (L1_vb_new != L1_vb)，確保寫入操作觸發了 VB 切換邏輯。
     5. 透過 VU 4013 讀取 BE (Bad Endurance) Fail Status。
     6. 再次透過 VU 405E 讀取新的 Bad Block Count (BB_count_new) 及 BBT 詳細數據 (BB_data_new)。
     7. 驗證 BB_count_new 是否等於 BB_count + 1，並檢查 BB_data_new 中是否包含目標區塊資訊 (CE=0, Plane=0, Block=L1_vb_next)。
   - 預期結果：
     1. BB_count_new 必須嚴格等於 BB_count + 1，代表韌體成功將受影響的區塊標記為 Bad Block 並更新計數器。
     2. BB_data_new 列表中必須存在一筆記錄，其 Block 欄位等於 L1_vb_next，且 CE 為 0，Plane 為 0，代表該特定物理區塊已被正確識別並加入 BBT。
     3. 整個流程中韌體不得發生 Assert 或系統崩潰，證明 Early Replacement Pool 機制在 Normal Area 的 Program Fail 情境下運作正常。