# Test Spec: UFS Media Scan Sequence Verification via C085/C08B Vendor Commands

## Verification Criterion (VC)
驗證 UFS 韌體在啟用 Media Scan 功能後，其內部掃描狀態機（State Machine）是否嚴格遵循預定義的 `media_scan_vb_group_scan_map` 順序執行。
1. **機制觸發驗證**：確認透過 Vendor Command `C08B` 啟用 Media Scan，並透過 `C085` 設定 `last_scan_spend_time` 為極大值 `0x1000000`，能夠強制觸發韌體進入下一組掃描群組（Next Scan Group）的流程。
2. **順序邏輯驗證**：透過輪詢 Vendor Command `40CF` 讀取 `cur_scan_vb` 與 `scan_group` 狀態，驗證韌體掃描的 Virtual Block (VB) 所屬的 Group ID 必須嚴格遞增（或按固定順序遍歷），不得跳躍或重複。
3. **環境準備驗證**：確認 LUN 0 (Normal MLC) 與 LUN 1 (Enhanced 1 SLC) 的 LBA 配置與寫入操作正確映射至對應的 Flash 層級，確保掃描對象存在有效資料。

## Test Case (TC) Checkpoints

1. **[TC01_LUN_Config_and_Data_Warmup]**：
   - 動作：
     1. 透過 `WriteDescriptor` (DescriptorIDN: CONFIGURATION) 配置 LUN 0 為 `MemoryType.NORMAL` (L88 MLC)，分配 `normal_total_AU` 個 Allocation Units；配置 LUN 1 為 `MemoryType.ENHANCED_1` (L84 SLC)，分配 `EM1_total_AU` 個 Allocation Units。
     2. 對 LUN 0 執行 Sequential Write，寫入大小為 `10 * tlc_vb_size` 的資料（其中 `tlc_vb_size` 由 `l88_vb_size_u1` 計算得出）。
     3. 對 LUN 1 執行 Sequential Write，寫入大小為 `10 * slc_vb_size` 的資料（其中 `slc_vb_size` 由 `l84_vb_size_u0` 計算得出）。
     4. 呼叫 `api.lba_to_pba` 獲取 LUN 0 和 LUN 1 起始 LBA 對應的 PBA，確認寫入路徑正確。
   - 預期結果：
     - LUN 0 與 LUN 1 均成功啟用且未設定寫保護 (`LUNWriteProtect.NOT_WRITE_PROTECTED`)。
     - LUN 0 的資料寫入至 MLC 層級，LUN 1 的資料寫入至 SLC 層級。
     - 韌體內部 VB 結構中，對應的 VB Group 標記應反映上述寫入操作產生的狀態（如 Dirty Bit 或 Group 歸屬）。

2. **[TC02_Media_Scan_Enable_and_Trigger]**：
   - 動作：
     1. 發送 Vendor Command `C08B`，參數設定 `enable_media_scan=True`，啟動韌體 Media Scan 機制。
     2. 初始化 `micron_vu_C085_param_with_data`，將 `last_scan_spend_time` 欄位設定為 `0x1000000`。
     3. 發送 Vendor Command `C085` 寫入上述參數。
   - 預期結果：
     - `C08B` 回應成功，韌體 Media Scan 狀態機被激活。
     - `C085` 寫入成功，韌體讀取到極大的 `last_scan_spend_time` 值，此值作為觸發條件，強制韌體跳過當前可能存在的延遲或緩衝狀態，直接進入下一個預定的掃描 VB Group 序列。

3. **[TC03_Scan_Sequence_Validation]**：
   - 動作：
     1. 進入輪詢迴圈，持續發送 Vendor Command `40CF` 讀取 Media Scan 參數。
     2. 解析回應 Payload 中的 `cur_scan_vb` (當前掃描 VB ID) 與 `scan_group` (當前掃描群組 ID)。
     3. 當 `cur_scan_vb == 0xFFFFFFFF` 且 `scan_page == 0xFFFFFFFF` 時，判定掃描流程結束，跳出迴圈。
     4. 在迴圈運行期間，收集所有出現過的 `scan_group` ID，存入 `scan_vb_group_idx` 列表。
     5. 將收集到的 `scan_vb_group_idx` 與程式碼中硬編碼的 `media_scan_vb_group_scan_map` 進行比對。
   - 預期結果：
     - 輪詢最終會因狀態碼 `0xFFFFFFFF` 而正常終止，代表韌體完成了所有配置的 VB Group 掃描。
     - `scan_vb_group_idx` 中的 Group ID 序列必須嚴格符合 `media_scan_vb_group_scan_map` 的定義順序。
     - 具體檢查點：若當前掃描 Group ID 為 `G_curr`，前一個掃描 Group ID 為 `G_prev`，則必須滿足 `index(G_curr) >= index(G_prev)`。若發現 `index(G_curr) < index(G_prev)`，則判定為測試失敗 (`SIGHTING_FAIL_DATA_COMPARE_FAIL`)，證明韌體掃描順序邏輯錯誤或狀態機跳躍異常。
     - 驗證涵蓋的 Group 類型包括：`CURRENT_L2_MLC`, `CURRENT_DATA_GC_BLK_MLC`, `INCOMPLETE_BLK_MLC`, `CURRENT_L1`, `CURRENT_L2_SLC`, `CURRENT_DATA_GC_BLK_SLC`, `INCOMPLETE_BLK_SLC`, `CURRENT_PTE`, `LOG_TAB_BLK`, `RAIN_SWAP_*`, `PTE_POOL`, `USED_BLK_POOL_*` 等所有定義在 Map 中的群組。