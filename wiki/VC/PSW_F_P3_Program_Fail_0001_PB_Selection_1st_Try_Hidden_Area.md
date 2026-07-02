# Test Spec: VC-29 (12.e) Program Fail in Hidden Area with New PB Selection

## Verification Criterion (VC)
驗證韌體在 Hidden Area（L2 VB）發生 Program Fail 且成功選取新替換區塊（New PB, BBT）的情境下，硬體行為與韌體狀態的一致性：
1. **BBT 更新驗證**：確認在注入 L2 VB 與新替換區塊（Next Replacement Block）的 Program Fail 後，Bad Block Table (BBT) 中的壞塊計數（BB Count）必須精確增加 2，且 L2 VB 與新替換區塊的物理地址（CE/Plane/Block）必須正確標記為壞塊。
2. **韌體穩定性驗證**：確認在此異常流程中，韌體未觸發 Assert（系統崩潰或斷言失敗），代表韌體能正確處理 Hidden Area 的壞塊管理並更新內部 BB Table，無需人工干預即可恢復正常狀態。

## Test Case (TC) Checkpoints
1. [Case01_HiddenArea_PF_BBT_Update_Check]：
   - 動作：
     1. 透過 Vendor Command (VU) 0x40C1 讀取 Open VB 資訊，提取 L2 邏輯 VB 號碼 (`L2_vb`)。
     2. 透過 VU 0x405E 讀取初始 Bad Block Count (`BB_count`) 並記錄。
     3. 透過 VU 0x40D6 預測下一個可用的替換區塊（Next Replacement Block），解析出該區塊的 CE、Plane 與 Block 號碼，此區塊將作為新 PB（BBT 目標）。
     4. 透過 VU 0xC012 注入 Program Fail 錯誤，指定兩個目標區塊：
        - 目標 1 (L2 PF)：`L2_vb` (CE=0, Plane=0)。
        - 目標 2 (BBT PF)：預測出的 Next Replacement Block (CE/Plane/Block 來自 VU 0x40D6)。
        - 設定 `fail_type=0` 且 `block_info_list_count=2`。
     5. 對 LUN 0 執行 Write10 命令，寫入 `WRITE_10_MAX_BLOCK_LEN` 長度的資料至 LBA 0，觸發實際的 Program 操作以引發硬體 Fail。
     6. 透過 VU 0x4013 讀取 BE (Block Error) Fail 狀態以確認硬體層級錯誤已發生。
     7. 再次透過 VU 0x405E 讀取更新後的 Bad Block Count (`BB_count_new`) 及 BBT 詳細數據。
     8. 計算並比對 BBT 數據，檢查是否包含初始目標 L2 VB 與新替換區塊的物理地址。
   - 預期結果：
     1. **BB Count 驗證**：`BB_count_new` 必須嚴格等於 `BB_count + 2`。這代表韌體正確識別了兩個獨立的 Program Fail 事件（一個在 L2，一個在新 PB）。
     2. **BBT 內容驗證**：
        - 在解析後的 BBT 數據列表中，必須能找到一筆記錄其 `Block`、`CE`、`Plane` 與 `target_data_L2` (即初始 L2 VB) 完全匹配，確認 L2 區塊已被標記為壞塊。
        - 在解析後的 BBT 數據列表中，必須能找到一筆記錄其 `Block`、`CE`、`Plane` 與 `target_data_BBT` (即新替換區塊) 完全匹配，確認新選取的替換區塊也已被標記為壞塊（因為注入時指定了它作為 Fail 目標，模擬新 PB 也失效的情境，或驗證韌體在選取新 PB 後的狀態追蹤）。
     3. **系統穩定性**：整個流程執行完畢後，腳本未拋出 Assert 異常，代表韌體在處理 Hidden Area 壞塊及新 PB 選取失敗/標記時，BB Table 更新機制運作正常，系統保持穩定。