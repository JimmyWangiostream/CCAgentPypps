# Test Spec: UFS Refresh Booking Queue State Machine & Priority Enforcement Test

## Verification Criterion (VC)
驗證 UFS 韌體中 Refresh Booking Queue (BQ) 的狀態機轉換邏輯與優先級仲裁機制：
1. **Stop & Enqueue Mode (C088=0x00)**：確認在停止執行但允許入隊模式下，Host 發送的 C087 命令能正確將 VB 加入 BQ，且 BQ 內容符合預期的高/中/低優先級分佈；當執行 Start (C088=0x01) 後，BQ 應被清空且 VB 狀態釋放。
2. **Disable Enqueue Mode (C088=0x04)**：確認在禁止入隊模式下，即使 Host 發送 C087 命令，韌體應拒絕將 VB 加入 BQ，導致 BQ 保持為空或僅包含先前未處理項目（若存在），驗證硬體/韌體層級的入隊閘門控制。
3. **Enable Enqueue Mode (C088=0x05)**：確認恢復允許入隊後，新的 C087 命令能立即生效並正確入隊，驗證狀態機從 "Disable" 到 "Enable" 的平滑切換。
4. **Priority Consistency**：驗證 HP (High), MP (Medium), LP (Low) 優先級列表在多次循環（Start -> Idle -> Stop/Disable -> Enqueue -> Start -> Idle）中的數據一致性，確保 VB 索引映射無錯亂。

## Test Case (TC) Checkpoints

1. **[Phase1_StopRefresh_AllowEnqueue_Verify]**：
   - 動作：
     1. 執行 `issue_C088` 設定參數為 `StopRefreshRefreshCanStillBeEnqueue` (0x00)。
     2. 從 TLC LUN 的 USED_BLK_POOL 獲取 VB 列表，隨機打亂後分配為：
        - LP: `[VB0, VB1, VB2, VB3]`
        - MP: `[VB0, VB4, VB5]`
        - HP: `[VB1, VB4, VB6]`
     3. 分別透過 `issue_C087` 將上述 VB 列表以 `HostVB` 類型及對應優先級推入 Booking Queue。
     4. 透過 `issue_40C5` 讀取當前 Booking Queue 狀態。
   - 預期結果：
     - Booking Queue 必須非空。
     - Queue 內的項目必須嚴格對應上述 HP/MP/LP 的 VB 索引組合。
     - 驗證韌體在 "Stop Execution" 狀態下，仍正確處理 "Enqueue" 請求，且優先級標籤正確寫入內部結構。

2. **[Phase1_StartRefresh_ClearQueue_Verify]**：
   - 動作：
     1. 執行 `issue_C088` 設定參數為 `StartRefresh` (0x01)。
     2. 執行 `polling_bkops_idle` 等待 BKOPS 操作完成並進入 Idle 狀態。
     3. 透過 `issue_40C5` 再次讀取 Booking Queue 狀態。
     4. 執行 `check_vb_release` 驗證 VB 狀態是否已從 "Booked" 變更為 "Released/Normal"。
   - 預期結果：
     - Booking Queue 必須為空 `{}`。
     - 先前入隊的 VB (VB0-VB6) 必須已被 Refresh 機制處理並釋放。
     - 驗證 "Start Refresh" 觸發了 BQ 中所有待處理項目的執行與清理流程。

3. **[Phase2_DisableEnqueue_Reject_Verify]**：
   - 動作：
     1. 重新獲取 VB 列表並重新分配 HP/MP/LP 組合（同 Phase1 邏輯）。
     2. 執行 `issue_C088` 設定參數為 `StopRefreshRefreshCanStillBeEnqueue` (0x00) 確保基礎狀態。
     3. 執行 `issue_C087` 將新的 VB 列表推入 Queue。
     4. 執行 `issue_40C5` 確認 Queue 已正確填入（作為基準）。
     5. 執行 `issue_C088` 設定參數為 `DisableEnqueueInRefreshBQ` (0x04)。
     6. 再次執行 `issue_C087` 嘗試將另一組 VB 列表推入 Queue。
     7. 執行 `issue_40C5` 讀取最終 Queue 狀態。
   - 預期結果：
     - 在步驟 5 執行後，Queue 應保持步驟 4 的狀態（或僅包含先前已入隊項目）。
     - 步驟 6 發送的 C087 命令**不應**導致新的 VB 進入 Queue。
     - 最終 Queue 內容必須與步驟 4 完全一致，證明 `DisableEnqueue` 位元成功阻斷了後續的入隊請求。

4. **[Phase3_EnableEnqueue_Resume_Verify]**：
   - 動作：
     1. 執行 `issue_C088` 設定參數為 `StartRefresh` (0x01) 並等待 `polling_bkops_idle`，確保 Queue 清空。
     2. 執行 `issue_C088` 設定參數為 `EnableEnqueueInRefreshBQ` (0x05)。
     3. 執行 `issue_C087` 將一組新的 HP/MP/LP VB 列表推入 Queue。
     4. 執行 `polling_bkops_idle` 等待處理完成。
     5. 執行 `issue_40C5` 確認 Queue 已清空。
   - 預期結果：
     - 在步驟 2 執行後，新的 C087 命令必須成功將 VB 加入 Queue。
     - 最終 Queue 必須為空 `{}`，且 VB 狀態已正確釋放。
     - 驗證韌體從 "Disable Enqueue" 狀態恢復到 "Enable Enqueue" 後，入隊功能完全恢復正常，無殘留狀態錯誤。