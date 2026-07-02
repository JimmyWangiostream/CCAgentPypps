# Test Spec: UFS VDET (Voltage Detector) Functional Verification with Power Cycle & Reset Scenarios

## Verification Criterion (VC)
驗證 UFS 裝置內建電壓檢測機制 (VDET) 在不同電源管理狀態與重置情境下的計數器行為：
1. **正常偵測模式**：確認在裝置處於 Active 狀態且 VDET 功能啟用時，Host 透過 Vendor Command (VU 40B8) 讀取的 `VccDropCnt` 與 `VccqDropCnt` 會在 Host 模擬 VCC/VCCQ 電壓跌落後正確遞增。
2. **電源循環後狀態保持**：確認在經歷 Unipro Reset 及 SSU Sleep/Active 循環後，VDET 計數器能正確累計之前的跌落事件，且不會因電源狀態切換而重置。
3. **VDET 禁用模式**：確認透過 Vendor Command (VU D074) 禁用 VDET 功能後，即使發生電壓跌落，VDET 計數器 (`VccDropCnt`, `VccqDropCnt`) 必須維持不變，證明硬體偵測邏輯已被正確關閉。
4. **HW Reset 後行為**：確認在 HW Reset 後，VDET 功能預設為啟用狀態，且電壓跌落事件能被正常記錄。

## Test Case (TC) Checkpoints

1. [Case01_ONFI_Freq_Verification]:
   - 動作：透過 `api.HwSetting` 將 `POWER_SAVING_CTRL_ENABLE` 設定為 `0x3A` 以禁用 Suspend 功能，確保裝置處於 Active 狀態。接著發送 Vendor Command (VU 4073) 查詢 ONFI 速度，並讀取回應中的 `ONFI_frequency` 欄位。
   - 預期結果：`ONFI_frequency` 的數值必須嚴格等於 `1600`。若不等於 1600，則觸發 `SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH` 異常，代表 Host 與 Device 間的 ONFI 頻率協商或硬體設定存在偏差。

2. [Case02_VDET_Normal_Detection_Check]:
   - 動作：
     1. 禁用 Suspend 功能 (`POWER_SAVING_CTRL_ENABLE = 0x3A`)。
     2. 發送 VU 40B8 讀取初始 VDET 資訊，記錄 `vdet_bk.VccDropCnt` 與 `vdet_bk.VccqDropCnt`。
     3. 執行 `drop_vcc_vccq_voltage()`，該函數會依序將 VCCQ 從 1.08V 降至 1.3V (模擬跌落)，並觸發 SSU Sleep/Active 循環。
     4. 再次發送 VU 40B8 讀取 VDET 資訊，獲取 `vdet.VccDropCnt` 與 `vdet.VccqDropCnt`。
   - 預期結果：`vdet.VccDropCnt` 必須大於 `vdet_bk.VccDropCnt`，且 `vdet.VccqDropCnt` 必須大於 `vdet_bk.VccqDropCnt`。這證明在 VDET 啟用且裝置處於 Active 狀態時，硬體電壓檢測電路成功捕捉到了 VCC/VCCQ 的電壓異常並更新了內部計數器。

3. [Case03_VDET_After_PowerCycle_Check]:
   - 動作：
     1. 在 Case02 的基礎上，手動切換 VCCQ 電壓至 1.15V -> 1.04V -> 1.3V (模擬額外的電壓波動)。
     2. 執行 Unipro Reset (`Dcmd5ResetType.UNIPRO_RESET`)。
     3. 執行 SSU Sleep/Active 循環 (`power_condition=0x02` 進入 Sleep, `0x01` 喚醒)。
     4. 發送 VU 40B8 讀取當前 VDET 資訊，獲取 `vdet`。
     5. 比較 `vdet` 與上一輪記錄的 `vdet_bk` (即 Case02 結束時的狀態)。
   - 預期結果：`vdet.VccDropCnt` 必須等於 `vdet_bk.VccDropCnt`，且 `vdet.VccqDropCnt` 必須等於 `vdet_bk.VccqDropCnt`。此步驟驗證 Unipro Reset 與 SSU 電源狀態切換不會導致 VDET 計數器意外重置或丟失已記錄的跌落事件，確保計數器的持久性與一致性。

4. [Case04_VDET_Disabled_By_VU_D074_Check]:
   - 動作：
     1. 執行 HW Reset (`Dcmd5ResetType.HW_RESET`) 以重置裝置狀態。
     2. 發送 VU 40B8 讀取初始 VDET 資訊，記錄 `vdet_bk`。
     3. 執行 `drop_vcc_vccq_voltage(isDisableVDET=True)`。此函數內部會：
        - 發送 VU D074 禁用 VDET。
        - 執行 VCCQ 電壓切換 (1.08V -> 1.3V)。
        - 執行 SSU Sleep/Active。
        - 發送 VU D074 再次禁用 VDET (確保狀態)。
        - 執行 VCC 電壓切換 (2.1V -> 2.5V)。
        - 執行 Unipro Reset 與 SSU Sleep/Active。
     4. 發送 VU 40B8 讀取最終 VDET 資訊，獲取 `vdet`。
   - 預期結果：`vdet.VccDropCnt` 必須等於 `vdet_bk.VccDropCnt`，且 `vdet.VccqDropCnt` 必須等於 `vdet_bk.VccqDropCnt`。這證明 Vendor Command VU D074 能正確關閉硬體 VDET 偵測邏輯，使得後續的電壓跌落事件不被記錄，計數器保持靜止。

5. [Case05_VDET_HW_Reset_Default_Behavior_Check]:
   - 動作：
     1. 執行 HW Reset (`Dcmd5ResetType.HW_RESET`)。
     2. 發送 VU 40B8 讀取初始 VDET 資訊，記錄 `vdet_bk`。
     3. 執行 `drop_vcc_vccq_voltage()` (預設 `isDisableVDET=False`)，觸發 VCC/VCCQ 電壓跌落及後續的電源循環。
     4. 發送 VU 40B8 讀取最終 VDET 資訊，獲取 `vdet`。
   - 預期結果：`vdet.VccDropCnt` 必須大於 `vdet_bk.VccDropCnt`，且 `vdet.VccqDropCnt` 必須大於 `vdet_bk.VccqDropCnt`。此步驟作為控制組，確認在 HW Reset 後，VDET 功能預設處於啟用狀態，且能正常偵測並記錄電壓跌落事件，與 Case04 形成對比，驗證 VDET 的預設行為與可配置性。