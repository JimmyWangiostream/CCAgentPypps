# Test Spec: UFS Protocol Command Sequence & Data Integrity Verification

## Verification Criterion (VC)
驗證 UFS 主機控制器與裝置間的協議交互完整性及資料一致性：
1. **協議層初始化與狀態檢查**：確認 `CmdSeqInitialFlow` 能正確設定鏈路啟動延遲與佇列空閒等待；確認 `CmdSeqTestUnitReady` 與標準 `TestUnitReady` 命令能正確返回 LUN 狀態、超時設定及響應時間，確保裝置進入 Unit Ready 狀態。
2. **鏈路速率切換機制**：驗證 `CmdSeqSpeedChange` 命令能正確觸發並返回 TX/RX 的 Gear、Lane、Mode 設定及保護/重試超時參數，確認鏈路參數協商結果。
3. **資料寫入與讀取一致性 (Manual Mode)**：在 Manual Mode 下，驗證 Write10 寫入特定 Pattern (0xDEAD/0xBEEF) 至 LUN 0，並通過 Read10 讀回，確認 payload 資料與寫入內容完全匹配。
4. **UNMAP 後資料行為驗證**：驗證在寫入兩筆 4KB 資料 (LBA 0 與 LBA 1) 後，對 LBA 0 執行 Unmap 操作，隨後讀取 LBA 0 開始的 8KB 範圍。預期結果為前 8KB 資料應為零 (Zero-filled)，後 8KB 資料應保留為第二筆寫入的 Pattern (0xBEEF)，驗證 UNMAP 邏輯與資料保留機制。
5. **非法 LBA 錯誤處理**：驗證當寫入/讀取超出有效 LBA 範圍 (0xFFFFFFFE) 時，系統應拋出 `PATTERN_ASSERT_BUFFER_MANAGER_FAIL_CYCLE_INDICATOR_NOT_FOUND` 異常，確認邊界檢查機制生效。
6. **配置描述符讀取**：驗證 `ReadDescriptor` 能正確讀取 CONFIGURATION 描述符，並解析 Header 與 Unit 欄位，確認裝置能力 (如 HPB, Write Booster, RPMB) 與 LUN 配置正確。

## Test Case (TC) Checkpoints

1. **[InitFlow_Response_Check]**：
   - 動作：建立 `CmdSeqInitialFlow` 命令，設定 `wait_queue_empty=True` 與 `delay_time=0`，發送並讀取回應。解析回應物件 `CmdSeqInitialFlowResponse`。
   - 預期結果：回應中 `l32_delay_time` 應為 0；`w36_wait_queue_empty` 應為 True；`l40_link_startup_time` 應為有效數值。確認初始化流程參數正確傳遞至硬體層。

2. **[TUR_CmdSeq_Response_Check]**：
   - 動作：建立 `CmdSeqTestUnitReady` 命令，指定 LUN 為 `api.WellKnownLUN.UFS_DEVICE`，設定 `timeout=100000` us，發送並讀取回應。
   - 預期結果：回應中 `b2_lun` 應為 UFS Device LUN ID；`l3_timeout` 應為 100000；`l40_test_unit_ready_time` 應為實際執行耗時。確認裝置處於 Unit Ready 狀態。

3. **[SpeedChange_Parameters_Check]**：
   - 動作：建立 `CmdSeqSpeedChange` 命令，發送並讀取回應 `CmdSeqSpeedChangeResponse`。
   - 預期結果：回應中 `b3_rx_mode`, `b3_rx_lane`, `b3_rx_gear` 及 `b4_tx_mode`, `b4_tx_lane`, `b4_tx_gear` 應反映當前或目標鏈路狀態；`w5_fc0_protection_timeout` 與 `w7_tc0_replay_timeout` 等超時參數應為非零有效值，確認鏈路切換參數協商成功。

4. **[Write10_Read10_Data_Integrity_Check]**：
   - 動作：
     1. 初始化測試器至 Unit Ready。
     2. 建立 Write10 命令，LUN=0, LBA=0, Length=3 (12KB)，設定 `fua=1` (Force Unit Access)，`manual_mode=True`。寫入資料為 `bytearray([0xBE, 0xEF]) * 2048` (即 4KB 的 0xBEEF pattern) 重複 3 次。
     3. 建立 Read10 命令，LUN=0, LBA=0, Length=3，`manual_mode=True`。
     4. 發送命令並讀取回應。
   - 預期結果：Read10 回應的 `resp.data` 前 12288 bytes (12KB) 必須嚴格等於寫入的 `w_data * 3`。確認資料寫入與讀取路徑無損壞，且 FUA 確保資料落盤。

5. **[UNMAP_Data_Zeroing_Check]**：
   - 動作：
     1. 初始化測試器至 Unit Ready。
     2. 寫入 Data A (0xDEAD pattern, 4KB) 至 LBA 0 (Length=3, 12KB)。
     3. 寫入 Data B (0xBEEF pattern, 4KB) 至 LBA 1 (Length=3, 12KB)。
     4. 執行 Unmap 命令，LUN=0, LBA=0, Length=2 (Unmap 前 8KB，即 LBA 0 和 LBA 1 的前兩段)。
     5. 執行 Read10 命令，LUN=0, LBA=0, Length=4 (讀取 16KB)。
     6. 檢查讀取回應的 `resp.data`。
   - 預期結果：
     - `resp.data[0:4096]` (LBA 0 第一段) 必須等於 `bytearray(4096)` (全零)。
     - `resp.data[4096:8192]` (LBA 0 第二段) 必須等於 `bytearray(4096)` (全零)。
     - `resp.data[8192:12288]` (LBA 1 第一段) 必須等於 `data_b` (0xBEEF pattern)。
     - `resp.data[12288:16384]` (LBA 1 第二段) 必須等於 `data_b` (0xBEEF pattern)。
     確認 Unmap 操作正確將指定 LBA 範圍標記為無效，且讀取時返回零值，而未受影響的 LBA 保留原始資料。

6. **[Illegal_LBA_Error_Handling_Check]**：
   - 動作：
     1. 初始化測試器至 Unit Ready。
     2. 建立 Write10 與 Read10 命令，LUN=0, LBA=0xFFFFFFFE (超出有效範圍), Length=3。
     3. 發送命令並嘗試讀取回應。
   - 預期結果：程式碼必須拋出 `PATTERN_ASSERT_BUFFER_MANAGER_FAIL_CYCLE_INDICATOR_NOT_FOUND` 異常。確認主機端或韌體層對非法 LBA 地址進行了嚴格檢查並拒絕執行。

7. **[ConfigDescriptor_Parsing_Check]**：
   - 動作：
     1. 初始化測試器至 Unit Ready。
     2. 對 `DescriptorIDN.CONFIGURATION` 執行 4 次 `ReadDescriptor`，Index 從 0 到 3，Selector=0。
     3. 解析回應中的 `u12_specific_fields` 為 `SfReadDescriptor`。
     4. 解析回應 `data` 為 `ConfigDescriptor410`，並遍歷 `units`。
   - 預期結果：
     - `SfReadDescriptor` 的 `b13_idn` 應為 CONFIGURATION IDN。
     - `ConfigDescriptorHeader` 的 `b3_boot_enable`, `b6_high_priority_lun`, `b11_hpb_control` 等欄位應反映裝置實際配置。
     - 每個 `ConfigDescriptorUnit` 的 `b0_lu_enable` 應為 1 (若 LUN 啟用)，`b3_memory_type` 應為有效值，`l4_num_alloc_units` 應大於 0。確認配置描述符解析邏輯正確，無記憶體越界或解析錯誤。