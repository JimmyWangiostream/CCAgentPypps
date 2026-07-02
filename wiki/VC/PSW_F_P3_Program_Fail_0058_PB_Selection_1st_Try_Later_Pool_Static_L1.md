# Test Spec: VC-32 (12.h) Program Fail - L2 Replacement Success & L1 Assert Handling

## Verification Criterion (VC)
驗證韌體在快閃記憶體程式/擦除失敗（Program/Erase Fail, PF）情境下的兩種關鍵硬體行為與狀態機轉換：
1.  **L2 (Host TLC) 正常替換機制**：當目標 L2 VB 區塊發生擦除失敗時，韌體應能正確識別壞塊，從替換池（Replacement Pool）選取新的 L2 VB，更新 Bad Block Table (BBT)，並強制進入 Read-Only 模式以保護數據完整性。
2.  **L1 (S-Chunk) 異常處理機制**：當目標 L1 VB 區塊發生程式失敗時，韌體不應進入 Read-Only 模式，而是觸發特定的韌體斷言（FW Assert 0x203），導致設備在初始化後無響應（Unresponsive），此為預期的異常保護行為，而非系統崩潰。

## Test Case (TC) Checkpoints

1.  **[L2_Replacement_BBTable_Update_Check]**：
    -   動作：
        1.  透過 Vendor Command (VC) `0x40C1` 讀取當前 L2 Open VB (`L2_vb`)，並透過 `0x40DC` 讀取下一個可用的 L2 VB (`L2_vb_next`)。
        2.  透過 VC `0x405E` 記錄初始壞塊計數 (`BB_count`)。
        3.  透過 VC `0x40D6` 確認替換池中有足夠的預備區塊（`next_replacement_block_2 != 0xFFFF`）。
        4.  使用 VC `0xC012` 針對 `L2_vb_next` 區塊注入擦除失敗（`fail_type=1`）。
        5.  執行連續 Write10 命令（LBA 從 0 開始，長度為 `WRITE_10_MAX_BLOCK_LEN`），直到讀取到的 L2 Open VB 發生改變（`L2_vb_new != L2_vb`）。
        6.  再次透過 VC `0x405E` 讀取新的壞塊資訊，計算 BBT 並驗證壞塊計數是否增加 1 (`BB_count_new == BB_count + 1`)。
        7.  驗證新的 BBT 中是否包含被標記為壞塊的 `target_data_L2` (CE:0, Plane:0, Block:`L2_vb_next`)。
    -   預期結果：
        -   L2 Open VB 號碼必須發生跳變，代表韌體成功從替換池選取了新的 L2 VB。
        -   壞塊計數必須精確增加 1。
        -   新的 BBT 數據中必須明確標記 `L2_vb_next` 為壞塊。
        -   此流程重複執行直到替換池預備區塊不足，驗證韌體在 L2 層級能正確處理 PF 並更新 BBT。

2.  **[L1_Assert_0x203_Unresponsive_Check]**：
    -   動作：
        1.  透過 VC `0x40C1` 讀取當前 L1 Open VB (`L1_vb`)，並透過 `0x40DC` 讀取下一個可用的 L1 VB (`L1_vb_next`)。
        2.  使用 VC `0xC012` 針對 `L1_vb_next` 區塊注入程式失敗（`fail_type=0`）。
        3.  執行隨機位置的 Write10 命令（長度 16 Bytes），並設置 `skip_response_check=True` 以捕獲底層錯誤。
        4.  監控設備響應：
            -   若設備無響應（觸發 `G_TIMEOUT_ALL`），檢查韌體斷言號碼是否為 `0x203`。
            -   若設備有響應，檢查 L1 Open VB 是否改變。
    -   預期結果：
        -   設備必須進入無響應狀態（Timeout），且韌體斷言號碼必須精確等於 `0x203`。
        -   L1 Open VB 號碼必須保持不變（`L1_vb_new == L1_vb`），證明韌體未嘗試進行替換，而是因 L1 層級 PF 觸發了保護性斷言。
        -   若未觸發 `0x203` 斷言或 L1 VB 發生改變，則視為測試失敗（`SIGHTING_RESPONSE_UNEXPECTED`）。