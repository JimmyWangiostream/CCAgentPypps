# Test Spec: UFS PSA State Transition & In-Progress Module Cleanup Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 PSA (Production State Authentication) 狀態機從 OFF 轉換至 PRE_SOLDERING、LOADING_COMPLETE 最終到達 SOLDERED 的過程中，硬體狀態機與韌體行為的正確性：
1. **PSA State Transition**：確認 Host 透過 Write Attribute 設定 `bPSAState` 後，Device 能正確回應並維持在對應的狀態（OFF -> PRE_SOLDERING -> LOADING_COMPLETE -> SOLDERED），且在 HW_RESET 後狀態鎖定於 SOLDERED。
2. **In-Progress Module Cleanup**：在 PSA 狀態為 OFF 或 SOLDERED 時，確認所有進行中的硬體模組（RPMB、HID/Defrag、Write Booster、HIR/Refresh）必須被強制清除或重置。
3. **Data Integrity during Reconfiguration**：在 HID Analysis/Defrag、Write Booster Flush、HIR Refresh 等模組處於 "In-Progress" 狀態時，執行 LUN 重新配置（Re-configuration），驗證這些模組的狀態是否被正確重置為 Idle/0，且 RPMB 關鍵數據在 LUN 配置變更後保持完整無損。

## Test Case (TC) Checkpoints

1. [PSA_State_Transition_Check]:
   - 動作：
     1. 將 LUN0 設為 Normal，LUN1 設為 EM1，並寫入 RPMB Key。
     2. 透過 VUC D085 解鎖 Config Descriptor，並透過 VUC C083 將 VB Erase Count 設為 1。
     3. 寫入 `PSA_DATA_SIZE` 屬性為最大值，並對 LUN0 發送 Unmap 命令。
     4. 讀取 `PSA_STATE` 屬性，確認為 `OFF` (0x00)。
     5. 寫入 `PSA_STATE` 為 `PRE_SOLDERING` (0x01)，讀取確認狀態。
     6. 寫入 `PSA_STATE` 為 `LOADING_COMPLETE` (0x02)，讀取確認狀態。
     7. 執行 HW_RESET (Power Cycle)。
     8. 對 LUN0 寫入 16MB 固定模式資料 (Pattern Mode: HW_FIX)。
     9. 讀取 `PSA_STATE` 屬性。
   - 預期結果：
     - 步驟 4-6：`PSA_STATE` 屬性值必須分別等於 0x00, 0x01, 0x02。
     - 步驟 9：`PSA_STATE` 屬性值必須等於 `SOLDERED` (0x03)。這代表在 LOADING_COMPLETE 狀態下執行 HW_RESET 後，韌體將 PSA 狀態強制鎖定為 SOLDERED，且寫入操作成功完成。

2. [RPMB_Integrity_After_Reconfig_Check]:
   - 動作：
     1. 對 RPMB Region 0 寫入 4 個 LBA 的測試資料，並記錄 MAC 與 Data。
     2. 隨機生成 Normal/EM1 比例（例如 50/50），執行 LUN 重新配置（Re-configuration）。
     3. 重新讀取 RPMB Region 0 的相同 4 個 LBA 資料。
   - 預期結果：
     - 讀回的 RPMB Data 與 MAC 必須與寫入前完全一致。這驗證了在 LUN 配置變更（涉及 Alloc Units 重新分配）的過程中，RPMB 的獨立儲存空間與 Key 機制未受影響，數據完整性得以維持。

3. [HID_Cleanup_Verification]:
   - 動作：
     1. 對 LUN0 與 LUN1 分別寫入大量資料（1GB+4GB），並穿插隨機寫入。
     2. 寫入 `DEFAG_OPERATION` 屬性為 `Analysis` (0x01)，輪詢 `HID_STATE` 直到其變為 `Required` (0x02)。
     3. 再次隨機寫入觸發 Defrag。
     4. 寫入 `DEFAG_OPERATION` 屬性為 `Analysis_And_Defrag` (0x02)。
     5. 讀取 `HID_STATE`，確認其變為 `Defrag_In_Progress` (0x03)。
     6. 在 Defrag 進行中，執行 LUN 重新配置（改變 Normal/EM1 比例）。
     7. 讀取 `HID_STATE` 與 `HID_PROGRESS_RATIO`。
   - 預期結果：
     - 步驟 7：`HID_STATE` 必須變為 `Idle` (0x00)，且 `HID_PROGRESS_RATIO` 必須為 0。這代表當 Host 介入並重新配置 LUN 時，硬體必須立即中止正在進行的 HID Defrag 流程，並清除所有相關狀態暫存器。

4. [Write_Booster_Cleanup_Verification]:
   - 動作：
     1. 啟用 Write Booster Flag，並對 LUN0 進行連續寫入（每次 1GB），直到 `EXC_EVENT_STATUS` 的 Bit 5 被設定（表示 WB Buffer 滿需 Flush）。
     2. 讀取 `WRITE_BOOSTER_BUFFER_FLUSH_STATUS`，確認其為 `In_Progress` (0x01)。
     3. 設定 `WRITE_BOOSTER_BUFFER_FLUSH_EN` Flag 觸發 Flush。
     4. 在 Flush 狀態為 `In_Progress` 時，執行 LUN 重新配置。
     5. 讀取 `WRITE_BOOSTER_BUFFER_FLUSH_STATUS`。
   - 預期結果：
     - 步驟 5：`WRITE_BOOSTER_BUFFER_FLUSH_STATUS` 必須變為 `Idle` (0x00)。這驗證了 LUN 重新配置會強制終止並清除 Write Booster 的 Flush 作業，確保硬體狀態回到初始 Idle 模式。

5. [HIR_Cleanup_Verification]:
   - 動作：
     1. 設定 `REFRESH_UNIT` 為 Whole Device (0x01)，`REFRESH_METHOD` 為 Manual Force (0x01)。
     2. 對 LUN0 與 LUN1 寫入 4GB 資料，並進行隨機寫入與 Erase。
     3. 啟用 `REFRESH_EN` Flag。
     4. 輪詢 Device Health Descriptor 中的 `l41_refresh_progress`，直到其值大於 0 且隨後變為 0（表示 Refresh 正在進行或剛完成）。
     5. 在 `refresh_progress` 大於 0 的瞬間（In-Progress），執行 LUN 重新配置。
     6. 讀取 `REFRESH_STATUS` 屬性與 Device Health Descriptor 中的 `l41_refresh_progress`。
   - 預期結果：
     - 步驟 6：`REFRESH_STATUS` 必須變為 `Idle` (0x00)，且 `l41_refresh_progress` 必須為 0。這驗證了硬體在接收到 LUN 重新配置指令時，會立即中止正在進行的 HIR (Health Information Refresh) 流程，並重置進度計數器。