# Test Spec: UFS Firmware Event Log, MMesg & Thermal Assert Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 RAIN Recovery 觸發後，Event Log 與 MMesg 記錄的完整性與數據一致性，以及 Thermal Protection 機制觸發 Assert Dump 的硬體行為：
1. **Event Log 驗證**：確認在 SLC LUN 注入 UECC 並觸發 Refresh (RAIN Recovery) 後，韌體正確寫入 Event Log ID `0x3011` (RAIN_RECOVERY) 與 `0x6001` (UECC)。檢查 Log Header 的 Priority 為 HIGH (0)，並驗證 Common Info 區塊中的 VCC/VCCQ Drop Count、System/NAND 溫度（誤差 < 5°C）、Smart Info (Host Write/Read Cmd Count 範圍 0x00-0x08, 0x08-0x10)、System Status Info (TLC L2 VB/Page/RemapVB 範圍 0x00-0x04, 0x04-0x08, 0x10-0x14) 以及 Host SSR Info (SLC Erase Count Min/Max/Avg 範圍 0x20-0x24, 0x24-0x28, 0x28-0x2C) 與透過 VU 命令 (0x40B8, 0x40FD, 0x4021, 0x40C1, 0x40FE) 讀取的即時參考數據完全一致。
2. **MMesg Log 驗證**：確認 RAIN Recovery 觸發後，MMesg 中新增包含 Log ID `0x0027` (EVENT_SOFTBIT), `0x002B` (EVENT_READ_DISTURB_REFRESH), `0x002D` (EVENT_RAID_RECOVERY), `0x0036` (EVEN_UFS_WRITE) 的記錄。驗證 MMesg 大於 8KB 時，透過 `wPara4` 偏移量 (0 與 2) 進行的 Split Read (各 0x2000 bytes) 組合數據與單次 Full Read (0x4000 bytes) 數據完全一致。
3. **Assert Dump 驗證**：確認透過 VU 0xD0F1 將 Thermal Protection High Threshold 設為 80°C 後，執行 Write10 指令觸發韌體 Stuck。驗證 Assert Dump 中記錄的 Assert Code 為 `0x464`，且詳細資訊中 `TmprStas` 欄位為 1，且 Index 5-16 的溫度相關數值均不為 `0xFFFF` (代表有效數據)。

## Test Case (TC) Checkpoints

1. [EventLog_RAIN_Recovery_Data_Integrity_Check]：
   - 動作：
     1. 清除所有 Event Log，確認計數為 0。
     2. 呼叫 `trigger_rain_recovery_event`：停止 Refresh (`VUC088Paremeter.StopRefresh`) -> 在 SLC LUN (LUN 0) 寫入資料 -> 取得 LBA 0 的 PCA (Virtual Block, CE, Plane) -> 透過 VU 0xC060 在該物理頁注入 UECC (Payload 0xAA) -> 讀取該頁觸發 UECC -> 確認 Booking Queue 有 Entry -> 啟動 Refresh (`VUC088Paremeter.StartRefresh`) 觸發 RAIN Recovery。
     3. 等待 Event Log 計數增加，讀取新增的 Log Index。
     4. 透過 VU 0x40B8, 0x40FD, 0x4021, 0x40C1, 0x40FE 及 `get_smart_info` 收集即時參考數據 (Reference Data)。
     5. 讀取 Event Log ID `0x3011` 與 `0x6001` 的完整 Payload。
     6. 比對 Header：檢查 Index 欄位與 Priority 欄位 (預期 0x00000000)。
     7. 比對 Common Info (Offset 8-576)：檢查 Timestamp 非 0/0xFFFFFFFF；VCC Drop Count (Offset 20) 與 VCCQ Drop Count (Offset 24) 必須等於 VU 0x40B8 讀取值；System Temperature (Offset 8) 與 NAND Temperature (Offset 12) 與參考值誤差需 < 5；Smart Info (Offset 36, Length 540) 中 Range (0,8) 與 (8,16) 的 Host Write/Read Cmd Count 必須與參考數據一致。
     8. 比對 System Status Info (Offset 1032, Length 512)：檢查 Range (0,4) TLC L2 VB, (4,8) Next Program Page, (16,20) RemapVB 與 VU 0x40C1 讀取值一致。
     9. 比對 Host SSR Info (Offset 1544, Length 1024)：檢查 Range (32,36) Min, (36,40) Max, (40,44) Avg SLC Erase Count 與 VU 0x40FE 讀取值一致。
   - 預期結果：所有 Event Log ID 存在；Header Priority 為 0；Common Info 中的溫度、Drop Count、Smart Info 指定範圍數值與參考數據完全匹配；System Status Info 與 Host SSR Info 指定範圍數值與參考數據完全匹配。

2. [MMesg_RAIN_Recovery_ID_And_Split_Read_Check]：
   - 動作：
     1. 清除所有 MMesg Log，確認計數 < 2。
     2. 呼叫 `trigger_rain_recovery_event` 觸發 RAIN Recovery。
     3. 讀取所有 MMesg Log，解析出新增的 Log ID 集合。
     4. 檢查新增 Log ID 是否包含 `0x0027` (EVENT_SOFTBIT), `0x002B` (EVENT_READ_DISTURB_REFRESH), `0x002D` (EVENT_RAID_RECOVERY), `0x0036` (EVEN_UFS_WRITE)。
     5. 針對最新的 MMesg Log Index，執行 Split Read 驗證：
        - 讀取 Full Log (Transfer Length 0x4000)。
        - 讀取 Split 1 (wPara4=0, Transfer Length 0x2000)。
        - 讀取 Split 2 (wPara4=2, Transfer Length 0x2000)。
        - 將 Split 1 與 Split 2 拼接，與 Full Log 進行 Byte-for-Byte 比對。
   - 預期結果：新增 Log ID 包含所有指定的 4 個 ID；Split Read 拼接後的數據與 Full Read 數據完全一致，無任何 Byte 差異。

3. [AssertDump_Thermal_Protection_Trigger_Check]：
   - 動作：
     1. 清除 Assert Dump，確認 Total Assert Count 為 0。
     2. 透過 VU 0x40FA 讀取當前 Thermal Stuck Threshold。
     3. 透過 VU 0xD0F1 寫入新的 Threshold：Low 保持原值，High 設為 80 (代表 UFS Temp = Real + 80)。
     4. 發送 Write10 指令 (LUN 0, LBA 0, Length 4KB, FUA=1)。
     5. 預期指令超時 (Timeout)，確認韌體因 Thermal Protection 進入 Stuck 狀態。
     6. 透過 DME Get 讀取 Assert Code，確認不為 0。
     7. 執行 HW_RESET 恢復設備。
     8. 讀取 Assert Dump Summary，確認 Total Assert Count > 0 且 Assert Numbers 中包含 `0x464`。
     9. 讀取 Assert Code `0x464` 的詳細資訊 (VU 0x4080 para_0=1, para_1=2)。
     10. 檢查 Assert Number 欄位為 `0x464`；檢查 Offset 4 的 `TmprStas` 為 1；檢查 Offset 5-16 的數值均不等於 `0xFFFF`。
   - 預期結果：Assert Dump 中成功記錄 Assert Code `0x464`；詳細資訊顯示 `TmprStas=1` 且溫度相關欄位為有效數值 (非 0xFFFF)，證明 Thermal Protection 機制正確觸發並記錄了硬體狀態。