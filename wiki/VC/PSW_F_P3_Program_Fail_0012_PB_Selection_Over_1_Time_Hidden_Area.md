# Test Spec: UFS FW Stuck Verification (VC-25) - Program Fail in Hidden Area with Failed PB Selection

## Verification Criterion (VC)
驗證韌體在「隱藏區 (Hidden Area)」發生連續寫入失敗，且「選擇新替換區塊 (PB Selection)」機制連續失敗超過 1 次時，系統是否會進入死鎖 (Stuck) 狀態並觸發特定的韌體斷言 (FW Assert)：
1.  **前置條件驗證**：確認透過 Vendor Command (VC) 40C1 取得的 L2 VB 號碼正確，並透過 VC 40D6 預測出兩個可用的替換區塊 (PB1, PB2)。
2.  **故障注入驗證**：透過 Vendor Command C012 強制在 L2 VB (隱藏區)、PB1 及 PB2 上注入 Program Fail，模擬替換區塊亦不可用的極端情境。
3.  **行為驗證**：執行 Write10 命令觸發寫入流程，預期韌體因無法找到有效替換區塊而卡死，最終觸發 FW Assert 0x511。若未觸發該特定 Assert 或逾時後無反應，則視為測試失敗。

## Test Case (TC) Checkpoints
1.  [VC-25_FW_Stuck_Assert_0x511_Check]：
    -   **動作**：
        1.  發送 Vendor Command **40C1** 獲取 Open VB 資訊，解析回傳值中的 `L2_Open_logical_VB_Host_TLC_number` 欄位，記為 `L2_vb`。
        2.  發送 Vendor Command **40D6** (`ce=0, plane=0, next_n=2, pool_type=2, is_CIS=0, pf_on_open_data=0`) 預測隱藏區的前兩個替換區塊。解析回傳的 8 位元組資料：
            -   從前 4 位元組提取 PB1 資訊：Block (`>>5 & 0x1FFFFFF`)、Plane (`>>2 & 0x7`)、CE (`& 0x3`)。
            -   從後 4 位元組提取 PB2 資訊：Block (`>>5 & 0x1FFFFFF`)、Plane (`>>2 & 0x7`)、CE (`& 0x3`)。
        3.  構建 `PhysicalAddressInformation` 結構體，設定三個失敗目標：
            -   Target 0: `L2_vb` (隱藏區主區塊)。
            -   Target 1: PB1 (預測的第一個替換區塊)。
            -   Target 2: PB2 (預測的第二個替換區塊)。
        4.  發送 Vendor Command **C012** (`fail_type=0, block_info_list_count=3`)，強制在上述三個區塊注入 Program Fail。
        5.  發送標準 **Write10** 命令 (`lun=0`, `lba=0`, `length=WRITE_10_MAX_BLOCK_LEN`, `fua=1`) 觸發寫入操作。
        6.  設定 `skip_response_check=True` 並捕獲 `G_TIMEOUT_ALL` 異常。
        7.  在捕獲異常後，呼叫 `api.get_fw_assert_number()` 讀取韌體斷言編號。
    -   **預期結果**：
        -   寫入命令必須觸發 `G_TIMEOUT_ALL` 異常（代表主機端等待回應逾時，韌體無回應）。
        -   `api.get_fw_assert_number()` 回傳的值必須精確等於 **0x511**。
        -   此結果確認韌體在隱藏區寫入失敗且連續兩次替換區塊選擇 (PB Selection) 均失敗後，確實進入死鎖狀態並觸發了預期的 FW Assert 0x511，符合 VC-25 規範。