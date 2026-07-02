# Test Spec: Rain Parity Recovery Mechanism Verification (UECC Injection & Data Recovery)

## Verification Criterion (VC)
驗證韌體在「Rain Parity (RAID-like protection)」機制下的錯誤恢復能力：
1. **Disable Parity Check**: 確認在 Host 透過 VU D08B 關閉 Full Block Protection (BIT0/1/2) 後，韌體不會保留舊的 Parity 資訊 (VU 4055 回傳空值)，且 HW_RESET 後系統能正常初始化。
2. **UECC Injection & Detection**: 在寫入資料後，透過 `inject_UECC` 對特定 LBA 的 Page 注入不可糾正的 UECC 錯誤，並確認在 Parity 關閉狀態下，直接讀取該 Page 會正確回傳 `ReadStatus.UECC` 狀態碼，證明硬體/韌體能準確偵測到資料損壞。
3. **Data Recovery via Parity**: 確認在 Parity 開啟狀態下 (BIT4/5/6)，即使原始 Page 存在 UECC 錯誤，韌體能利用 Parity 資訊重建資料，使得標準 Read Compare 操作成功通過 (expect_error=False)，證明 Rain 機制能有效修復單點 UECC 錯誤。

## Test Case (TC) Checkpoints
1. [Case01_Parity_Disable_Cleanup_Check]：
   - 動作：針對當前測試模式 (TLC/SLC/WB) 的 LUN，寫入超過 6 pageline 的資料。執行 HW_RESET (無 Power Down)。接著透過 VU D08B 將 BIT0/1/2 (Host Full Block Protection Rain Disable) 設為 0 (Disable)，並透過 VU 4054 確認 Rain Info。隨後執行 VU 4055 讀取 Parity 資訊。
   - 預期結果：VU 4055 回傳的 `get_parity[0:8]` 必須等於 `bytearray(8)` (全零/空值)。這驗證了當 Host 明確關閉 Full Block Protection 時，韌體不會嘗試使用或保留相關的 Parity 數據，確保測試環境乾淨。

2. [Case02_UECC_Injection_Detection_Check]：
   - 動作：重新配置並寫入新的資料區塊 (長度為 `cursor.first_empty_physical_page + 6`)。獲取目標 LBA (0) 的 PCA (Physical Channel Address)。執行 `inject_UECC` 函數，針對該 PCA 對應的 Page 注入 UECC 錯誤 (根據 SLC/TLC 模式調整注入參數)。再次執行 HW_RESET。透過 VU D08B 確保 BIT4/5/6 (Data Recovery) 處於 Disable 狀態 (透過 `host_full_block_protection_rain &= ~data_recovery`)。最後執行 `direct_read_raw_data_and_check_status`，設定 `expect_status=ReadStatus.UECC` 且 `REH_Enable=True`。
   - 預期結果：直接讀取操作必須回傳 `ReadStatus.UECC`。這驗證了當 Parity 恢復機制被禁用時，硬體/韌體能正確識別並報告底層 Flash 的 UECC 錯誤，未進行任何掩飾或錯誤恢復。

3. [Case03_Parity_Recovery_Success_Check]：
   - 動作：保持上述 UECC 注入的狀態不變。透過 VU D08B 將 BIT4/5/6 (Data Recovery) 設為 1 (Enable)，即 `host_full_block_protection_rain |= data_recovery`。透過 VU 4054 確認 Rain Info 更新。最後執行 `read_compare_rain_result`，使用之前寫入的 `write_record` 進行比對，設定 `expect_error=False`。
   - 預期結果：Read Compare 操作必須成功通過 (無錯誤)。這驗證了當 Data Recovery (Parity) 機制啟用時，韌體能夠利用儲存的 Parity 資訊，從具有 UECC 錯誤的 Page 中重建出正確的資料，從而滿足 Host 的讀取請求，證明 Rain 保護機制對 UECC 錯誤的有效修復能力。