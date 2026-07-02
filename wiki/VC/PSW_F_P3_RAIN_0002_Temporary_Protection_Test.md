# Test Spec: UFS Rain UECC Recovery & Event Logging Verification

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇硬體層級 UECC (Uncorrectable ECC) 錯誤時，Rain (Reliability, Availability, and Integrity) 機制的完整處理鏈路：
1. **多模式寫入與注入**：確認在 TLC、Write Booster (WB) 及 SLC (EM1) 三種不同儲存模式下的 L2 區塊，經 HW_RESET 後能成功注入真實 UECC 錯誤。
2. **事件日誌記錄準確性 (0x6001)**：確認韌體在 SPOR (System Power On Reset) 後，能精確記錄 UECC 發生時的物理位置 (Die, Plane, Block, Page)、模式 (SLC/TLC) 及錯誤類型 (Real UECC)，並驗證 `block_N` 欄位中僅失敗 Plane 對應的 Block 號碼有效，其餘必須為 0。
3. **恢復事件日誌記錄準確性 (0x3011)**：確認韌體觸發 Refresh 機制後，記錄恢復過程的詳細參數，包括錯誤類型 (Read UECC)、恢復結果 (Decode OK)、VB 狀態 (Open L2 FBP)、Parity 位置 (Swap) 及邏輯 Page 映射，並驗證 `errblock_N` 欄位中僅失敗 Plane 對應的 Block 號碼有效，其餘必須為 0xFFFF。
4. **BBT 退休機制**：確認發生 Read Scan UECC 的 Virtual Block (VB) 已被正確標記為 Retirement，並記錄原因為 `READ_SCAN_UECC`。

## Test Case (TC) Checkpoints

1. [Step1_TLC_UECC_Injection]：
   - 動作：針對 `TestNormalLun` 以 `TEST_TLC` 模式寫入超過 6 個 Pageline 的資料，觸發 Flush Swap 條件並執行 HW_RESET。隨後繼續寫入 32MB 資料至同步點。計算目標 LBA (`last_lba // 2`)，透過 `get_PCA_and_print` 獲取該 LBA 對應的物理地址資訊 (PCA)，並將其標記為 SLC=False (TLC 模式) 加入 `UECC_pca` 列表。
   - 預期結果：成功獲取 TLC 模式下的物理地址 (Die, Block, Plane, Page)，且該地址對應的 Virtual Block (VB) 處於正常可寫狀態。

2. [Step2_WB_UECC_Injection]：
   - 動作：針對 `TestWBLun` 以 `TEST_WB` 模式寫入超過 6 個 Pageline 的資料，觸發 Flush Swap 條件並執行 HW_RESET。啟用 `WRITEBOOSTER_EN` Flag 後，繼續寫入 32MB 資料至同步點。計算目標 LBA (`last_lba // 2`)，獲取 PCA 並標記為 SLC=True (WB 模式通常對應 SLC 緩衝區或特定配置) 加入 `UECC_pca` 列表。
   - 預期結果：成功獲取 Write Booster 模式下的物理地址，且該地址對應的 VB 處於正常狀態。

3. [Step3_SLC_UECC_Injection]：
   - 動作：針對 `TestEM1Lun` 以 `TEST_SLC` 模式寫入超過 6 個 Pageline 的資料，觸發 Flush Swap 條件並執行 HW_RESET。隨後繼續寫入 32MB 資料至同步點。計算目標 LBA (`last_lba // 2`)，獲取 PCA 並標記為 SLC=True (SLC 模式) 加入 `UECC_pca` 列表。
   - 預期結果：成功獲取 SLC 模式下的物理地址，且該地址對應的 VB 處於正常狀態。

4. [Step4_UECC_Inject_and_Verify]：
   - 動作：遍歷 `UECC_pca` 列表中的三個地址 (TLC, WB, SLC)，對每個地址執行 `inject_UECC` 注入真實 UECC 錯誤。隨後透過 `direct_read_raw_data_and_check_status` 讀取該物理頁面的 Payload，並驗證讀取狀態必須為 `ReadStatus.UECC`。
   - 預期結果：所有三個注入點的讀取狀態均返回 `UECC`，確認錯誤已成功注入且未被硬體自動修正，為後續韌體恢復測試建立基準。

