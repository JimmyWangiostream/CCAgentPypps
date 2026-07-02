# Test Spec: VC-32 (12.h) Program Fail on PTE with FW Assert 0x203 Verification

## Verification Criterion (VC)
驗證當 PTE (Program Target Entry) 區塊發生 Program Fail 且韌體觸發 Assert 0x203 時的硬體行為與狀態機邏輯：
1.  **前置條件確認**：確認系統處於正常運作狀態，並精確識別出即將被注入故障的 PTE 目標區塊（PTE_vb_next）。
2.  **故障注入與狀態鎖定**：透過 Vendor Command (VU C012) 在 PTE 區塊強制注入 Program Fail，隨後執行連續隨機寫入操作。
3.  **核心行為驗證**：
    *   確認裝置在遭遇 PTE 故障後進入非回應狀態（Unresponsive），並觸發特定的韌體 Assert 編號 **0x203**。
    *   確認在 Assert 0x203 觸發後，韌體**未**進入 Read-Only Mode（只讀模式），而是保持掛起或特定錯誤狀態。
    *   確認 PTE 的邏輯 VB 號碼（PTE VB Number）在故障發生前後**保持不變**，代表韌體未嘗試自動遷移 PTE 或修復該區塊，而是選擇記錄錯誤並停止服務。
    *   此測試旨在驗證韌體在 PTE 層級發生不可恢復錯誤時，能正確觸發 Assert 機制並維持 PTE 標記的穩定性，而非錯誤地執行區塊替換或進入保護模式。

## Test Case (TC) Checkpoints
1.  [Pre_Process_L2_EF_Cycle_Check]：
    -   動作：初始化測試環境並關閉 FW_DEBUG_MODE。透過 VU 40C1 與 40DC 獲取當前 L2 Open VB 與下一個 L2 VB。透過 VU 405E 記錄初始 Bad Block (BB) 計數。透過 VU 40D6 預測替換區塊，若剩餘替換區塊不足（next_replacement_block_2 == 0xFFFF）則跳出循環。否則，透過 VU C012 在 L2 區塊注入 Erase Fail，並執行順序寫入直到 L2 VB 切換，最後透過 VU 4013 與 405E 驗證 BB 計數增加且 BBT 正確更新。重複此循環直至替換區塊耗盡。
    -   預期結果：L2 區塊的 Erase Fail 能正確觸發韌體的替換機制，BB 計數精確增加 1，且 BBT 數據與預期目標區塊資訊完全匹配，確保測試環境中的替換池狀態符合預期，為後續 PTE 測試鋪路。

2.  [Step1_PTE_PF_Assert_0x203_Check]：
    -   動作：
        1.  透過 VU 40C1 獲取當前 PTE 邏輯 VB 號碼 (`PTE_vb`)。
        2.  透過 VU 40DC 獲取下一個 PTE 邏輯 VB 號碼 (`PTE_vb_next`)。
        3.  透過 VU C012 在 CE=0, Plane=0, Block=`PTE_vb_next` 處注入 Program Fail (`fail_type=0`)。
        4.  進入無限循環，每次生成隨機 LBA 並執行 Write10 命令（長度為 WRITE_10_MAX_BLOCK_LEN）。
        5.  捕獲 `G_TIMEOUT_ALL` 異常，檢查韌體 Assert 編號是否為 **0x203**。
        6.  若 Assert 為 0x203，記錄日誌並返回（測試通過）。
        7.  若未捕獲異常或 Assert 非 0x203，則透過 VU 40C1 讀取當前 PTE VB 號碼 (`PTE_vb_new`)。
        8.  若 `PTE_vb_new` 不等於初始 `PTE_vb`，拋出 `SIGHTING_RESPONSE_UNEXPECTED` 錯誤。
    -   預期結果：
        1.  裝置必須在寫入過程中因 PTE 故障而進入非回應狀態，並觸發韌體 Assert **0x203**。
        2.  韌體**不得**進入 Read-Only Mode（因為 Assert 0x203 的定義通常為 Device remains unresponsive after initialization, Confirmed not in read-only mode）。
        3.  在故障發生期間，PTE 的邏輯 VB 號碼必須**嚴格保持不變**（`PTE_vb_new == PTE_vb`），證明韌體未執行 PTE 重建或遷移，而是將該 PTE 標記為故障並掛起系統。
        4.  若未觸發 0x203 或 PTE VB 發生改變，則視為測試失敗。