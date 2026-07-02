# Test Spec: UFS Rain Recovery Mechanism Verification (TLC/SLC/WB)

## Verification Criterion (VC)
驗證 UFS 韌體在「Host Permanent Rain」功能關閉與開啟狀態下，針對 PTE LWP (Last Valid Page) 的錯誤處理與資料恢復機制：
1. **Disable Rain 情境**：確認在 Host Permanent Rain 功能關閉時，寫入的 VB 最後有效頁 (LWP) 不會編碼 Parity (FW Spare Mark 為 0x83)，且該頁若發生 UECC 錯誤，韌體不會嘗試修復，直接返回 UECC 狀態。
2. **Enable Rain 情境**：確認在 Host Permanent Rain 功能開啟時，韌體能透過 Parity 資訊成功修復 LWP 的 UECC 錯誤，並返回正常讀取結果 (Read Compare Pass)。
3. **模式覆蓋**：此驗證邏輯需涵蓋 TLC、SLC 及 Write Booster (WB) 三種操作模式，確保不同 Flash 編碼與快取策略下的 Rain 機制一致性。

## Test Case (TC) Checkpoints

1. [Case01_Disable_Rain_No_Parity_Check]：
   - 動作：
     1. 針對當前測試模式 (TLC/SLC/WB)，透過 `issue_D08B` 將 Host Permanent Rain 的 BIT0/1/2 (對應 `Rain_in_last_valid_page`) 設為 Disable。
     2. 寫入 1 個 VB 資料至目標 LUN，並透過 `create_closed_vb` 獲取最後有效頁的 VB 地址。
     3. 計算該頁的 PCA (Physical Channel Address)，針對 TLC 模式設定 `b4_mode=2`，SLC 模式設定 `b4_mode=1`，並指定對應的 CE/Plane/Page。
     4. 執行 `direct_read` 讀取該頁原始資料，檢查 FW Spare Mark (偏移量 0x4004)。
   - 預期結果：FW Spare Mark 必須等於 `0x83`。這代表在 Rain 功能關閉時，韌體未對最後有效頁進行 Parity 編碼，該頁僅為 Dummy 狀態，無錯誤修復能力。

2. [Case02_Enable_Rain_UECC_Recovery_Check]：
   - 動作：
     1. 執行 HW_RESET (POR) 重置系統，並根據測試模式設定 Write Booster 標誌。
     2. 再次寫入 1 個 VB 資料，獲取新的 LWP PCA。
     3. 透過 `inject_UECC` 在該 LWP 頁面注入單比特或多比特 UECC 錯誤。
     4. 再次執行 HW_RESET (POR) 觸發韌體初始化流程。
     5. 透過 `issue_D08B` 將 Host Permanent Rain 的 BIT4/5/6 (對應 `data_recovery`) 設為 Enable。
     6. 先執行 `direct_read_raw_data_and_check_status`，設定 `expect_status=ReadStatus.UECC` 且 `REH_Enable=True`，驗證韌體在錯誤發生時的初始狀態。
     7. 接著透過 `issue_D08B` 確保 BIT4/5/6 維持 Enable 狀態。
     8. 執行 `read_compare_rain_result`，嘗試讀取並比對該頁資料。
   - 預期結果：
     - 步驟 6 中，讀取狀態必須返回 `UECC`，確認錯誤已被硬體或韌體偵測到。
     - 步驟 8 中，讀取比對必須成功 (`expect_error=False`)，代表韌體在 Rain 功能開啟時，成功利用 Parity 資訊修復了 LWP 的 UECC 錯誤，資料恢復正常。

3. [Case03_Mode_Coverage_Verification]：
   - 動作：重複上述 Case01 與 Case02 的邏輯，分別在 `TestMode.TEST_TLC`、`TestMode.TEST_SLC` 與 `TestMode.TEST_WB` 三種模式下執行。
     - TLC 模式：`last_pageline` 設為 1111，`b4_mode` 設為 2。
     - SLC/WB 模式：`last_pageline` 設為 1103，`b4_mode` 設為 1。
     - WB 模式：需額外設定 `api.FlagIDN.WRITEBOOSTER_EN`。
   - 預期結果：所有三種模式下，Disable Rain 時 FW Spare Mark 均為 0x83；Enable Rain 時，注入 UECC 後均能成功修復並通過 Read Compare。這驗證了 Rain 機制在不同 Flash 編碼密度與快取行為下的硬體行為一致性。