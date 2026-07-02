# Test Spec: VC-29 (12.e) Program Fail in Hidden Area with Write Booster

## Verification Criterion (VC)
驗證在啟用 Write Booster (WB) 且涉及 Hidden Area (L2 VB) 的情境下，當韌體透過 Vendor Command (VU C012) 強制注入 Program Fail 錯誤時，控制器的硬體行為與韌體恢復機制：
1.  **BBT 更新驗證**：確認韌體在偵測到 L2 VB (Write Booster 邏輯區塊) 與對應的 Replacement Block (BBT 管理區塊) 發生 Program Fail 後，能正確將這兩個實體區塊標記為 Bad Block，並更新 Bad Block Table (BBT)。
2.  **狀態碼驗證**：確認 Bad Block Count (透過 VU 405E 讀取) 精確增加 2 個單位，且 BBT 資料中明確包含被注入失敗的 L2 VB 與 Replacement Block 的 CE/Plane/Block 資訊。
3.  **無 Assert 驗證**：確認整個流程中韌體未觸發 Assert 異常，代表韌體具備處理 Hidden Area 與 WB 混合情境下 Program Fail 的穩健性。

## Test Case (TC) Checkpoints
1.  [Case01_WB_Hidden_Area_PF_BBT_Update_Check]：
    -   動作：
        1.  配置 LUN 0 (Normal), LUN 1 (EM1), LUN 2 (WB/Write Booster)。
        2.  透過 Vendor Command VU 40C1 讀取 Open VB 資訊，提取 `open_logical_VB_number_for_Write_Booster_WB_L2` 作為目標 L2 VB 號碼。
        3.  透過 Vendor Command VU 405E 讀取初始 Bad Block Count (`BB_count`) 並記錄。
        4.  透過 Vendor Command VU 40D6 查詢預測的下一個 Replacement Block (Pool Type 2, Hidden Area)，解析出目標 Replacement Block 的 CE, Plane, Block 號碼。
        5.  構造 `PhysicalAddressInformation`，設定兩組失敗目標：
            -   Target 1 (L2): Die=0, Plane=0, Block=`L2_vb`, Page=0。
            -   Target 2 (BBT): Die=`next_replacement_ce`, Plane=`next_replacement_plane`, Block=`next_replacement_block`, Page=0。
        6.  執行 Vendor Command VU C012，以 `fail_type=0` (Program Fail) 強制注入上述兩組實體區塊的 Program Fail 錯誤。
        7.  設定 Flag `WRITEBOOSTER_EN` 啟用 WB 功能。
        8.  對 LUN 2 (WB LUN) 的 LBA 0 執行 Write10 指令寫入 `WRITE_10_MAX_BLOCK_LEN` 長度的資料，觸發實際的 Program 操作以激活前述注入的 Fail 狀態。
        9.  執行 Vendor Command VU 4013 讀取 BE (Block Error) Fail Status。
        10. 再次執行 Vendor Command VU 405E 讀取新的 Bad Block Count (`BB_count_new`) 及 BBT 詳細資料 (`BB_data_new`)。
        11. 比對 `BB_count_new` 是否等於 `BB_count + 2`。
        12. 在 `BB_data_new` 中搜尋是否包含 Target 1 (L2) 與 Target 2 (BBT) 的完整 CE/Plane/Block 資訊。
    -   預期結果：
        1.  `BB_count_new` 必須精確等於 `BB_count + 2`，代表控制器正確識別並標記了兩個新的 Bad Block。
        2.  `BB_data_new` 中必須存在一筆資料，其 Block/CE/Plane 完全匹配 Target 1 (L2 VB)，代表 L2 區塊已被標記為 Bad。
        3.  `BB_data_new` 中必須存在另一筆資料，其 Block/CE/Plane 完全匹配 Target 2 (Replacement Block)，代表 BBT 管理區塊也已被標記為 Bad。
        4.  整個測試流程未拋出 Assert 異常，代表韌體在處理 Hidden Area 與 WB 交錯的 Program Fail 時邏輯正確且穩定。