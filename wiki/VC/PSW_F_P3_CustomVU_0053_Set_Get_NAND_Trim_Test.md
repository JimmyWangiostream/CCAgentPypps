# Test Spec: UFS NAND Trim Register Read/Write/Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體透過 Vendor Command (0x4A84/0xC084) 對 NAND Trim 暫存器進行讀寫與恢復的硬體一致性與資料完整性：Case 01 確認預設 Trim 值（0x4A2=0x3, 0x4A3=0x1, 0x4A4=0x4, 0x4A5=0x1, 0x6FF=0x0）與硬體實際狀態相符；Case 02 確認透過 Vendor Command 寫入特定測試值（0x4A3=10, 0x4A4=20, 0x4A5=30）後，硬體暫存器狀態能即時反映該變更；Case 03 確認寫入後的讀回值與預期設定值完全一致，無資料損毀或延遲；Case 04 確認透過恢復預設備份值，硬體狀態能成功回退至初始狀態，驗證韌體對 NAND Trim 參數的完整控制權。

## Test Case (TC) Checkpoints
1. [Case01_Default_Trime_Read_Check]：
   - 動作：透過 `issue_4084_to_get_NAND_trim` API 針對地址 0x4A2, 0x4A3, 0x4A4, 0x4A5, 0x6FF 執行讀取操作，獲取硬體目前的 Trim 值。將讀回值與預定義的 `default_value` 字典進行比對（預期：0x4A2=0x3, 0x4A3=0x1, 0x4A4=0x4, 0x4A5=0x1, 0x6FF=0x0）。若地址位於 `set_dict` 中，則將當前讀回值存入 `backup` 字典以備後續恢復。
   - 預期結果：所有指定地址的讀回值必須嚴格等於預設值。若任何地址讀回值不符，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。此步驟確保測試環境處於已知的硬體初始狀態，排除先前測試殘留的 Trim 設定干擾。

2. [Case02_Custom_Trime_Write_Check]：
   - 動作：透過 `issue_C084_to_set_NAND_trim` API 發送 Vendor Command，將 `set_dict` 中的值寫入硬體 NAND Trim 暫存器（預期寫入：0x4A3=10, 0x4A4=20, 0x4A5=30）。寫入完成後，立即再次呼叫 `issue_4084_to_get_NAND_trim` 讀取這些地址的當前狀態。
   - 預期結果：Vendor Command 執行無錯誤返回。硬體內部暫存器應已更新為新值，為下一步的讀回驗證做準備。此步驟驗證韌體發送寫入指令的機制及硬體接收指令的響應能力。

3. [Case03_Written_Value_Verification_Check]：
   - 動作：遍歷 `set_dict` 中的每個地址與對應值，將步驟 2 中讀回的 `TrimValue` 與 `set_dict` 中的預期值進行逐位元比對。
   - 預期結果：對於地址 0x4A3, 0x4A4, 0x4A5，讀回值必須分別等於 10, 20, 30。若讀回值與設定值不一致，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。此步驟確認 NAND Trim 參數的寫入操作已正確反映在硬體狀態機中，無資料傳輸錯誤或暫存器映射錯誤。

4. [Case04_Trime_Recovery_Check]：
   - 動作：透過 `issue_C084_to_set_NAND_trim` API 發送 Vendor Command，將 `backup` 字典中儲存的原始預設值寫回硬體（即恢復 0x4A3=0x1, 0x4A4=0x4, 0x4A5=0x1 等狀態）。
   - 預期結果：Vendor Command 執行無錯誤。硬體 NAND Trim 暫存器狀態應成功恢復至 Case 01 驗證過的初始預設值。此步驟驗證韌體具備完整的參數恢復機制，確保測試結束後硬體狀態不會因測試注入而永久改變，維持系統穩定性。