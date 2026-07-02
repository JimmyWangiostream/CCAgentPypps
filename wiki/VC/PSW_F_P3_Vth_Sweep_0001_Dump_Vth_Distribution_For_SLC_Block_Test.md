# Test Spec: UFS PTE (0007) UECC Event Log VT Diff Verification Test

## Verification Criterion (VC)
驗證 UFS 韌體在發生不可修復的 UECC (Unrecoverable ECC) 錯誤時，其 Event Log 機制能否精確記錄並回報受影響 Page 的 Vth (Threshold Voltage) 分佈差異：
1.  **硬體行為觸發**：透過 Vendor Command (C060) 直接覆寫特定 SLC 模式的 Physical Page 資料為 0xAA，強制產生硬體層級的 UECC 錯誤。
2.  **狀態確認**：透過 Host Read10 指令讀取該 LBA，確認控制器回報 ReadStatus.UECC，證明錯誤已被硬體偵測且韌體未自動修復。
3.  **VT 數據採集**：針對發生錯誤的 Page 及其相鄰的 WL (Word Line)、SB (Sub-Block)、Plane 區域，透過 Vendor Command (401D) 讀取原始的 Vth 分佈數據。
4.  **Log 比對驗證**：透過 Vendor Command (40B0/4080) 讀取 Event Log 中 ID 為 0x6004 的 VT Diff 記錄，驗證 Log 中記錄的 Vth Diff 數值與步驟 3 中直接讀取的 Vth 數據計算出的 Diff 完全一致，確保韌體記錄的錯誤特徵數據準確無誤。

## Test Case (TC) Checkpoints
1.  [Case01_LBA0_UECC_VT_Log_Check]：
    -   動作：
        1.  配置 LUN 1 (EM1) 為測試目標，寫入 `slc_vb_size` 個 4KB 區塊。
        2.  針對 LBA 0，透過 VU 4051 取得其物理地址 (PBA: Die, Plane, Block, Page)。
        3.  計算該 Page 對應的 WL 編號 (`wl = page // 4`)。
        4.  呼叫 `inject_UECC`，使用 Vendor Command C060 將該 Page 的 Payload 寫入 0xAA (16KB 長度)，強制產生 UECC。
        5.  執行 Host Read10 讀取 LBA 0，並透過 `direct_read_raw_data_and_check_status` 確認狀態為 `ReadStatus.UECC`。
        6.  透過 Vendor Command 401D 讀取以下區域的 Vth 分佈：
            -   失敗的 WL (`wl`) 與失敗的 SB (`page % 4`)。
            -   失敗 WL 上的其他 3 個 SB。
            -   失敗 WL -1 的剩餘 SB。
            -   失敗 WL +1 的前幾個 SB。
            -   失敗 WL 與 SB 的其他 Plane。
        7.  等待 Event Log 計數增加，讀取 Log ID 為 0x6004 的 VT Diff 記錄。
        8.  將直接讀取的 Vth 數據轉換為 Diff List (相鄰閾值電壓之差)，並與 Event Log 中的 Diff List 進行逐項比對。
    -   預期結果：
        -   Host Read10 必須回報 `ReadStatus.UECC`。
        -   Event Log 中必須存在 ID 為 0x6004 的記錄。
        -   直接讀取的 Vth Diff List 與 Event Log 中的 VT Diff 數據必須完全相等 (`vt == event_vt`)，證明韌體正確記錄了導致 UECC 的具體 Vth 異常特徵。

2.  [Case02_RandomLBA_UECC_VT_Log_Check]：
    -   動作：
        1.  隨機選擇一個 LBA (範圍 1 至 `length-1`)。
        2.  透過 VU 4051 取得該 LBA 的物理地址，並透過 VU 4052 反向驗證 LBA 對應關係正確。
        3.  執行與 Case01 相同的 UECC 注入 (C060 寫 0xAA)、狀態檢查 (ReadStatus.UECC) 及周邊 VT 數據採集 (401D)。
        4.  讀取 Event Log ID 0x6004 並比對 VT Diff 數據。
    -   預期結果：
        -   VU 4052 反向轉換的 LBA 必須與原始輸入 LBA 一致。
        -   Host Read10 必須回報 `ReadStatus.UECC`。
        -   直接讀取的 Vth Diff List 與 Event Log 中的 VT Diff 數據必須完全相等。

3.  [Case03_LastLBA_UECC_VT_Log_Check]：
    -   動作：
        1.  選擇最後一個 LBA (`length - 1`)。
        2.  透過 VU 4051 取得物理地址，並透過 VU 4052 驗證。
        3.  執行與 Case01 相同的 UECC 注入、狀態檢查及周邊 VT 數據採集。
        4.  讀取 Event Log ID 0x6004 並比對 VT Diff 數據。
    -   預期結果：
        -   VU 4052 反向轉換的 LBA 必須與原始輸入 LBA 一致。
        -   Host Read10 必須回報 `ReadStatus.UECC`。
        -   直接讀取的 Vth Diff List 與 Event Log 中的 VT Diff 數據必須完全相等。