# Test Spec: UFS VTH Sweep & Event Log VT Diff Verification

## Verification Criterion (VC)
驗證韌體在發生單點 UECC (Unrecoverable ECC) 錯誤時，VTH (Voltage Threshold) 掃描機制與 Event Log 記錄的一致性：
1.  **硬體行為觸發**：透過 Vendor Command (C060) 直接寫入特定 PBA (Die/Plane/Block/Page) 的 Raw Data 並注入 0xAA 模式以觸發硬體 UECC，確認 Host Read (Read10) 正確返回 UECC 狀態碼。
2.  **VTH 數據採集**：針對失敗的 WL (Word Line) 及其相鄰 WL (WL-1, WL+1) 和同 Block 的其他 Plane，透過 Vendor Command (401D) 讀取 VT Distribution，並計算相鄰 VT 階梯的差值 (VT Diff)。
3.  **Event Log 驗證**：確認韌體在檢測到 UECC 後，透過 Vendor Command (40B0/4080) 產生的 Event Log (ID 0x6004) 中記錄的 VT Diff 數據，與步驟 2 中透過 401D 直接讀取並計算出的 VT Diff 數據完全一致。

## Test Case (TC) Checkpoints
1.  [UECC_Injection_and_Read_Status_Check]：
    -   動作：配置 LUN 0 (Normal) 與 LUN 1 (Enhanced 1)。針對 LUN 0 寫入 3 * TLC_VB_Size 的資料。隨機選取一個 LBA，透過 VU 4051 取得其對應的 PBA (Die, Plane, Block, Page)。使用 Vendor Command C060 向該 PBA 寫入 16KB * 3 的 0xAA 資料（觸發 TLC 模式下的 UECC）。接著發送 Host Read10 命令讀取該 LBA。最後使用 Vendor Command C060 讀取狀態，預期返回 `ReadStatus.UECC`。
    -   預期結果：Host Read10 應成功完成但標記為錯誤；C060 狀態檢查必須返回 `UECC`，確認硬體層面已正確識別出該 Page 的資料損毀且無法透過 ECC 修復。

2.  [VT_Diff_Collection_Scope_Check]：
    -   動作：根據失敗 Page 的 WL 編號，透過 `get_wl_sb_number_by_page_on_TLC` 計算出失敗的 WL 和 SB (Sub-Block)。執行以下 VU 401D 呼叫以收集 VT Distribution：
        1.  失敗 WL 的失敗 SB。
        2.  失敗 WL 的其他 3 個 SB。
        3.  失敗 WL - 1 的剩餘 SB (從失敗 SB 開始到結尾)。
        4.  失敗 WL + 1 的剩餘 SB (從開頭到失敗 SB)。
        5.  失敗 WL 和 SB 的其他 Plane。
        將所有讀取的 VT 數據轉換為 VT Diff List (相鄰 VT 值的差值)。
    -   預期結果：成功獲取所有指定區域的 VT Distribution 數據，並能正確計算出 VT Diff List，作為後續與 Event Log 比對的基準數據 (Baseline)。

3.  [Event_Log_VT_Data_Consistency_Check]：
    -   動作：等待 Event Log 計數增加（確認韌體已記錄 UECC 事件）。使用 Vendor Command 4080/40B0 讀取 Event Log，篩選出 Log ID 為 `0x6004` (EVENT_BE_VT_LOG_ID) 的記錄。從 Event Log 的 `SPECIFIC_LOG_INFO_OFFSET` 開始提取 VT Diff 數據。將 Event Log 中的 VT Diff 數據與步驟 2 中計算出的 VT Diff List 進行逐項比對。
    -   預期結果：Event Log 中記錄的 VT Diff 數據必須與透過 VU 401D 直接讀取並計算出的 VT Diff List **完全相等**。這驗證了韌體在處理 UECC 事件時，正確地採用了與 VTH Sweep 相同的邏輯來記錄電壓閾值偏移量，確保韌體內部狀態與硬體實際物理特性的一致性。