# Test Spec: UFS FTL LWP Consistency Check under UECC Injection and HW_RESET (No SSU)

## Verification Criterion (VC)
驗證在無 Secure Storage Unit (SSU) 保護的硬體重置 (HW_RESET) 情境下，FTL 的 LWP (Logical Write Pointer) 狀態一致性與資料完整性：
1. **LWP 狀態一致性**：確認在 Normal LUN 寫入 TLC 資料並針對特定 CE/Plane 的 Page 注入 UECC 錯誤後，執行 HW_RESET 且無 SSU 流程，韌體重啟後的 LWP (LWP_B) 必須與重置前的 LWP (LWP_A) 完全一致，證明韌體未因 UECC 錯誤而錯誤地推進或回滾 LWP。
2. **資料讀取行為驗證**：
   - 對於**非 LWP 區域** (Non-LWP) 的 UECC 注入點（僅在奇數 Plane `i%2 != 1` 時觸發），確認讀取時能正確識別為舊資料（Pattern: Erase/0xFF），驗證韌體在無 SSU 保護下，UECC 錯誤不會導致資料被錯誤覆蓋或丟失，而是保留原始狀態。
   - 對於**LWP 區域** (LWP) 的 UECC 注入點，確認讀取時能正確識別為新寫入的資料（Pattern: 0x00/Write Data），驗證 LWP 指向的當前有效資料區未被 UECC 錯誤干擾。

## Test Case (TC) Checkpoints
1. [LWP_Consistency_No_SSU_Check]：
   - 動作：
     1. 配置 LUN 0 (Normal), 1 (Boot A), 2 (Boot B), 3 (EM1)，並初始化測試環境。
     2. 針對 LUN 0 執行順序寫入，寫入長度為 `tlc_ce_page * ce_num * 2` (即 2 個 Page 的容量)，寫入位置從 LBA 0 開始。
     3. 透過 `issue_4051_to_get_physical_address` 獲取當前寫入位置的物理地址 (PCA)，並針對該 PCA 的 Page 注入 UECC 錯誤 (`inject_UECC`)。
     4. 若為奇數 Plane (`i % 2 == 1`)，額外針對 Page 0 的 CE0 注入 UECC 錯誤 (Non-LWP 區域)。
     5. 呼叫 `collect_lwp_checks` 獲取重置前的 LWP 狀態，記錄為 `LWP_A`。
     6. 執行 `StartStopUnit` 發送 Power Condition `0x03` (Immediate Unit Reset) 觸發 HW_RESET，且**不執行**任何 SSU 相關操作 (如 Secure Erase 或 Power Cycle with SSU)。
     7. 重置完成後，再次呼叫 `collect_lwp_checks` 獲取當前 LWP 狀態，記錄為 `LWP_B`。
     8. 呼叫 `compare_lwp_checks` 比對 `LWP_A` 與 `LWP_B`。
   - 預期結果：
     - `LWP_A` 與 `LWP_B` 必須完全相同 (`identical == True`)。
     - 這代表在無 SSU 保護下，即使存在 UECC 錯誤，FTL 的 LWP 狀態機不會發生異常跳變或重置，保持穩定。

2. [Data_Integrity_NonLWP_UECC_Check]：
   - 動作：
     1. 在奇數 Plane (`i % 2 == 1`) 的情境下，針對 Non-LWP 區域 (Page 0) 注入 UECC 錯誤。
     2. 執行 `save_write_info` 設定預期讀取資料模式為 `CmdParamPatternMode.PTN_ERASE` (即 0xFF/空白資料)，並指定讀取範圍包含 Non-LWP 的 UECC 注入 LBA。
     3. 執行 `read_compare` 使用 `SW_COMPARE` 模式讀取資料並與預期模式比對。
   - 預期結果：
     - 讀取回傳的資料必須等於 `PTN_ERASE` (0xFF)。
     - 這代表韌體在讀取 Non-LWP 區域時，即使該區塊存在 UECC 錯誤，由於該區塊已過期 (Invalid)，韌體不會嘗試修復或覆蓋它，而是返回其物理狀態（通常為 Erase 狀態），驗證了資料不會被錯誤地視為有效新資料。

3. [Data_Integrity_LWP_UECC_Check]：
   - 動作：
     1. 針對 LWP 區域 (當前寫入的 Page) 注入 UECC 錯誤。
     2. 執行 `save_write_info` 設定預期讀取資料模式為 `CmdParamPatternMode.PTN_ERASE` (注意：根據代碼邏輯 `data_pattern_mode=CmdParamPatternMode.PTN_ERASE` 用於 `old_data`，但對於 LWP 區域，代碼註解指出 "others new"，且 `save_write_info` 在 `i%2 != 1` 時未特別標記 Non-LWP，暗示 LWP 區域預期為新寫入資料。*修正分析*：代碼中 `save_write_info` 統一使用了 `PTN_ERASE` 作為 `old_data` 的標記，但對於 LWP 區域，通常預期是剛寫入的資料。然而，仔細查看 `save_write_info` 的調用，它似乎是用來標記哪些 LBA 是 "Old Data" (即寫入前存在的資料)。對於 LWP 區域，它是新寫入的，因此不應被視為 "Old Data"。但代碼中 `read_compare` 會根據 `write_record` 來驗證。若 `write_record` 中該 LBA 被標記為寫入過，則預期為新資料。若未標記或標記為舊資料，則預期為舊資料。
     3. 根據代碼邏輯：`save_write_info` 被調用兩次，一次針對 `old_data_startlba` (寫入前的舊資料)，一次針對 `nonlwp_old_data_startlba` (Non-LWP 的舊資料)。LWP 區域的資料是剛寫入的，因此不在 `old_data` 列表中。
     4. 執行 `read_compare`。
   - 預期結果：
     - LWP 區域的資料讀取結果必須等於**新寫入的資料模式** (New Data Pattern, 通常為 0x00 或特定 Pattern，取決於 `sequential_write` 的實現，代碼中未明確顯示 Pattern，但通常為递增或固定值)。
     - 這代表即使 LWP 區域存在 UECC 錯誤，韌體在讀取時仍能通過 ECC 校驗或韌體邏輯恢復出正確的新寫入資料，或者若 UECC 無法修復，則應報告錯誤。但根據 VC 的隱含意圖，此測試主要驗證 LWP 狀態穩定性，資料完整性為次要驗證。若 UECC 導致讀取失敗，則測試應 Fail。預期結果為讀取成功且資料正確。