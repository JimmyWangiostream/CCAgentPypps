# Test Spec: UFS NAND Trim Table Consistency & Power Cycle Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在模擬不同 MLC Block Erase Count (EC) 閾值情境下，NAND Trim Table (透過 Vendor Command 0x4084 讀取) 是否能正確對應至 pConfig 中設定的 `TEMPCO_TRIM` 數值，並確認在不同電源循環條件（HW_RESET with/without VCC Power Off, SSU with/without VCC Power Off）下，該 Trim 表的一致性與恢復機制：
1. **EC 模擬與 Trim 映射驗證**：透過 Vendor Command 寫入模擬的 EC 值，確認韌體讀取的 NAND Trim 值嚴格等於 pConfig 中對應 EC 組別（EC1~EC4）的 `TEMPCO_TRIM` 前 24 個數值。
2. **電源循環穩定性驗證**：在設定特定 EC 閾值後，執行 HW_RESET 或 SSU 配合 VCC 斷電/上電循環，驗證韌體在重新初始化後，NAND Trim 值仍保持與該 EC 閾值對應的 `TEMPCO_TRIM` 一致，未發生漂移或錯誤載入。
3. **恢復機制驗證**：測試結束後，透過 Vendor Command 恢復原始 EC 表並執行 HW_RESET，確認 NAND Trim 值恢復為設備出廠預設值（Default Trim Values）。

## Test Case (TC) Checkpoints

1. [Case01_PreCheck_DefaultTrim_Verification]：
   - 動作：從 pConfig 讀取 `XTEMP_EC` 閾值（索引 28-35）與 `TEMPCO_TRIM_ADDR`（索引 36-99），並解析出 EC1~EC4 對應的 `TEMPCO_TRIM` 數據（各 32 bytes，取前 24 bytes）。透過 Vendor Command 0x4084 讀取當前 NAND Trim 值，並計算當前 MLC 平均 Erase Count (`l4180_d2d3_avg_erase_cnt`)。比對當前平均 EC 與 `XTEMP_EC` 閾值，確認當前 Trim 值是否等於對應 EC 組別的 `TEMPCO_TRIM`。
   - 預期結果：當前 MLC 平均 EC 必須大於或等於某個 `XTEMP_EC` 閾值，且讀取的 NAND Trim 值（6 組地址，每組 4 bytes，共 24 個整數）必須精確等於該 EC 組別在 pConfig 中定義的 `TEMPCO_TRIM` 前 24 個數值。若不一致，測試失敗並恢復 EC 表。

2. [Case02_EC_Simulation_HW_Reset_Verification]：
   - 動作：針對 EC1~EC4 四個閾值分別執行循環。對每個 EC 閾值，透過 `set_device_ec` 寫入對應的模擬 EC 值至 SRAM。接著執行 `api.init_tester_to_unit_ready` 設定 `resetmode=HW_RESET` 且 `powerdown=True`（模擬完整掉電重啟）。重啟後，透過 Vendor Command 讀取 FW Geometry 中的 `l4180_d2d3_avg_erase_cnt`，並透過 Vendor Command 0x4084 讀取 NAND Trim 值。
   - 預期結果：讀回的 `l4180_d2d3_avg_erase_cnt` 必須等於設定的模擬 EC 值；讀回的 NAND Trim 值（24 個整數）必須精確等於該 EC 閾值對應的 `TEMPCO_TRIM` 前 24 個數值。

3. [Case03_EC_Simulation_HW_Reset_No_PowerOff_Verification]：
   - 動作：針對 EC1~EC4 四個閾值分別執行循環。對每個 EC 閾值，透過 `set_device_ec` 寫入對應的模擬 EC 值。接著執行 `api.init_tester_to_unit_ready` 設定 `resetmode=HW_RESET` 且 `powerdown=False`（模擬僅硬體重啟，VCC 不斷電）。重啟後，讀取 FW Geometry 中的 `l4180_d2d3_avg_erase_cnt` 及透過 Vendor Command 0x4084 讀取 NAND Trim 值。
   - 預期結果：讀回的 `l4180_d2d3_avg_erase_cnt` 必須等於設定的模擬 EC 值；讀回的 NAND Trim 值（24 個整數）必須精確等於該 EC 閾值對應的 `TEMPCO_TRIM` 前 24 個數值。

4. [Case04_EC_Simulation_SSU_VCC_Off_Verification]：
   - 動作：針對 EC1~EC4 四個閾值分別執行循環。對每個 EC 閾值，透過 `set_device_ec` 寫入對應的模擬 EC 值。接著發送 SSU (StartStopUnit) 命令，設定 `lun=UFS_DEVICE`, `power_condition=2` (Sleep/Standby)，並等待隊列清空。隨後執行 `VCC_power_off_power_on`（切斷 VCC 電源再恢復）。最後發送 SSU 命令喚醒設備 (`power_condition=1`)。重啟後，透過 Vendor Command 0x4084 讀取 NAND Trim 值。
   - 預期結果：讀回的 NAND Trim 值（24 個整數）必須精確等於該 EC 閾值對應的 `TEMPCO_TRIM` 前 24 個數值，證明在 SSU 配合 VCC 斷電循環後，Trim 表狀態仍正確維持。

5. [Case05_EC_Simulation_SSU_VCC_On_Verification]：
   - 動作：針對 EC1~EC4 四個閾值分別執行循環。對每個 EC 閾值，透過 `set_device_ec` 寫入對應的模擬 EC 值。接著發送 SSU 命令，設定 `lun=UFS_DEVICE`, `power_condition=3` (Power Down)，並等待隊列清空。隨後執行 `VCC_power_off_power_on`（切斷 VCC 電源再恢復）。最後發送 SSU 命令喚醒設備 (`power_condition=1`)。重啟後，透過 Vendor Command 0x4084 讀取 NAND Trim 值。
   - 預期結果：讀回的 NAND Trim 值（24 個整數）必須精確等於該 EC 閾值對應的 `TEMPCO_TRIM` 前 24 個數值，證明在 SSU Power Down 配合 VCC 斷電循環後，Trim 表狀態仍正確維持。

6. [Case06_ECRecovery_DefaultState_Verification]：
   - 動作：測試結束後，呼叫 `recover_ec` 將 SRAM 中的 EC 表恢復為測試前的備份值。接著執行 `api.init_tester_to_unit_ready` 設定 `resetmode=HW_RESET` 且 `powerdown=True`。重啟後，透過 Vendor Command 0x4084 讀取 NAND Trim 值。
   - 預期結果：讀回的 NAND Trim 值（24 個整數）必須精確等於測試開始前儲存的 `defaultlist`（即設備出廠預設的 NAND Trim 值），證明 EC 表恢復機制正確且設備狀態已回到初始預設狀態。