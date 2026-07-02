# Test Spec: UFS PTE/EM1 LWP UECC Injection under Diverse Power Cycle Scenarios

## Verification Criterion (VC)
驗證 UFS 韌體在不同電源循環（Power Cycle）策略下，對已注入 UECC 錯誤之 LWP（Logical Write Page）的恢復機制與資料完整性：
1. **Case 01 (No Action)**：確認在無任何電源管理指令介入下，UECC 錯誤標記殘留於 LWP，且後續讀取驗證會因 ECC 校驗失敗而回報錯誤（Data Corruption）。
2. **Case 02 (DeepSleep + SPOR)**：確認透過 StartStopUnit (SSU) 指令將 LUN 進入 Deep Sleep (Power Condition 0x04) 並執行 HW_RESET (Soft Power Off, powerdown=False) 後，韌體是否觸發 LWP 重建或錯誤標記清除機制，預期結果應為資料修復或標記清除。
3. **Case 03 (Full POR)**：確認透過 HW_RESET (Hard Power Off, powerdown=True) 進行完整掉電重啟後，韌體是否透過 Flash Translation Layer (FTL) 的元數據重建或 Bad Block Management 機制修復 UECC 錯誤。
4. **Case 04 (Switch Partition + SPOR)**：確認在 EM1 LUN 寫入 SLC 資料以觸發 Partition Switch 情境後，再執行 Deep Sleep + SPOR，驗證此特定硬體狀態切換是否影響 Normal LUN 中 UECC 錯誤的恢復行為。

## Test Case (TC) Checkpoints
1. [Case01_NoAction_UECC_Persistence_Check]：
   - 動作：針對 `TestNormalLun` 寫入 3 頁 TLC 資料，取得最後 LBA (`last_lba`)。透過 `inject_UECC_in_random_written_pca` 隨機選取一個已寫入 LBA 對應的 PCA (Physical Cluster Address)，並呼叫 `inject_UECC` 注入 UECC 錯誤（SLC 模式關閉）。接著執行 `TEST_ITEM.NOTHING` 分支，即不發送任何 SSU 或 Reset 指令，直接進入 `read_compare_rain_result` 進行讀取比對。
   - 預期結果：讀取比對結果應顯示資料錯誤（Mismatch 或 ECC Error），因為韌體未執行任何電源循環觸發的恢復流程，注入的 UECC 錯誤導致該 LWP 資料無法正確解碼，驗證無保護下的資料損壞狀態。

2. [Case02_DeepSleep_SPOR_Recovery_Check]：
   - 動作：重置 LUN 配置並重新寫入 3 頁 TLC 資料至 `TestNormalLun`，注入 UECC 錯誤。接著執行 `TEST_ITEM.DEEPSLEEP` 分支：發送 StartStopUnit (SSU) 指令，設定 `lun=UFS_DEVICE`，`power_condition=0x04` (Deep Sleep)，`start=0` (Stop)，並設定 `wait_queue_empty=True` 確保隊列清空。隨後呼叫 `api.init_tester_to_unit_ready` 執行 `HW_RESET` 且 `powerdown=False` (Soft Power Off / SPOR)。最後執行讀取比對。
   - 預期結果：讀取比對應成功（Data Match 或 ECC Corrected），代表韌體在 SPOR 過程中檢測到 LWP 的 UECC 標記，並透過 LWP Reconstruction 或 FTL 元數據重載機制修復了錯誤，或將該 LWP 標記為可修復狀態，確保資料完整性恢復。

3. [Case03_FullPOR_Recovery_Check]：
   - 動作：重置 LUN 配置並重新寫入 3 頁 TLC 資料至 `TestNormalLun`，注入 UECC 錯誤。接著執行 `TEST_ITEM.POR` 分支：直接呼叫 `api.init_tester_to_unit_ready` 執行 `HW_RESET` 且 `powerdown=True` (Hard Power Off / Full POR)。最後執行讀取比對。
   - 預期結果：讀取比對應成功，代表韌體在完整掉電重啟後，透過 Flash Controller 的初始化流程（如 L2P Table 重建、Bad Block Scan 或 PTE 修復機制）自動修復了注入的 UECC 錯誤，驗證硬體級別的錯誤恢復能力。

4. [Case04_SwitchPartition_SPOR_Cross_LUN_Check]：
   - 動作：重置 LUN 配置，在 `TestNormalLun` 寫入 3 頁 TLC 資料並注入 UECC 錯誤。接著執行 `TEST_ITEM.SWITCH_PARTITION` 分支：先在 `TestEM1Lun` 寫入 4KB 資料（觸發 SLC 模式以切換 Partition 狀態），然後對 `TestNormalLun` 執行 Deep Sleep + SPOR (同 Case 02 的 SSU + HW_RESET powerdown=False)。最後執行讀取比對。
   - 預期結果：讀取比對應成功，驗證即使在觸發 Partition Switch 的硬體狀態變更情境下，Normal LUN 中的 UECC 錯誤仍能透過 SPOR 流程被正確修復，排除 Partition 切換邏輯對 LWP 恢復機制的干擾。