5. [Step5_SPOR_Trigger]：
   - 動作：執行 `api.init_tester_to_unit_ready` 並指定 `Dcmd5ResetType.HW_RESET` 且 `powerdown=False`，模擬系統硬體重啟。
   - 預期結果：UFS 設備執行硬體重置，韌體重新初始化並開始掃描儲存介質。

6. [Step6_Data_Compare]：
   - 動作：清除事件日誌，發送 VU 命令 `C088` 參數為 `StopRefreshRefreshCanStillBeEnqueue` 以控制 Refresh 行為，隨後執行 `read_compare_rain_result` 進行資料比對。
   - 預期結果：韌體檢測到 UECC 並觸發恢復機制，資料比對結果應反映恢復過程中的狀態（具體恢復結果由後續日誌驗證）。

7. [Step7_Refresh_Booking_Q_Check]：
   - 動作：發送 VU 命令 `40C5`，並傳入三個注入 UECC 的 VB 號碼列表 (`VB_list`)，檢查 Refresh Booking Queue。
   - 預期結果：韌體已將這三個包含 UECC 的 VB 加入 Refresh 排隊佇列，準備進行資料重建或搬移。

8. [Step8_EventLog_0x6001_Verification]：
   - 動作：
     1. 建構預期列表 `self.expected`，包含每個注入點的 LUN, LBA, VB, Die, Block, Plane, Page, Logical Page, SLC 標誌。
     2. 查詢事件日誌 ID `0x6001` (BeUeccEvent)。
     3. 對每個預期項目，在日誌中尋找匹配的 Block 和 Logical Page。
     4. 驗證匹配項目的欄位：
        - `block_N`：僅在 `exp["plane"]` 索引處的 Block 號碼等於 `exp["block"]`，其餘 `block_N` (N != plane) 必須為 0。
        - `die`：必須等於 `exp["die"]`。
        - `startPlane`：必須等於 `exp["plane"]`。
        - `flags_bits.slcMode`：必須等於 `exp["slc_en"]` (TLC=0, SLC/WB=1)。
        - `flags_bits.ueccType`：必須等於 2 (代表 Real UECC)。
     5. 若參數不匹配或日誌中找不到所有預期項目，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
   - 預期結果：韌體精確記錄了 UECC 發生時的物理環境，包括正確的 Die、Plane、Block 號碼，並正確區分 SLC/TLC 模式及錯誤類型為真實 UECC。

9. [Step9_EventLog_0x3011_Verification]：
   - 動作：
     1. 建構預期列表 `self.expected`。
     2. 查詢事件日誌 ID `0x3011` (RainRecoveryEventLog)。
     3. 對每個預期項目，在日誌中尋找匹配的 Block 和 Page。
     4. 驗證匹配項目的欄位：
        - `errblock_N`：僅在 `exp["plane"]` 索引處的 Block 號碼等於 `exp["block"]`，其餘 `errblock_N` (N != plane) 必須為 0xFFFF。
        - `die`：必須等於 `exp["die"]`。
        - `errType`：必須等於 0 (代表 Read UECC)。
        - `logVB` 和 `pvb`：必須等於 0xFFFF。
        - `pageInfo`：其值必須等於 `exp["logical_page"] << 2` (高 10 位為 Logical Page，低 2 位為 LMU=0)。
        - `recovResult`：必須等於 0 (代表 Decode OK)。
        - `openVbFlag`：必須等於 1 (代表 Open L2 FBP)。
        - `vbType`：必須等於 `exp["slc_en"]`。
        - `parityPosition`：必須等於 2 (代表 Swap)。
        - `abnormalUECCPhy`：必須等於 0。
     5. 若參數不匹配或日誌中找不到所有預期項目，拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
   - 預期結果：韌體精確記錄了恢復過程，確認錯誤類型為 Read UECC，恢復結果為 Decode OK，且正確標記了 VB 狀態為 Open L2 FBP 及 Parity 位置為 Swap。

10. [Step10_BBT_Retirement_Check]：
    - 動作：發送 VU 命令 `40E5`，並傳入三個注入 UECC 的 VB 號碼列表，檢查 BBT (Bad Block Table) 的退休狀態。
    - 預期結果：這三個 VB 在 BBT 中已被標記為 Retirement，且退休原因 (`reason`) 必須為 `READ_SCAN_UECC`，確認韌體在檢測到無法修復的 UECC 後正確執行了區塊退休機制。