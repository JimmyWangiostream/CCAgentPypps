# Test Spec: UFS PSA (Power State Adaptation) Lifecycle & Inhibition Mechanism Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 PSA (Power State Adaptation) 流程中的狀態機轉換、緩衝區管理、以及硬體抑制期 (Inhibition Phase) 的行為一致性：
1. **PSA 初始化與數據累積**：確認在 `PRE_SOLDERING` 狀態下，寫入資料會正確佔用 PSA 緩衝區，且 `dPSADataSize` 屬性變更能即時反映在 `VU 0x4050` 的剩餘緩衝區大小中；同時驗證 `VU 0x404F` 的 Host Read Trim 機制在讀取 Normal/EM1 LUN 時的正確觸發邏輯。
2. **PSA 中斷與恢復**：確認在 `LOADING_COMPLETE` 狀態下執行 HW_RESET 後，韌體能正確進入抑制期，此時 `VU 0x405C` 的 Reflow Progress 與 `VU 0x404F` 的 Migration State 必須維持為 0 (Idle)，且 Host Read Trim 不觸發；驗證 PSA 狀態被正確鎖定為 `LOADING_COMPLETE` 直到首次寫入觸發遷移。
3. **PSA 遷移與硬體抑制**：確認首次寫入後，裝置進入 `SOLDERED` 狀態並啟動背景資料遷移 (Reflow)；驗證在遷移過程中，`VU 0x405C` 的進度值必須嚴格遞增 (0->100)，`VU 0x404F` 的 `IsPsaOngoing` 必須為 1，且 `HostReadWithPSATrim` 必須為 0；若在遷移超過 50% 時執行 HW_RESET，韌體必須能從中斷點恢復遷移，且進度值不得倒退。
4. **VB Trim 狀態驗證**：確認在 PSA 流程中，相關 MLC VB 的 Trim Type 必須為 `PSA (0x01)`；在遷移完成後，VB Trim Type 必須轉變為 `POR (0x00)`。

## Test Case (TC) Checkpoints

1. [PSA_Init_Buffer_Allocation_Check]：
   - 動作：配置 2 個 Normal LUN (LUN 0, 1) 與 2 個 EM1 LUN (LUN 2, 3)，設定 `dPSADataSize` 為 16GB。寫入 8GB 資料至 Normal LUN 後 Unmap，接著將 `bPSAState` 寫入 `PRE_SOLDERING`。隨後寫入 14.5GB 資料至 Normal LUN 及 EM1 LUN。
   - 預期結果：`VU 0x4050` 返回的 `RemainPSABufferSize` 必須精確等於 `16GB - 14.5GB = 1.5GB`；`VU 0x404F` 顯示 `IsPsaOngoing=0`；`VU 0x405C` 顯示 `PercentageForSLCPSAblocks=0`；Health Report 中 `psastate` 為 `PRE_SOLDERING`，`psa_data_size` 為已寫入的 14.5GB 對應區塊數。

2. [PSA_Read_Triggers_Host_Read_Trim_Check]：
   - 動作：在 PSA 緩衝區未滿且狀態為 `PRE_SOLDERING` 時，分別讀取 Normal LUN (LUN 0) 與 EM1 LUN (LUN 2) 的資料。
   - 預期結果：讀取 Normal LUN 後，`VU 0x404F` 的 `HostReadWithPSATrim` 必須變為 1 (代表觸發了 Host Read Trim 機制以釋放緩衝區空間或標記狀態)；讀取 EM1 LUN 後，`HostReadWithPSATrim` 必須恢復為 0 (EM1 LUN 不參與 PSA 緩衝區管理，故不觸發 Trim)。

3. [PSA_Inhibition_Phase_State_Lock_Check]：
   - 動作：將 `bPSAState` 設為 `LOADING_COMPLETE`，執行 HW_RESET 硬體重啟。在重啟後的抑制期 (Inhibition Time, 約 90% 時間內)，輪詢讀取 `VU 0x405C` 與 `VU 0x404F`。
   - 預期結果：在抑制期內，`VU 0x405C` 的 `PercentageForSLCPSAblocks` 與 `PercentageForSLCPSAblocks2` 必須均為 0；`VU 0x404F` 的 `IsPsaOngoing` 必須為 0；Health Report 中的 `psastate` 必須維持為 `LOADING_COMPLETE`。這驗證了韌體在抑制期內禁止任何 PSA 遷移或狀態變更。

4. [PSA_Soldered_Migration_Start_Check]：
   - 動作：抑制期結束後，對 Normal LUN 執行一次 16MB 的寫入操作。
   - 預期結果：寫入完成後，`VU 0x4050` 的 `RemainPSABufferSize` 必須為 0；Health Report 中的 `psastate` 必須變更為 `SOLDERED`；`VU 0x404F` 的 `IsPsaOngoing` 必須變更為 1，表示 PSA 遷移流程已啟動。

5. [PSA_Migration_Polling_Continuity_Check]：
   - 動作：進入輪詢迴圈，持續監控 `VU 0x405C` 的 `PercentageForSLCPSAblocks` 與 `VU 0x404F` 的 `IsPsaOngoing`。
   - 預期結果：
     1. `PercentageForSLCPSAblocks` 必須從 0 遞增到 100，且任何時刻不得出現數值減少的情況 (Progress Decrease Check)。
     2. `PercentageForSLCPSAblocks` 與 `PercentageForSLCPSAblocks2` 必須始終相等。
     3. `HostReadWithPSATrim` 在遷移期間必須始終為 0。
     4. 當進度達到 100% 時，`IsPsaOngoing` 必須變更為 0，標誌遷移完成。

6. [PSA_Migration_Interruption_Recovery_Check]：
   - 動作：在 `VU 0x405C` 進度大於 50% 時，執行 HW_RESET 硬體重啟。
   - 預期結果：重啟後，韌體必須從中斷點繼續遷移。`VU 0x405C` 的進度值必須從重啟前的數值繼續遞增，絕不能重置為 0 或低於重啟前的數值。最終進度仍必須達到 100% 且 `IsPsaOngoing` 歸零。

7. [VB_Trim_Type_Transition_Check]：
   - 動作：在 PSA 流程中 (Step 16 之後) 與遷移完成後 (Step 29 之後)，分別呼叫 `check_vb_mlc_trim`。
   - 預期結果：
     - 流程中：所有屬於 `USED_BLK_POOL_MLC` 與 `CURRENT_L2_MLC` 的 VB，其 `vb_trim` 欄位必須等於 `0x01` (PSA)。
     - 遷移後：上述 VB 的 `vb_trim` 欄位必須等於 `0x00` (POR)，代表資料已從 SLC PSA 區塊遷移至正常 MLC 區塊，且 PSA 標記已清除。