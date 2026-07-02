# Test Spec: VC-30 (12.f) Program Fail on PTE Early Replacement Pool Verification

## Verification Criterion (VC)
驗證韌體在 PTE (Primary Target Entry) 區塊遭遇 Program Fail 且該區塊位於 Early Replacement Pool 時，系統能否正確執行 Bad Block Table (BBT) 更新機制：
1.  **狀態初始化**：確認初始 PTE VB 號碼、Next PTE VB 號碼及當前 BB Count 基線。
2.  **故障注入**：透過 Vendor Command `0xC012` 強制在 Next PTE 區塊（CE=0, Plane=0）注入 Program Fail 錯誤。
3.  **替換觸發**：透過連續寫入操作觸發 PTE 切換，確保新的 PTE 指向原 Next PTE 區塊（即故障區塊）。
4.  **恢復驗證**：確認韌體自動將故障區塊標記為 Bad Block，BB Count 嚴格增加 1，且 BBT 中正確包含該故障區塊的物理地址資訊，同時韌體無 Assert 崩潰。

## Test Case (TC) Checkpoints
1.  **[Case01_PTE_PF_Inject_and_Replace_Check]：
    - 動作：
        1.  透過 Vendor Command `0x40C1` 讀取當前開啟的 VB 資訊，提取 `PTE_Block_VB_number_logical` 作為初始 PTE VB (`PTE_vb`)。
        2.  透過 Vendor Command `0x40DC` (參數 0) 讀取下一個開啟的 VB 資訊，提取 `PTE` 欄位作為 Next PTE VB (`PTE_vb_next`)。
        3.  透過 Vendor Command `0x405E` 讀取當前 Bad Block 資訊，解析前 4 位元組小端序整數作為初始 BB Count (`BB_count`)。
        4.  建構 `PhysicalAddressInformation`，設定 CE=0, Plane=0, Block=`PTE_vb_next`, Page=0，並透過 Vendor Command `0xC012` 執行 `issue_C012_to_create_program_erase_fail` (fail_type=0) 在該 Next PTE 區塊注入 Program Fail。
        5.  記錄目標故障區塊資訊 `target_data_PTE` (Block=`PTE_vb_next`, CE=0, Plane=0)。
        6.  進入迴圈執行隨機 Write10 操作 (LUN=0, Length=Max Block Len, FUA=1)，每次寫入後透過 `0x40C1` 檢查當前 PTE VB。當讀取到的 `PTE_vb_new` 不等於初始 `PTE_vb` 時，表示 PTE 已切換，跳出迴圈。
        7.  透過 Vendor Command `0x4013` 讀取 BE (Bad Endurance) Fail 狀態。
        8.  再次透過 Vendor Command `0x405E` 讀取更新後的 Bad Block 資訊，解析新的 BB Count (`BB_count_new`) 並呼叫 `calculate_bbt` 解析 BBT 資料結構。
        9.  驗證 `BB_count_new` 是否等於 `BB_count + 1`，並檢查 BBT 中是否存在與 `target_data_PTE` 完全匹配的條目。
    - 預期結果：
        -   PTE 成功切換至原 Next PTE 區塊。
        -   `BB_count_new` 必須精確等於 `BB_count + 1`，代表韌體正確識別並標記了一個新的 Bad Block。
        -   BBT 查詢結果中必須找到包含 Block=`PTE_vb_next`, CE=0, Plane=0 的條目，代表韌體已將該 Program Fail 區塊正確加入替換池並更新 BBT，且過程中未發生韌體 Assert 或系統崩潰。