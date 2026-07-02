# Test Spec: UFS Enhanced Health Report & Power State Counter Verification

## Verification Criterion (VC)
驗證 UFS 裝置在多種操作情境下，Enhanced Health Report (VU 0x40FE) 與 Device Health Descriptor (IDN 0xF8) 中計數器與狀態欄位的準確性與一致性：
1. **基礎配置與寫入加速器 (WB)**：確認 LUN 0 (TLC/Normal) 與 LUN 3 (EM1/Enhanced_1) 的 Thin Provisioning 配置正確，且 Write Booster Buffer 的可用空間 (Available WB Size) 與 SLC Cache 相關計數器符合預設幾何結構。
2. **資料傳輸計數**：驗證對 LUN 0 與 LUN 3 執行特定大小的 Read/Write 操作後，Health Report 中對應的 `read_data_size_tlc/em1` 與 `write_data_size_tlc/em1` 欄位是否正確累加。
3. **電源狀態轉換計數**：驗證執行 SSU (Start/Stop Unit) 進入 Sleep (PC=0x02), Power Down (PC=0x03), Deep Sleep (PC=0x04) 及喚醒流程後，`sleep_state_counter`, `power_down_state_counter`, `deep_sleep_state_counter` 是否正確遞增。
4. **初始化與異常關機計數**：驗證 HW_RESET 配合 Power Down (Safe Shutdown) 與無 Power Down (Unsafe Shutdown) 情境下，`initialization_count_success/failure`, `safe/unsafe_shutdown_initialization_count`, `init_count_pon/spor` 及 `spor_recovery_count` 的變化邏輯。
5. **環境與電壓監控**：驗證 VDET (Voltage Detection) 在 VCC/VCCQ 電壓切換時觸發計數增加，以及透過 Vendor Command 修改溫度邊界後，`too_high/low_temperature_count` 的觸發機制。
6. **配置鎖定機制**：驗證 `CONFIG_DESCR_LOCK` 屬性寫入 0x1 後，Health Report 中的 `bconfigdescrlock` 欄位同步鎖定，且透過 VU 0xD085 解鎖後恢復正常。

## Test Case (TC) Checkpoints

1. **[LUN_Config_WB_Initial_Check]**：
   - 動作：透過 `config_lun` 配置 4 個 Config Descriptor，其中 LUN 0 設為 NORMAL (TLC) 並分配 1/3 Total AU，LUN 3 設為 ENHANCED_1 (EM1) 並分配 1/3 Total AU，其餘禁用。寫入配置後，讀取 Health Report，並透過 `api.read_attribute` 讀取 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 與 `CURRENT_WRITEBOOSTER_BUFFER_SIZE`。
   - 預期結果：Health Report 中 `available_write_booster_size` 必須等於 `int(4096 / 1242)`；`max_slc_cache_wb_size` 必須等於 `int(4096 / 10)`；`available_slc_cache_wb_buffer_size` 必須等於 100。這確認了 Write Booster Buffer 的幾何結構與初始狀態符合韌體定義。

2. **[TLC_EM1_Data_Transfer_Counter_Check]**：
   - 動作：記錄初始 Health Report 中的 `read_data_size_tlc_unit_100mb`, `read_data_size_for_em1_unit_100mb`, `write_data_size_tlc_unit_100mb`, `write_data_size_for_em1_unit_100mb`。接著對 LUN 0 執行 100MB (BLOCK4K_SIZE_100M_BYTE) 的 Write 與 Read，再對 LUN 3 執行同樣大小的 Write 與 Read。最後重新讀取 Health Report。
   - 預期結果：LUN 0 (TLC) 的 Read/Write 計數器必須大於初始值（增加至少 1 單位）；LUN 3 (EM1) 的 Read/Write 計數器也必須大於初始值。這驗證了韌體能正確區分並累加不同 Memory Type (TLC vs EM1) 的 I/O 數據量。

3. **[SSU_Power_State_Counter_Check]**：
   - 動作：
     - **Sleep**: 記錄 `sleep_state_counter`，發送 SSU (PC=0x02) 進入 Sleep，再發送 SSU (PC=0x01) 喚醒，讀取 Health Report。
     - **Power Down**: 記錄 `power_down_state_counter`，發送 SSU (PC=0x03) 進入 Power Down，再發送 SSU (PC=0x01) 喚醒，讀取 Health Report。
     - **Deep Sleep**: 記錄 `deep_sleep_state_counter`，發送 SSU (PC=0x04) 進入 Deep Sleep，執行 HW_RESET 恢復，讀取 Health Report。
   - 預期結果：每次對應的電源狀態轉換後，`sleep_state_counter`, `power_down_state_counter`, `deep_sleep_state_counter` 必須分別增加至少 1。這驗證了 UFS 裝置在進入不同 SSU 電源狀態並成功恢復後，硬體計數器能正確追蹤狀態轉換次數。

