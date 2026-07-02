# Test Spec: BFEA (Block Failure Early Analysis) Bin Assignment & Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 BFEA (Block Failure Early Analysis) 機制在特定電源狀態轉換下的行為一致性：
1. **Case 01 (SSU Power Down)**：確認在將目標 VB 強制設定為高錯誤率 Bin (Bin 15) 後，執行 **SSU Power Down (Power Condition 3)** 並等待 60 秒，韌體應維持該 Bin 設定不變，驗證掉電不觸發自動修復或 Bin 重置。
2. **Case 02 (SSU Sleep)**：確認在相同高錯誤率 Bin 設定下，執行 **SSU Sleep (Power Condition 0x02)** 並等待 60 秒，韌體應維持該 Bin 設定不變，驗證睡眠狀態不觸發自動修復。
3. **核心邏輯驗證**：透過 Vendor Command `0x40B0` (BFEA Scan) 的參數 2 (Set Bin) 與參數 3 (Get Bin) 進行寫入與讀回比對，確保 Host 端設定的 Bin Index (15) 能正確持久化至 FTL 層，且不受上述電源管理狀態影響。

## Test Case (TC) Checkpoints

1. [Case01_SSU_PowerDown_BinPersistence_Check]：
   - 動作：
     1. 執行 `flow1_4` 讀取 MConfig 獲取 LONG_SLEEP 參數。
     2. 執行 `random_config` 配置 LUN，並隨機選定一個 Normal LUN (`random_en_lun`)。
     3. 執行 `flow5`：對該 LUN 執行 Unmap 清空資料，設定 `FlagIDN.PURGE_EN` 並輪詢 `AttributeIDN.PURGE_STATUS` 直到狀態為 `0x03` (Complete)，最後透過 Vendor Command `0xD088` 禁用 Auto Standby。
     4. 執行 `flow6` 禁用 BFEA Scan。
     5. 執行 `flow7`：向該 LUN 寫入 3 個 TLC VB 大小的資料 (`3 * tlc_vb_size`)。
     6. 執行 `flow8`：透過 `lba_to_pba` 將 LBA 0 轉換為 PBA，取得對應的 CE (`test_ce`) 與 VB (`test_vb`) 編號。
     7. 執行 `flow10`：透過 Vendor Command `0x40B0` (參數 2: Set Bin) 將該 `test_vb` 的 Bin 值強制設定為 **15** (最高錯誤率/最壞情況)。
     8. 執行 `flow11(case_num=1)`：發送 **SSU StartStopUnit** 命令，設定 `power_condition=3` (Power Down)，`immed=0`，並等待隊列清空。隨後 `time.sleep(60)` 等待 60 秒。最後發送 `power_condition=0x01` (Active/Idle) 喚醒裝置。
     9. 執行 `flow12_13`：透過 Vendor Command `0x40B0` (參數 3: Get Bin) 讀回該 `test_vb` 的 Bin 值，並與預期值 15 進行比對。
   - 預期結果：
     - 讀回的 Bin 值必須等於 **15**。
     - 這代表在 SSU Power Down 並經歷 60 秒靜置後，韌體**沒有**執行 BFEA 自動修復或 Bin 重置機制，Host 設定的高錯誤率 Bin 狀態被完整保留。

2. [Case02_SSU_Sleep_BinPersistence_Check]：
   - 動作：
     1. 重複 `flow1_4` 至 `flow10` 的初始化步驟，確保目標 `test_vb` 的 Bin 值被設定為 **15**。
     2. 執行 `flow11(case_num=2)`：發送 **SSU StartStopUnit** 命令，設定 `power_condition=0x02` (Sleep)，`immed=0`，並等待隊列清空。隨後 `time.sleep(60)` 等待 60 秒。最後發送 `power_condition=0x01` (Active/Idle) 喚醒裝置。
     3. 執行 `flow12_13`：透過 Vendor Command `0x40B0` (參數 3: Get Bin) 讀回該 `test_vb` 的 Bin 值，並與預期值 15 進行比對。
   - 預期結果：
     - 讀回的 Bin 值必須等於 **15**。
     - 這代表在 SSU Sleep 並經歷 60 秒靜置後，韌體**沒有**執行 BFEA 自動修復或 Bin 重置機制，Host 設定的高錯誤率 Bin 狀態被完整保留。

3. [BFEA_Set_Get_Consistency_Check] (隱含於 flow10 & flow12_13 的邏輯驗證)：
   - 動作：
     1. 在 `flow10` 中，針對特定的 `test_ce` 和 `test_vb`，發送 Vendor Command `0x40B0`，Payload 結構為 `[OpCode=2, VB_Index, CE_Index, Bin_Value]`，其中 `Bin_Value` 設為 15。
     2. 在 `flow12_13` 中，針對相同的 `test_ce` 和 `test_vb`，發送 Vendor Command `0x40B0`，Payload 結構為 `[OpCode=3, VB_Index, CE_Index, 0]`。
     3. 解析返回 Payload 的前 4 個 Byte (Little Endian)，提取 Bin Index 數值。
   - 預期結果：
     - 返回的 Bin Index 數值必須嚴格等於 **15**。
     - 驗證 Vendor Command `0x40B0` 的 Set/Get 機制在 FTL 層面的數據一致性，確保 Bin 標記能正確寫入並讀出，無資料損毀或映射錯誤。