# Test Spec: UFS REH (Read Error Handling) & Sticky Read Integration Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Read Error Handling (REH) 模組與 Sticky Read 功能的協同運作機制：
1. **REH 錯誤注入與掩碼邏輯驗證**：透過 Vendor Command `D014` 精確控制 REH 的 Big/Small Step 掩碼（Masking），確認當特定 Step 被 Mask 時，`4014` VUC 回報的 ECC Error Bits 應為 0；當 Step 未被 Mask 時，回報值應介於 0x0001 至 0x3FFE 之間（非零且非溢出），驗證 REH 錯誤計數器的獨立性與準確性。
2. **Sticky Read 狀態強制覆蓋驗證**：透過 `4066` VUC 強制將特定 Die/Page Type 的 Read Last Table 狀態設為 Sticky Read，確認該狀態能正確影響後續的 Raw Data 讀取路徑，並確保在 REH 觸發錯誤恢復後，Sticky Read 的 Offset 與狀態標誌能正確反映在硬體行為中。
3. **LBA/PBA 映射一致性驗證**：在 REH 觸發錯誤恢復（Recovery）後，透過 `4052` VUC 將物理地址轉回邏輯地址，驗證恢復後的 LBA 是否仍指向原始寫入的 LUN 與 LBA 範圍，確保錯誤恢復未導致邏輯映射錯亂。

## Test Case (TC) Checkpoints

1. [LUN_Configuration_and_Initial_Write]：
   - 動作：
     1. 透過 `push_write_config` 配置 LUN 0 為 Normal Memory Type，LUN 1 為 Enhanced 1 (EM1) Memory Type，並分配對應的 Allocation Units。
     2. 執行 `issue_C088` 停止 Refresh 執行但允許入隊。
     3. 對 LUN 0 寫入 TLC VB Size 的資料，對 LUN 1 寫入 SLC VB Size 的資料。
     4. 透過 `set_read_last_table` 初始化 Read Last Reference Table。
     5. 透過 `issue_4066` 啟用 Sticky Read 功能。
     6. 透過 `issue_D014` Option 7 分配 Codeword Buffer 以儲存 REH 資訊。
   - 預期結果：LUN 配置成功；寫入完成且無錯誤；Sticky Read 狀態為 ENABLE；REH Buffer 分配成功。

2. [REH_Step_Masking_and_ECC_Verification]：
   - 動作：
     1. 隨機選擇一個 LBA，透過 `issue_4051` 獲取其物理地址 (PBA: Die, Plane, Block, Page)。
     2. 針對該 Die 與 Page Type，透過 `issue_4066` 強制設定 Sticky Read 狀態。
     3. 遍歷所有 REH Steps (Big/Small)，針對每個 Step 組合執行以下子步驟：
        a. 計算掩碼：若 Big Step <= 2，Mask 對應 Small Step；若 Big Step > 2，Mask 對應 Big Step。
        b. 執行 `issue_D014` Option 1 設定 `bigStepBitMap` 與 `smallStepBitMap` 以啟用/禁用特定 REH Step。
        c. 執行 `issue_D014` Option 0 觸發 REH Recovery 於指定 Step。
        d. 執行 `issue_4052` 將 PBA 轉回 LBA，驗證返回的 LUN 與 LBA 是否在預期範圍內。
        e. 執行 Host Read 4KB 從該 LBA。
        f. 執行 `issue_40F9` 獲取 Recovery Number 與 Error Bits。
        g. 執行 `issue_4014` Option 2 獲取所有 Plane 的 ECC 結果 Payload。
        h. 解析 Payload 中對應 Step 的 Error Number。
   - 預期結果：
     - **Masked Step**：若當前 Step 被 Mask（即 `cb/cs` 匹配當前測試的 `b/s`），`issue_4014` 返回的所有 Plane Error Number 必須全為 `0`。
     - **Unmasked Step**：若當前 Step 未被 Mask，`issue_4014` 返回的所有 Plane Error Number 必須滿足 `0 < Value < 0x3FFF`。
     - **LBA Consistency**：`issue_4052` 返回的 LBA 必須與原始寫入的 LBA 一致，且 LUN 正確。

3. [Sticky_Read_Integration_Check]：
   - 動作：
     1. 在 REH 測試循環中，針對每個 Die 與 Page Type，呼叫 `issue_4066_force_current_read_last_as_sticky_read` 強制覆蓋 Read Last Table。
     2. 驗證 `issue_4066` 返回的狀態為 `STICKY_READ_STATUS.SUCCESS`。
     3. 在 REH 恢復過程中，確認 Sticky Read 機制未干擾 REH 的錯誤計數與恢復流程。
   - 預期結果：Sticky Read 狀態設置成功；在 REH 恢復期間，Sticky Read 的 Offset 與狀態標誌保持穩定，未因 REH 觸發而產生非預期的狀態跳變或錯誤。

4. [Resource_Release_and_Cleanup]：
   - 動作：
     1. 執行 `issue_D014` Option 7 釋放 Codeword Buffer。
   - 預期結果：Buffer 釋放成功，無記憶體洩漏或硬體狀態殘留。