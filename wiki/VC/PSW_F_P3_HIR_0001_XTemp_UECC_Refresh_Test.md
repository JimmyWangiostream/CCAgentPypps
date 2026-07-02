# Test Spec: UFS XTEMP Cross-Temperature Refresh & Booking Queue Validation

## Verification Criterion (VC)
驗證 UFS 韌體在 XTEMP（跨溫度）機制下的錯誤處理與恢復流程：
1. **Booking Queue 正確性**：當 NAND 溫度超出 T1-T2 安全範圍（Tnand > T2）並觸發 UECC 注入後，韌體應將受影響的 Logical VB 加入 Booking Queue，且 `TheBookingUser` 欄位必須精確為 `XTEMP_BOOKING (0x20)` 與 `BOOKING_IN_MP (0x02)` 的組合（即 0x22），確認錯誤被正確歸類為 XTEMP 相關。
2. **Refresh 狀態機轉換**：確認 `bRefreshStatus` 屬性在執行 `C088` 指令後，嚴格遵循 `01h` (Idle/Enqueued) -> `05h` (Executing) -> `00h` (Completed) 的狀態轉換邏輯，且中間狀態不得跳躍。
3. **異常事件標記與清除**：驗證 `wExceptionEventStatus` 的 BIT11 在 Refresh 完成後被置位（Raise），並在第二次讀取該屬性時自動清除（Reset），確認硬體異常旗標的讀寫行為符合規範。

## Test Case (TC) Checkpoints

1. [XTEMP_Booking_User_Validation]：
   - 動作：
     1. 設定 `REFRESH_UNIT=1`, `REFRESH_METHOD=1`，並寫入資料至 LUN0。
     2. 透過 `set_ec` 設定 EC 參數，執行 HW_RESET 以啟用 XTEMP 演算法。
     3. 將 NAND 溫度設定為 `XTEMP_REFRESH_T2 + 1`（超出 T2 上限），隨後在 LUN0 寫入 `TLC_VB_4K_SIZE` 大小的資料。
     4. 透過 `get_PCA_and_print` 取得該 LBA 對應的 VB 號碼 (`self.vb_number`)，並使用 `inject_UECC` 在該 VB 的 LWP 中注入 UECC 錯誤。
     5. 發送 `40C5` 指令獲取 Booking Queue，遍歷 `BookingQueueVB` 陣列，尋找 `LogicalVBNumber` 等於 `self.vb_number` 的項目。
     6. 檢查該項目的 `TheBookingUser` 欄位數值。
   - 預期結果：
     - 必須在 Booking Queue 中找到該 VB 號碼。
     - `TheBookingUser` 欄位的數值必須嚴格等於 `0x22` (即 `XTEMP_BOOKING (0x20)` | `BOOKING_IN_MP (0x02)`)。若不等於此值，測試失敗，代表韌體未正確識別 XTEMP 觸發的 Booking 來源。

2. [Refresh_Status_Machine_Transition]：
   - 動作：
     1. 發送 `C088` 指令，參數設為 `StopRefreshRefreshCanStillBeEnqueue`，確保當前 Refresh 停止但可排隊。
     2. 發送 `C088` 指令，參數設為 `StartRefresh`，啟動 Refresh 執行。
     3. 輪詢讀取 `api.AttributeIDN.REFRESH_STATUS` 屬性，直到狀態值等於 `05h` (Executing) 為止。在此過程中，若讀取到 `01h`，需清除 `REFRESH_EN` Flag 並繼續輪詢，不得視為錯誤。
     4. 當狀態為 `05h` 後，繼續輪詢直到狀態值等於 `00h` (Completed)。
     5. 再次讀取 `REFRESH_STATUS`，確認其值仍為 `00h`。
   - 預期結果：
     - 狀態轉換路徑必須為：初始 -> `01h` (可選) -> `05h` -> `00h`。
     - 最終狀態必須穩定在 `00h`。若出現其他數值（如 `02h`, `03h` 等）或在 `05h` 後未轉為 `00h`，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

3. [Exception_Event_Status_Bit11_Toggle]：
   - 動作：
     1. 在 Refresh 完成（狀態為 `00h`）後，讀取 `api.AttributeIDN.EXC_EVENT_STATUS` 屬性。
     2. 檢查返回值與 `BIT11` 進行 AND 運算，確認結果等於 `BIT11`。
     3. 再次讀取 `api.AttributeIDN.EXC_EVENT_STATUS` 屬性。
     4. 檢查返回值與 `BIT11` 進行 AND 運算，確認結果等於 `0`。
   - 預期結果：
     - 第一次讀取：`wExceptionEventStatus` 的 BIT11 必須為 `1`，代表 XTEMP 相關的異常事件已被記錄並標記。
     - 第二次讀取：BIT11 必須為 `0`，代表該異常旗標具有「讀取清除」(Read-to-Clear) 的特性，確認韌體/硬體邏輯正確處理了異常狀態的確認機制。