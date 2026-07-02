# Test Spec: UFS Firmware Configuration & SRAM Integrity Verification (Cases 1-10)

## Verification Criterion (VC)
驗證 UFS 韌體中 mConfig/pConfig 在多種寫入途徑（FFU Bin 寫入、VU 直接設定、HW Page 設定）下的持久化與讀回一致性，以及韌體內部 SRAM 結構體（mConfig/pConfig）的記憶體完整性與 ATS 計時器行為：
1.  **Cases 1-3 (FFU Path)**：驗證透過 Host 發送 FFU Write Buffer 更新 FW_HW_BIN 後，韌體在 HW_RESET 或 RESET_N 重啟時，能正確從 Flash 載入並應用修改後的 mConfig/pConfig 版本號（Version），且 VU 讀回值與寫入值一致。
2.  **Cases 4-5 (VU Path)**：驗證透過 Vendor Command 直接修改 VU 中的 mConfig/pConfig 版本號後，韌體重啟能正確持久化該變更，且 Health Report (0x40FE) 中的 PRL 欄位與預期 PRL 匹配。
3.  **Case 6 (HW Page Path)**：驗證透過 Vendor Command 寫入 HW Page 配置後，韌體重啟能正確讀取並應用該 HW Page 數據，確保硬體參數配置無損。
4.  **Cases 7-10 (SRAM Integrity & ATS)**：驗證透過 Vendor Command 直接修改韌體 SRAM 中 `gUfsApiStruct.mconfig` 相關保留欄位（Reserved Fields）後，數據能正確寫入且讀回一致；同時驗證在 L1 模式（Cases 7-8）下 ATS 計時器正常遞增，在 L2 模式（Cases 9-10）下 StartStopUnit 命令能正確執行並等待隊列清空，確保韌體狀態機與計時器邏輯未因記憶體修改而崩潰。

## Test Case (TC) Checkpoints

1.  **[Case01_FFU_Bin_Write_Check]**：
    -   動作：根據 CE 數量計算 `HW_page_offset` 與 `mConfig/pConfig` 在 Bin 中的偏移量。讀取當前 FW_HW_BIN，透過 `codesign_ffu_bin` 包含 mConfig 簽名後，使用 `send_ffu_write_buffer` 將 Bin 寫入裝置。接著執行 HW_RESET 或 RESET_N 重啟。讀取 VU 中的 mConfig 與 pConfig 數據，並與寫入前的 Bin 數據進行比對。
    -   預期結果：VU 讀回的 mConfig 與 pConfig payload 必須與寫入 FFU Bin 中的數據完全一致，證明 FFU 寫入流程能正確更新韌體配置區。

2.  **[Case02_FFU_Bin_mConfig_Version_Change_Check]**：
    -   動作：在當前 Bin 的 `mConfig_in_FW_HW_BIN_offset + 7 + offset` 位置（即 mConfig Version 欄位）寫入隨機值 `randversion` (0x01-0xFF)。重新簽名並透過 `send_ffu_write_buffer` 寫入。執行 HW_RESET 或 RESET_N 重啟。讀取 VU 中的 mConfig 數據，檢查其 Version 欄位。
    -   預期結果：VU 讀回的 mConfig Version 欄位數值必須等於寫入的 `randversion`，證明 FFU 寫入能正確覆蓋並持久化 mConfig 的版本號。

3.  **[Case03_FFU_Bin_pConfig_Version_Change_Check]**：
    -   動作：在當前 Bin 的 `pConfig_in_FW_HW_BIN_offset + 7 + offset` 位置（即 pConfig Version 欄位）寫入隨機值 `randversion`。重新簽名並透過 `send_ffu_write_buffer` 寫入。執行 HW_RESET 或 RESET_N 重啟。讀取 VU 中的 pConfig 數據，檢查其 Version 欄位。
    -   預期結果：VU 讀回的 pConfig Version 欄位數值必須等於寫入的 `randversion`，證明 FFU 寫入能正確覆蓋並持久化 pConfig 的版本號。

4.  **[Case04_VU_mConfig_Version_Change_Check]**：
    -   動作：透過 `project_api.set_mConfig_data` 直接修改 VU 中的 mConfig 結構體，將 `mConfig_Version` 欄位設為隨機值 `randversion`。執行 HW_RESET 或 RESET_N 重啟。讀取 VU 中的 mConfig 數據，並透過 `issue_40FE_to_read_enhanced_health_report` 讀取 Health Report，檢查 `prl` 與 `fw_current_prl` 欄位是否等於預期的 `PRL` 值。
    -   預期結果：VU 讀回的 mConfig Version 必須等於 `randversion`；Health Report 中的 `prl` 與 `fw_current_prl` 必須等於預期的 `PRL` 值，證明 VU 寫入有效且韌體健康報告狀態正常。

