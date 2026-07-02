# Test Spec: Sticky Read Feature Validation with UECC Injection and Power Cycle Persistence

## Verification Criterion (VC)
驗證 UFS 韌體中 Sticky Read（黏著讀取）機制在異常電源循環下的狀態保持能力與錯誤恢復行為：
1. **基礎功能驗證**：確認在正常運行狀態下，透過 Vendor Command `0x4066` 啟用 Sticky Read 並強制當前 Read Last Table 為 Sticky Read 後，當針對特定 LBA 執行讀取並觸發 UECC 錯誤（透過 `0xD014` 注入）時，韌體應自動切換至 Sticky Read 模式以恢復資料，且透過 `0x4066` 查詢狀態應回報 `STICKY_READ_ENTERED` 及正確的 Offset。
2. **禁用驗證**：確認在禁用 Sticky Read 功能後，即使發生相同的 UECC 錯誤情境，韌體不應進入 Sticky Read 模式，狀態應回報 `STICKY_READ_NOT_ENTERED`。
3. **掉電持久性驗證（核心目標）**：確認在 Sticky Read 已啟用且設定完成後，執行 `HW_RESET`（硬體重啟/掉電）後，韌體在重新初始化階段應自動恢復 Sticky Read 狀態。再次針對同一物理位置（Die/Page/Block）觸發 UECC 錯誤時，系統仍應處於 `STICKY_READ_ENTERED` 狀態，證明 Sticky Read 的設定或狀態已持久化於非易失性儲存或韌體記憶體中，未因掉電而遺失。

## Test Case (TC) Checkpoints

1. [Case01_Disable_StickyRead_NoEnter_Check]：
   - 動作：
     1. 配置 LUN0 為 Normal LU，LUN1 為 EM1 LU，並分別寫入 1 VB 大小的資料。
     2. 針對 LUN0 (TLC) 或 LUN1 (SLC) 隨機選取一個 LBA，透過 `0x4051` VUC 轉換為物理地址 (PBA)，取得 Die, Plane, Block, Page 資訊。
     3. 計算該 Page 對應的 `PAGE_TYPE` 並選取一個 `READ_LAST_TABLE` 索引。
     4. 透過 `0xD014` VUC 設定 Read Last Table 參考資料。
     5. 執行 `0x4066` VUC 禁用 Sticky Read (`STICKY_READ_SETTING.DISABLE`)。
     6. 透過 `0xD014` VUC 在該物理位置注入 UECC 錯誤（設定 Read Recovery Module），並執行讀取操作。
     7. 執行 `0x4066` VUC 查詢 Sticky Read 狀態。
   - 預期結果：
     - `0x4066` 查詢結果中 `result` 必須為 `SUCCESS (0)`。
     - `stickyReadStatus` 必須等於 `STICKY_READ_NOT_ENTERED`。
     - 查詢回傳的 `offset1/2/3` 必須與參考表中的預期值**不相等**，證明韌體未啟用 Sticky Read 機制。

2. [Case02_Enable_StickyRead_Enter_Check]：
   - 動作：
     1. 保持 Case01 相同的 LBA 與物理地址配置。
     2. 執行 `0x4066` VUC 啟用 Sticky Read (`STICKY_READ_SETTING.ENABLE`)。
     3. 執行 `0x4066` VUC 強制將當前 Read Last Table 設為 Sticky Read (`force_read_last_as_sticky_read`)，隨機選取 ARC (0-2)。
     4. 透過 `0xD014` VUC 在相同物理位置注入 UECC 錯誤，並執行讀取操作。
     5. 執行 `0x4066` VUC 查詢 Sticky Read 狀態。
   - 預期結果：
     - `0x4066` 查詢結果中 `result` 必須為 `SUCCESS (0)`。
     - `stickyReadStatus` 必須等於 `STICKY_READ_ENTERED`。
     - 查詢回傳的 `offset1/2/3` 必須與參考表中的預期值**完全相等**，證明韌體成功切換至 Sticky Read 模式並使用正確的 Offset 恢復資料。

3. [Case03_PowerCycle_Persistence_Check]：
   - 動作：
     1. 在 Case02 成功進入 Sticky Read 狀態後，執行 `init_tester_to_unit_ready(Dcmd5ResetType.HW_RESET)` 進行硬體重啟（模擬異常掉電）。
     2. 韌體重新初始化後，透過 `0xD014` VUC 重新設定 Read Last Table 參考資料。
     3. 針對**相同的物理地址**（Die, Page, Block），再次執行 `0x4066` VUC 強制將當前 Read Last Table 設為 Sticky Read（模擬韌體上電後的自動恢復或手動觸發機制，根據程式碼邏輯，此處再次呼叫 force 是為了確保狀態載入，但關鍵在於後續檢查是否仍處於 Sticky 狀態）。
     4. 透過 `0xD014` VUC 在相同物理位置注入 UECC 錯誤，並執行讀取操作。
     5. 執行 `0x4066` VUC 查詢 Sticky Read 狀態。
   - 預期結果：
     - `0x4066` 查詢結果中 `result` 必須為 `SUCCESS (0)`。
     - `stickyReadStatus` 必須等於 `STICKY_READ_ENTERED`。
     - 查詢回傳的 `offset1/2/3` 必須與參考表中的預期值**完全相等**。
     - **關鍵驗證點**：這證明即使經過 `HW_RESET`，Sticky Read 的功能狀態或相關配置（如 Read Last Table 的映射關係）在韌體重啟後依然有效，能夠在發生 UECC 時自動或半自動地進入 Sticky Read 模式進行錯誤恢復，而非退回到普通讀取模式。