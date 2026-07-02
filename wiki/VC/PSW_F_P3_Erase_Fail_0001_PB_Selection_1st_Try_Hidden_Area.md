# Test Spec: UFS Program/Erase Fail Handling in Hidden Area (VC-6)

## Verification Criterion (VC)
驗證韌體在 Hidden Area 發生 Erase Fail 時的 Bad Block Table (BBT) 更新機制與系統穩定性：
1.  **錯誤注入與狀態確認**：透過 Vendor Command `0xC012` 強制在 L2 VB (Host Data Area) 及其對應的 Replacement Block (BBT Area) 注入 Erase Fail 狀態。
2.  **BBT 更新驗證**：在觸發 Erase Fail 後，透過連續 Write10 操作直到 L2 VB 切換，確認韌體已正確識別失效區塊。讀取 Vendor Command `0x405E` 回傳的 Bad Block Information，驗證 Bad Block Count 必須精確增加 2 (L2 VB 與 Replacement Block 各計為 1 個 Bad Block)。
3.  **BBT 內容完整性驗證**：解析 `0x405E` 回傳的 BBT 資料，確認 L2 VB 的物理地址 (CE/Plane/Block) 與 Replacement Block 的物理地址均已被正確標記為 Bad Block 並記錄在案。
4.  **系統穩定性驗證**：整個流程中韌體不得發生 Assert (Crash) 或 Hang，確保在隱藏區域發生硬體級錯誤時，韌體能透過軟體層級的 BBT 維護機制維持系統正常運作。

## Test Case (TC) Checkpoints
1.  [Case01_EraseFail_Injection_And_BBT_Update_Check]：
    -   動作：
        1.  透過 `issue_40C1` 取得當前 L2 VB (`L2_vb`) 號碼，並透過 `issue_40DC` 取得下一個可用的 L2 VB (`L2_vb_next`)。
        2.  透過 `issue_405E` 記錄初始 Bad Block Count (`BB_count`)。
        3.  透過 `issue_40D6` (Pool Type 2, Hidden Area) 取得預測的 Replacement Block 物理地址 (`next_replacement_ce/plane/block`)。
        4.  建構 `PhysicalAddressInformation`，指定 Die 0, Plane 0, Block `L2_vb_next` 為目標 L2 VB，並指定上述 Replacement Block 為對應的 BBT 區塊。
        5.  發送 Vendor Command `0xC012` (Fail Type 1: Erase Fail)，強制將 L2 VB 與 Replacement Block 標記為 Erase Fail。
        6.  執行連續 Write10 寫入 (LBA 0 開始，長度 `WRITE_10_MAX_BLOCK_LEN`)，直到 `issue_40C1` 回傳的 L2 VB 號碼發生改變 (`L2_vb_new != L2_vb`)，確保韌體已處理完該區塊的寫入並切換 VB。
        7.  再次發送 `issue_405E` 取得新的 Bad Block Count (`BB_count_new`) 及 BBT 詳細資料 (`BB_data_new`)。
        8.  比對 `BB_count_new` 是否等於 `BB_count + 2`。
        9.  在 `BB_data_new` 中搜尋是否包含目標 L2 VB (`target_data_L2`) 與目標 Replacement Block (`target_data_BBT`) 的物理地址資訊。
    -   預期結果：
        1.  `BB_count_new` 必須精確等於 `BB_count + 2`，代表韌體正確識別了兩個新的 Bad Block。
        2.  `BB_data_new` 中必須存在一筆資料，其 CE/Plane/Block 與 `target_data_L2` (即 `L2_vb_next`) 完全匹配。
        3.  `BB_data_new` 中必須存在一筆資料，其 CE/Plane/Block 與 `target_data_BBT` (即 Replacement Block) 完全匹配。
        4.  測試過程無 Assert 或異常中斷，代表韌體在 Hidden Area 發生 Erase Fail 時，BBT 更新邏輯運作正常且系統穩定。