5.  **[Case05_VU_pConfig_Version_Change_Check]**：
    -   動作：透過 `project_api.set_pConfig_data` 直接修改 VU 中的 pConfig 結構體，將 `pConfig_version` 欄位設為隨機值 `randversion`。執行 HW_RESET 或 RESET_N 重啟。讀取 VU 中的 pConfig 數據，並檢查 Health Report 中的 `prl` 與 `fw_current_prl` 欄位。
    -   預期結果：VU 讀回的 pConfig Version 必須等於 `randversion`；Health Report 中的 `prl` 與 `fw_current_prl` 必須等於預期的 `PRL` 值，證明 VU 寫入有效且韌體健康報告狀態正常。

6.  **[Case06_HW_Page_Config_Write_Check]**：
    -   動作：備份當前 HW Setting 數據，透過 `project_api.set_HW_page_config_data` 寫入備份的 HW Page 數據（`temp_HW_page`）。執行 HW_RESET 或 RESET_N 重啟。讀取 VU 中的 HW Page 配置數據，並與寫入前的數據進行逐位元比對。
    -   預期結果：VU 讀回的 HW Page 數據必須與寫入的 `temp_HW_page` 完全一致，證明 HW Page 配置能正確持久化並重載。

7.  **[Case07_L1_mConfig_SRAM_Write_Check]**：
    -   動作：進入 Vendor Mode，透過 `api.get_fw_address` 獲取 `gUfsApiStruct.mconfig->m_reserved_9` 的 SRAM 地址。讀取該地址當前值，寫入隨機值 `randvalue` (0x00-0xFE)。等待 15 秒（ATS 計時器檢查），讀取 ATS 計時器並確認其遞增。再次讀取該 SRAM 地址。
    -   預期結果：SRAM 讀回值必須等於寫入的 `randvalue`；ATS 計時器必須遞增，證明 L1 模式下韌體運行正常且記憶體寫入無損。

8.  **[Case08_L1_pConfig_SRAM_Write_Check]**：
    -   動作：進入 Vendor Mode，獲取 `gUfsApiStruct.mconfig->p_reserved_9[0]` 的 SRAM 地址。讀取該地址當前值，寫入隨機值 `randvalue`。等待 15 秒，讀取 ATS 計時器並確認其遞增。再次讀取該 SRAM 地址。
    -   預期結果：SRAM 讀回值必須等於寫入的 `randvalue`；ATS 計時器必須遞增，證明 L1 模式下韌體運行正常且記憶體寫入無損。

9.  **[Case09_L2_mConfig_SRAM_Write_Check]**：
    -   動作：進入 Vendor Mode，獲取 `gUfsApiStruct.mconfig->m_reserved_9` 的 SRAM 地址。讀取該地址當前值，寫入隨機值 `randvalue`。發送 `StartStopUnit` 命令至 `UFS_DEVICE` (LUN 0)，設定 `power_condition=0x02` (Active/Idle)，`start=0`，並等待隊列清空。發送 `StartStopUnit` 命令設定 `power_condition=0x01` (Power Down)，`start=0`，並等待隊列清空。再次讀取該 SRAM 地址。
    -   預期結果：SRAM 讀回值必須等於寫入的 `randvalue`，證明在 L2 模式及電源狀態切換過程中，韌體記憶體數據保持完整且未因狀態機切換而丟失。

10. **[Case10_L2_pConfig_SRAM_Write_Check]**：
    -   動作：進入 Vendor Mode，獲取 `gUfsApiStruct.mconfig->p_reserved_9[0]` 的 SRAM 地址。讀取該地址當前值，寫入隨機值 `randvalue`。發送 `StartStopUnit` 命令至 `UFS_DEVICE` (LUN 0)，設定 `power_condition=0x02`，`start=0`，並等待隊列清空。發送 `StartStopUnit` 命令設定 `power_condition=0x01`，`start=0`，並等待隊列清空。再次讀取該 SRAM 地址。
    -   預期結果：SRAM 讀回值必須等於寫入的 `randvalue`，證明在 L2 模式及電源狀態切換過程中，韌體記憶體數據保持完整且未因狀態機切換而丟失。