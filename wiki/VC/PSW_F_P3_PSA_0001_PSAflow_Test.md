# Test Spec: UFS PSA (Persistent Storage Area) Flow Validation & State Machine Integrity

## Verification Criterion (VC)
驗證 UFS 裝置在 PSA (Persistent Storage Area) 流程中的狀態機轉換邏輯、寫入限制檢查與硬體狀態持久化機制：
1. **狀態機順序與互斥性**：驗證 `bPSAState` 必須嚴格遵循 `OFF -> PRE_SOLDERING -> LOADING_COMPLETE -> SOLDERED` 的順序，任何跳躍或重複設定（如從 LOADING_COMPLETE 直接設為 PRE_SOLDERING，或在非 OFF 狀態下設為 PRE_SOLDERING）均應返回 `GENERAL_FAILURE (0xFF)`。
2. **PSA Data Size 限制與寫入保護**：驗證 `dPSADataSize` 不可超過 `dPSAMaxDataSize`，且在 `PRE_SOLDERING` 階段，對 PSA Sensitive LUN (Normal Memory) 的寫入會觸發 `TARGET_FAILURE (0x01)` 當數據量超過分配上限或超出 `dPSADataSize` 定義範圍；同時驗證非 PSA Sensitive LUN (EM1) 在此階段仍可正常寫入。
3. **Write Booster 隔離性**：驗證在 `PRE_SOLDERING` 階段寫入 PSA Sensitive LUN 時，Write Booster 緩衝區大小應保持不變（預期值 `0xA`），確保 PSA 數據未進入 WB 路徑。
4. **掉電恢復與狀態持久化**：驗證在 `LOADING_COMPLETE` 狀態下執行 HW_RESET 後，韌體內部狀態應恢復為 `Post_reflow (0x02)` 且 `bPSAState` 屬性維持 `LOADING_COMPLETE`；在 `SOLDERED` 狀態下執行 HW_RESET 後，`bPSAState` 應維持 `SOLDERED` 且數據完整性通過驗證。
5. **RPMB 與 Refresh 機制**：驗證在 `LOADING_COMPLETE` 狀態下執行 RPMB Write 不會改變 PSA 狀態；驗證在 `SOLDERED` 狀態下觸發 Refresh (HIR) 後，VB Trim Type 應從 `PSA` 轉換為 `POR`。

## Test Case (TC) Checkpoints

1. **[PSA_State_Transition_Validation]**：
   - 動作：
     - 嘗試將 `bPSAState` 設為 `LOADING_COMPLETE`（當前為 OFF），預期返回 `GENERAL_FAILURE (0xFF)`。
     - 嘗試將 `bPSAState` 設為 `PRE_SOLDERING`（當前為 OFF，但未 Unmap 數據），預期返回 `GENERAL_FAILURE (0xFF)`。
     - 執行 Unmap 所有 PSA Sensitive LUN 後，將 `bPSAState` 設為 `PRE_SOLDERING`，預期成功。
     - 再次嘗試將 `bPSAState` 設為 `PRE_SOLDERING`（當前已是該狀態），預期返回 `GENERAL_FAILURE (0xFF)`。
     - 嘗試將 `bPSAState` 設為 `PRE_SOLDERING`（當前為 LOADING_COMPLETE），預期返回 `GENERAL_FAILURE (0xFF)`。
     - 嘗試將 `bPSAState` 設為 `LOADING_COMPLETE`（當前為 LOADING_COMPLETE），預期返回 `GENERAL_FAILURE (0xFF)`。
   - 預期結果：所有非預期狀態轉換的 Write Attribute 命令均返回 `QueryResponseCode.GENERAL_FAILURE (0xFF)`；僅在 Unmap 完成後設為 `PRE_SOLDERING` 成功。