4. **[Safe_Unsafe_Shutdown_Init_Counter_Check]**：
   - 動作：
     - **Safe Shutdown**: 記錄 `initialization_count_success`, `safe_shutdown_initialization_count`, `init_count_pon`。執行 `write_data` 確保資料落盤，接著執行 `init_tester_to_unit_ready` (HW_RESET + Power Down=True)。讀取 Health Report。
     - **Unsafe Shutdown**: 記錄 `initialization_count_failure`, `init_count_spor`, `unsafe_shutdown_initialization_count`, `spor_recovery_count`。執行 `write_data`，接著執行 `init_tester_to_unit_ready` (HW_RESET + Power Down=False)。讀取 Health Report。隨後執行 RESET_N 恢復，再次讀取確認 `spor_recovery_count` 增加。最後執行 HW_RESET + Power Down=True 恢復，確認 `spor_recovery_count` 不再增加。
   - 預期結果：
     - Safe Shutdown 後：`initialization_count_success`, `safe_shutdown_initialization_count`, `init_count_pon` 均增加 1。
     - Unsafe Shutdown 後：`initialization_count_failure`, `init_count_spor`, `unsafe_shutdown_initialization_count` 均增加 1，且 `spor_recovery_count` 增加 1。
     - RESET_N 後：`spor_recovery_count` 再次增加 1（代表 Sporadic Recovery 嘗試）。
     - 最終 Safe Shutdown 後：`spor_recovery_count` 保持不變。這驗證了韌體能正確區分有無電源供應的關機行為，並正確追蹤 SPOR (Sudden Power Off Recovery) 的恢復狀態。

5. **[VDET_Temperature_Boundary_Check]**：
   - 動作：
     - **VDET**: 記錄 `vdet_count`。執行 `drop_vcc_vccq_voltage`，該函數會切換 VCCQ 至 1.08V/1.3V 及 VCC 至 2.1V/2.5V，並觸發 Unipro Reset 與 SSU Sleep/Active。讀取 Health Report。
     - **Temperature**: 記錄 `too_high_temperature_count` 與 `too_low_temperature_count`。透過 Vendor Command (VUC) 修改 `DEVICE_TOO_HIGH_TEMP_BOUNDARY` 為 80，讀取 Health Report 確認計數增加。再修改 `DEVICE_TOO_LOW_TEMP_BOUNDARY` 為 180，讀取 Health Report 確認計數增加。最後恢復原始邊界值。
   - 預期結果：
     - VDET 測試後：`vdet_count` 必須增加至少 1，證明電壓異常偵測機制在電壓切換與重置過程中被觸發。
     - Temperature 測試後：修改高溫邊界後 `too_high_temperature_count` 增加；修改低溫邊界後 `too_low_temperature_count` 增加。這驗證了韌體能根據動態設定的溫度邊界屬性正確更新健康報告中的環境異常計數。

6. **[Config_Lock_Attribute_Sync_Check]**：
   - 動作：記錄初始 Health Report 中的 `bconfigdescrlock`。讀取 Attribute IDN 0x0B (`CONFIG_DESCR_LOCK`)。將其寫入 0x1。再次讀取 Attribute 與 Health Report。接著發送 Vendor Command 0xD085 解鎖 LUN 配置。再次讀取 Attribute 與 Health Report。
   - 預期結果：
     - 寫入 Attribute 0x0B 為 0x1 後，Health Report 中的 `bconfigdescrlock` 必須同步變為 0x1。
     - 執行 0xD085 解鎖後，Attribute 0x0B 必須變回 0x0，且 Health Report 中的 `bconfigdescrlock` 也必須變回 0x0。
     - 這驗證了 UFS 標準屬性與 Vendor 健康報告欄位之間的硬體同步機制，確保配置鎖定狀態的一致性。

7. **[Health_Descriptor_Binary_Sync_Check]**：
   - 動作：透過 `pattern_get_health_descriptor_then_check`，發送 Read Descriptor (IDN 0xF8) 獲取 Device Health Descriptor 的二進制數據，並與之前透過 VU 0x40FE 獲取的 Enhanced Health Report payload 進行逐位元比對。
   - 預期結果：兩者之間的差異位元數 (diff_item) 必須小於或等於 10。這驗證了標準 UFS Device Health Descriptor 與 Vendor 擴充健康報告在核心狀態欄位上的數據一致性，確保標準工具與 Vendor 工具讀取的裝置健康狀態無衝突。