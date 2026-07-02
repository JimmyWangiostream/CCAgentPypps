# Test Spec: UFS XTEMP Refresh Mechanism & Exception Event Handling Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 XTEMP (Temperature-based Refresh) 機制啟用後，針對不同 NAND 溫度閾值（T1/T2）與 Refresh Unit 設定下的硬體行為：
1. **Refresh Status 狀態機驗證**：確認在 `REFRESH_EN` 設定且 Command Queue 為空時，`REFRESH_STATUS` 屬性應先呈現 `0x05` (Refresh In Progress/Active)，隨後自動恢復為 `0x00` (Idle/Normal)，證明 Refresh 操作已正確觸發並完成。
2. **Background Operation Alert 驗證**：確認當 Refresh 機制啟動時，透過 `ReadFlag` 查詢 `BG_OP_EN` 旗標，其 Device Information 欄位 (`b9_device_information`) 必須為 `1`，代表裝置正確回報背景操作（Refresh）正在進行。
3. **Exception Event Status (BIT11) 觸發與清除驗證**：確認在 `EXC_EVENT_CONTROL` 設定 `BIT11` 後，當 Refresh 機制觸發時，`EXC_EVENT_STATUS` 的 `BIT11` 必須被置位（Raise）；且在讀取該狀態暫存器後，`BIT11` 必須自動清除（Reset），證明異常事件狀態機符合 UFS 規範的讀取清除行為。
4. **Refresh Progress 穩定性驗證**：確認在上述條件下，`dRefreshProgress` 與 `dRefreshTotalCount` 在 Refresh 觸發期間及之後保持不變，證明此測試情境下的 Refresh 並未導致實際的 Flash 資料重新整理進度計數增加（可能因溫度條件未達實際刷新閾值或為模擬觸發）。

## Test Case (TC) Checkpoints
1. [XTEMP_Configuration_and_Initialization]：
   - 動作：
     1. 透過 `config_lun()` 配置 Normal LUN 與 Boot LUN。
     2. 讀取 `mconfig` 中的 XTEMP 參數 (`XTEMP_ENABLE_PEC`, `XTEMP_TEMP_BUFFER`, `XTEMP_TIME_DETECTION_VALUE`, `XTEMP_REFRESH_T1`, `XTEMP_REFRESH_T2`)。
     3. 計算 `set_ec_value = XTEMP_ENABLE_PEC * 100`，並透過 `set_ec` 將該值寫入至 `l52_total_vb_count` 個 VB 的 Payload 起始位置（每 4 位元組重複該值）。
     4. 執行 `HW_RESET` (Powerdown=True) 以啟用 XTEMP 演算法。
     5. 寫入 `AttributeIDN.REFRESH_METHOD = 1` (Force Refresh)。
     6. 讀取 Device Health Descriptor，記錄初始的 `refreshProgress` (Bytes 41-44) 與 `refreshCount` (Bytes 37-40)。
     7. 寫入 `AttributeIDN.EXC_EVENT_CONTROL = BIT11` 以啟用特定異常事件監控。
   - 預期結果：韌體成功初始化 XTEMP 參數；`REFRESH_METHOD` 設定為 Force 模式；`EXC_EVENT_CONTROL` 正確啟用 BIT11 監控；初始 Health Descriptor 讀取成功，作為後續比對基準。

2. [Refresh_Unit_Variation_and_Temperature_Condition_Setup]：
   - 動作：
     1. 迴圈執行 `refresh_unit` 為 0 (Slice) 與 1 (Fullcard) 兩次。
     2. 每次迴圈開始前，寫入 `AttributeIDN.REFRESH_UNIT` 為當前 `refresh_unit` 值。
     3. 讀取並記錄當下的 `refreshProgress` 與 `refreshCount`。
     4. 針對每個 `TestCases` (HOT_RESKY, COLD_RESKY)：
        - 寫入隨機長度資料至 LUN0 (Start LBA 0, Length 4KB~512KB)。
        - 讀取 T1/T2 閾值。
        - 若為 `COLD_RESKY`：透過 `set_nand_temp` 將 NAND 溫度設定為 `XTEMP_REFRESH_T1 - 1` (低於 T1)。
        - 若為 `HOT_RESKY`：透過 `set_nand_temp` 將 NAND 溫度設定為 `XTEMP_REFRESH_T2 + 1` (高於 T2)。
        - 等待 `XTEMP_TIME_DETECTION_VALUE` 時間。
        - 讀取 Device Health Descriptor，記錄 `refreshProgress_step4` 與 `refreshCount_step4`。
   - 預期結果：`REFRESH_UNIT` 設定生效；NAND 溫度成功模擬至指定閾值之外；等待時間足夠讓溫度感測器穩定；記錄下觸發 Refresh 前的 Progress 狀態。

3. [Refresh_Status_Machine_and_BG_Operation_Alert_Check]：
   - 動作：
     1. 寫入 `api.set_flag(api.FlagIDN.REFRESH_EN)` 啟用 Refresh 機制。
     2. 讀取 `AttributeIDN.REFRESH_STATUS`，檢查返回值是否等於 `0x05`。
     3. 再次讀取 `AttributeIDN.REFRESH_STATUS`，檢查返回值是否等於 `0x00`。
     4. 透過 `ExecuteCMD.ReadFlag().assign(idn=api.FlagIDN.BG_OP_EN).enqueue()` 發送 Read Flag 命令。
     5. 讀取回應 (`rsp`)，檢查 `rsp.upiu.b9_device_information` 是否等於 `1`。
   - 預期結果：
     - 第一次讀取 `REFRESH_STATUS` 必須為 `0x05`，代表 Refresh 操作已啟動。
     - 第二次讀取 `REFRESH_STATUS` 必須為 `0x00`，代表 Refresh 操作已完成或進入閒置狀態。
     - `b9_device_information` 必須為 `1`，確認裝置在 Refresh 期間正確回報 Background Operation 狀態。

4. [Exception_Event_Status_BIT11_Raise_and_Reset_Check]：
   - 動作：
     1. 讀取 `AttributeIDN.EXC_EVENT_STATUS`。
     2. 檢查返回值與 `BIT11` 進行 AND 運算，結果必須等於 `BIT11` (非零)。
     3. 再次讀取 `AttributeIDN.EXC_EVENT_STATUS`。
     4. 檢查返回值與 `BIT11` 進行 AND 運算，結果必須等於 `0` (BIT11 已清除)。
   - 預期結果：
     - 第一次讀取時，`EXC_EVENT_STATUS` 的 BIT11 必須被置位，證明 Refresh 機制觸發了預設的異常事件監控。
     - 第二次讀取時，BIT11 必須被自動清除，證明狀態暫存器符合「讀取即清除」的硬體行為規範。

5. [Refresh_Progress_Stability_Verification]：
   - 動作：
     1. 在完成上述所有檢查後，再次讀取 Device Health Descriptor。
     2. 提取新的 `refreshProgress_step8` (Bytes 41-44) 與 `refreshCount_step8` (Bytes 37-40)。
     3. 將 `refreshProgress_step8` 與步驟 2 中記錄的 `refreshProgress_step4` 進行比較。
   - 預期結果：
     - `refreshProgress_step8` 必須嚴格等於 `refreshProgress_step4`。
     - 這證明在當前測試情境（溫度觸發但可能未達實際 Flash 刷新閾值，或僅為狀態機驗證）下，Refresh 機制僅觸發了狀態變更與事件回報，並未導致實際的 Flash 資料重新整理進度計數增加。