2. **[PSA_Data_Size_Limit_Check]**：
   - 動作：
     - 讀取 `dPSAMaxDataSize`，嘗試將 `dPSADataSize` 設為 `dPSAMaxDataSize + 1`。
     - 將 `dPSADataSize` 設為 `dPSAMaxDataSize`。
     - 在 `PRE_SOLDERING` 狀態下，向 PSA Sensitive LUN 寫入數據，總量超過 `dPSADataSize` 但小於 Max PSA SLC VB allocable size，然後嘗試設為 `LOADING_COMPLETE`。
     - 繼續寫入數據，使總量超過 Max PSA SLC VB allocable size。
   - 預期結果：
     - 設定 `dPSADataSize > dPSAMaxDataSize` 時返回 `GENERAL_FAILURE (0xFF)`。
     - 當寫入數據超過 `dPSADataSize` 時，設為 `LOADING_COMPLETE` 返回 `GENERAL_FAILURE (0xFF)`。
     - 當寫入數據超過 Max PSA SLC VB allocable size 時，Write10 命令返回 `UPIUResponse.TARGET_FAILURE (0x01)`。

3. **[Write_Booster_Isolation_in_PRE_SOLDERING]**：
   - 動作：
     - 啟用 Write Booster，讀取初始 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE`。
     - 在 `PRE_SOLDERING` 狀態下，向 PSA Sensitive LUN 寫入 8GB 數據（FUA=1）。
     - 再次讀取 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE`。
   - 預期結果：寫入前後 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 均為 `0xA`，證明 PSA 敏感數據未佔用 Write Booster 緩衝區。

4. **[Non_Sensitive_LU_Access_in_PRE_SOLDERING]**：
   - 動作：
     - 在 `PRE_SOLDERING` 狀態下，向非 PSA Sensitive LUN (EM1 Memory Type) 寫入數據。
   - 預期結果：Write10 命令成功執行，無錯誤返回，證明非敏感 LUN 在 PSA 流程中仍可正常存取。

5. **[Power_Cycle_Recovery_in_LOADING_COMPLETE]**：
   - 動作：
     - 將 `bPSAState` 設為 `LOADING_COMPLETE`。
     - 執行 HW_RESET (Power Cycle)。
     - 透過 Vendor Command 讀取韌體 Debug Info 的 payload 第 469 位元組。
     - 讀取 `bPSAState` 屬性。
   - 預期結果：
     - 韌體內部分配狀態 `payload[469]` 必須等於 `0x02` (Post_reflow)。
     - `bPSAState` 屬性必須維持在 `LOADING_COMPLETE`，證明狀態在掉電後未丟失。

6. **[RPMB_Access_in_LOADING_COMPLETE]**：
   - 動作：
     - 在 `LOADING_COMPLETE` 狀態下，執行 RPMB Region 0 的 Key Programming 與 Data Write。
     - 嘗試將 `bPSAState` 設為 `PRE_SOLDERING` 或 `LOADING_COMPLETE`。
   - 預期結果：
     - RPMB 寫入成功。
     - 嘗試改變 `bPSAState` 均返回 `GENERAL_FAILURE (0xFF)`，證明 RPMB 操作不影響 PSA 狀態機鎖定。

7. **[Soldered_State_Transition_and_Persistence]**：
   - 動作：
     - 在 `LOADING_COMPLETE` 狀態下，向 PSA Sensitive LUN 寫入有效數據（LBA 在範圍內）。
     - 讀取 `bPSAState`。
     - 嘗試將 `bPSAState` 設為 `OFF`、`PRE_SOLDERING`、`LOADING_COMPLETE`。
     - 執行 HW_RESET。
     - 讀取 `bPSAState` 並執行 Data Compare。
   - 預期結果：
     - 寫入有效數據後，`bPSAState` 自動變更為 `SOLDERED`。
     - 嘗試改變 `bPSAState` 均返回 `GENERAL_FAILURE (0xFF)`。
     - HW_RESET 後，`bPSAState` 維持 `SOLDERED`。
     - Data Compare 通過，證明數據完整性。

8. **[Refresh_Mechanism_Verification_in_SOLDERED]**：
   - 動作：
     - 在 `SOLDERED` 狀態下，觸發 HIR (Hardware Interrupt Request) 以啟動 Refresh 流程。
     - 輪詢 `REFRESH_STATUS` 屬性直到等於 `0x03` (Refresh Complete)。
     - 呼叫 `check_vb_mlc_trim` 檢查 VB Trim Type。
   - 預期結果：
     - `REFRESH_STATUS` 最終變為 `0x03`。
     - VB Trim Type 從 `PSA (1)` 變更為 `POR (0)`，證明 Refresh 機制正確重置了 PSA 相關的 VB 標記。