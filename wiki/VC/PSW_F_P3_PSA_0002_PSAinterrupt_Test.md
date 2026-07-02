# Test Spec: UFS PSA (0007) Pre-Soldering & Loading Complete State Machine Validation

## Verification Criterion (VC)
驗證 UFS 裝置在 PSA (Pre-Soldering Area) 流程中的狀態機轉換邏輯與硬體保護機制：
1. **Pre-Soldering 保護**：確認在 `bPSAState` 為 `PRE_SOLDERING` 時，強制刷新 (HIR) 與 HID 操作被拒絕 (返回 `GENERAL_FAILURE`)，且韌體內部狀態未改變；執行 HW_RESET (無 SSU) 後，狀態仍維持 `PRE_SOLDERING`。
2. **Loading Complete 保護與中斷恢復**：確認在 `bPSAState` 為 `LOADING_COMPLETE` 時，寫入敏感 LUN 被拒絕 (`TARGET_FAILURE`)；執行 HW_RESET 後狀態強制重置為 `PRE_SOLDERING`，此時嘗試設定為 `LOADING_COMPLETE` 失敗；透過寫入 `OFF` 中斷流程，確認韌體內部 Debug Payload `0x469` 欄位變更為 `0x01` (Interrupt)；再次嘗試寫入敏感資料仍被拒絕。
3. **Soldering 完成與 Post-Reflow 驗證**：確認在 `LOADING_COMPLETE` 狀態下執行 Power Cycle (含 SSU)，重啟後狀態維持 `LOADING_COMPLETE`；執行首次寫入後，狀態自動轉換為 `SOLDERED`；透過 Vendor Command `0x405C` 確認 SLC PSA 區塊重流進度為 `0xFFFFFFFF` (100%)，且透過 `0x404F` 確認 PSA 遷移狀態為 `IsPsaOngoing=1` (表示遷移已完成/鎖定)。

## Test Case (TC) Checkpoints

1. [Case01_PreSoldering_HIR_HID_Rejection_Check]：
   - 動作：配置 4 個 LUNs (LU0-1 為 Normal/Sensitive, LU2-3 為 Enhanced1/Non-Sensitive)，設定 Write Booster Buffer 為 4GB。將 `bPSAState` 設為 `PRE_SOLDERING`。若支援 Refresh，呼叫 `HIR_when_PSA_flow_error_test` 發送 `SetFlag(REFRESH_EN)`、`WriteAttribute(REFRESH_METHOD)`、`WriteAttribute(REFRESH_UNIT)`。若支援 HID，呼叫 `HID_when_PSA_flow_error_test` 發送 `WriteAttribute(DEFAG_OPERATION=0x02)`。
   - 預期結果：所有 HIR 相關命令 (`SetFlag`, `WriteAttribute`) 的回應碼 `b6_query_response` 必須等於 `0xFF` (`GENERAL_FAILURE`)；HID 命令回應成功但 `bHIDState` 在 1 分鐘內必須維持 `0x03` (In Progress) 且不執行實際整理，代表 PSA 保護機制生效，拒絕任何可能影響 PSA 區塊的操作。

2. [Case02_HWReset_NoSSU_StatePreservation_Check]：
   - 動作：在 `PRE_SOLDERING` 狀態下，執行 `api.init_tester_to_unit_ready` 設定 `resetmode=HW_RESET` 且 `powerdown=False` (無 SSU 硬體重啟)。重啟後，嘗試將 `bPSAState` 寫入 `LOADING_COMPLETE`。
   - 預期結果：寫入 `LOADING_COMPLETE` 的回應碼 `b6_query_response` 必須等於 `0xFF` (`GENERAL_FAILURE`)。這證明在無 SSU 的硬體重啟後，韌體未能恢復 PSA 進度，狀態機回退或鎖定，無法直接進入 Loading 階段。

3. [Case03_Interrupt_FwInternalState_Check]：
   - 動作：在 `PRE_SOLDERING` 狀態下，寫入敏感 LUN (LU0/1) 資料量為 `dPSADataSize / 2`。接著將 `bPSAState` 設為 `OFF` 以中斷流程。讀取 Debug Info，檢查 `debug_info.payload[469]` 欄位。隨後嘗試寫入敏感 LUN (LU0) 16MB 資料。
   - 預期結果：`debug_info.payload[469]` 數值必須等於 `0x01` (代表 FW Internal State 為 Interrupt)；寫入敏感 LUN 的回應碼 `b6_response` 必須等於 `0x01` (`TARGET_FAILURE`)，證明在中斷狀態下，PSA 區塊仍受保護，禁止主機寫入。

4. [Case04_PowerCycle_PreservesLoadingState_Check]：
   - 動作：重新配置 LUN，寫入敏感 LUN 資料，並將 `bPSAState` 設為 `LOADING_COMPLETE`。執行 `api.init_tester_to_unit_ready` 設定 `resetmode=HW_RESET` 且 `powerdown=True` (含 SSU 電源循環)。重啟後讀取 `bPSAState`。
   - 預期結果：讀回的 `bPSAState` 數值必須等於 `api.PSAState.LOADING_COMPLETE`。這驗證了韌體在 SSU 電源循環後，能夠從非揮發性儲存中恢復 PSA 進度，正確維持在 `LOADING_COMPLETE` 狀態而非重置。

5. [Case05_SolderingTransition_Verification]：
   - 動作：在 `LOADING_COMPLETE` 狀態下，對敏感 LUN (LU0) 執行首次 16MB 寫入。寫入完成後，讀取 `bPSAState`。
   - 預期結果：`bPSAState` 數值必須自動轉換為 `api.PSAState.SOLDERED`。這代表韌體偵測到 PSA 區塊資料寫入完成，並觸發狀態機從 Loading 轉為 Soldered (鎖定)。

6. [Case06_PostReflow_MigrationState_Check]：
   - 動作：在 `SOLDERED` 狀態下，發送 Vendor Command `0x405C` (PSA Post Reflow Progress) 與 `0x404F` (PSA Migration State)。解析回應資料。
   - 預期結果：`0x405C` 回應中的 `PercentageForSLCPSAblocks` 欄位數值必須等於 `0xFFFFFFFF` (代表 100% 完成)；`0x404F` 回應中的 `IsPsaOngoing` 欄位數值必須等於 `0x01` (代表 PSA 遷移/鎖定流程已確認完成)。這驗證了硬體後處理流程 (Post-Reflow) 已正確標記 PSA 區塊為最終鎖定狀態。