# Test Spec: UFS Firmware RAIN Recovery Log Verification (VU 4082)

## Verification Criterion (VC)
驗證韌體在 SLC LUN 發生 UECC 錯誤且 Refresh 機制被觸發時的 RAIN (Recovery from Array Inconsistencies) 恢復流程完整性：
1. **錯誤注入與觸發**：確認透過 VU C060 直接寫入原始資料至 SLC LUN 0 的特定物理頁面（Page）並啟用 ECC 計算，成功製造硬體層級的 UECC 錯誤；隨後透過讀取操作觸發該錯誤，並確認 Booking Queue 中有待處理的 VB 條目。
2. **恢復機制執行**：確認透過 VU C088 啟動 Refresh 流程後，韌體能識別 Booking Queue 中的錯誤 VB 並執行 RAIN 恢復。
3. **日誌完整性驗證**：透過讀取 VU 4082 日誌 Payload，驗證在 RAIN 恢復前後，日誌中是否新增了特定的 Event Log ID。預期必須新增 Log ID 39 (EVENT_SOFTBIT)、43 (EVENT_READ_DISTURB_REFRESH)、45 (EVENT_RAID_RECOVERY) 及 54 (EVEN_UFS_WRITE)，以證明韌體正確記錄了軟位元錯誤、讀取干擾刷新、RAID 恢復及 UFS 寫入等關鍵恢復步驟。

## Test Case (TC) Checkpoints
1. [Preparation_SLC_LUN_Configuration]：
   - 動作：透過 `config_lun` 配置 LUN 結構，將 LUN 0 設定為 SLC 模式（MemoryType: ENHANCED_1, Provisioning: ERASE），分配總容量的一半作為 SLC AU；將 LUN 1 設定為 TLC 模式（MemoryType: NORMAL），分配剩餘容量。啟用 Write Booster Buffer 為 SHARED 模式。
   - 預期結果：LUN 0 成功初始化為 SLC 模式，LUN 1 為 TLC 模式，且 Write Booster Buffer 配置正確，為後續的 SLC 錯誤注入提供硬體環境。

2. [Baseline_VU_4082_Log_Snapshot]：
   - 動作：執行 `issue_4082_read_log` 讀取韌體 RAM 中的 VU 4082 日誌 Payload。解析 Payload 結構，每個 Log Unit 大小為 0x20 位元組。從每個 Unit 的偏移量 0x06 處讀取 2 位元組 Little-Endian 數據作為 `log_id`，偏移量 0x00 處讀取 4 位元組作為 `timestamp`。記錄所有現有的 Log ID 及其出現次數作為基準（Before Units）。
   - 預期結果：成功解析出當前系統中已存在的日誌條目，建立 `before_units` 列表，包含所有現有的 Log ID 計數，用於後續差異比對。

3. [UECC_Injection_via_VU_C060]：
   - 動作：
     1. 透過 `issue_C088_to_start_or_stop_refresh` 發送 `StopRefresh` 參數，暫停背景 Refresh 操作，防止干擾。
     2. 向 SLC LUN 0 寫入資料，確保 LBA 0 處有有效的 VB 存在。
     3. 透過 `issue_4051_to_get_physical_address` 取得 LBA 0 對應的物理地址資訊（Die, Plane, Block, Page）。
     4. 呼叫 `issue_C060_to_write_raw_data`，將該物理頁面的資料覆寫為 0xAA 填充的 16KB Payload（`DATA_SIZE_16K_BYTE`），並設定 `Ecc_Enable=1` 和 `SLC_Enable=True`。此操作繞過正常寫入路徑，直接在硬體層面製造 ECC 無法校正的 UECC 錯誤。
   - 預期結果：硬體層面的特定 Page 資料被破壞且 ECC 標記為錯誤，但尚未觸發韌體的高層恢復邏輯，因為 Refresh 已被暫停。

4. [UECC_Trigger_and_Booking_Queue_Check]：
   - 動作：
     1. 對 SLC LUN 0 的 LBA 0 執行 Read10 操作，強制韌體讀取含有 UECC 的頁面。
     2. 透過 `issue_40C5_to_get_booking_queue` 讀取 Booking Queue 狀態。
     3. 檢查 `LogicalVBNumberInBookingQueue` 欄位的值。
   - 預期結果：讀取操作成功觸發 UECC 錯誤檢測；Booking Queue 中的 `LogicalVBNumberInBookingQueue` 必須大於 0，證明錯誤 VB 已正確入隊等待恢復，且未因 Refresh 暫停而丟失。

5. [RAIN_Recovery_Trigger_via_VU_C088]：
   - 動作：透過 `issue_C088_to_start_or_stop_refresh` 發送 `StartRefresh` 參數，啟動 Refresh 流程。
   - 預期結果：韌體偵測到 Booking Queue 中有待處理的錯誤 VB，並啟動 RAIN 恢復機制（包含 Softbit 處理、RAID 重建等步驟）來修復該 VB。

6. [Post_Recovery_VU_4082_Log_Verification]：
   - 動作：
     1. 再次執行 `issue_4082_read_log` 讀取更新後的 VU 4082 Payload。
     2. 解析新的 Log Unit 列表（After Units）。
     3. 計算新增的 Log ID：比對 After 與 Before 的 Log ID 計數，找出計數增加的 Log ID。
     4. 驗證新增的 Log ID 是否完全包含 `REQUIRED_NEW_LOG_IDS` 集合：{39, 43, 45, 54}。
   - 預期結果：
     - 必須新增 Log ID 39 (EVENT_SOFTBIT)，代表韌體執行了軟位元錯誤處理。
     - 必須新增 Log ID 43 (EVENT_READ_DISTURB_REFRESH)，代表 Refresh 機制被觸發。
     - 必須新增 Log ID 45 (EVENT_RAID_RECOVERY)，代表 RAID 恢復演算法被執行。
     - 必須新增 Log ID 54 (EVEN_UFS_WRITE)，代表恢復後的資料寫入操作被記錄。
     - 若缺少任何一個指定的 Log ID，測試應判定為失敗，證明 RAIN 恢復流程中的特定硬體/韌體交互步驟未被正確記錄或執行。