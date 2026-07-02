# Test Spec: FW Version & Compile Date Consistency Verification (Vendor Cmd 0x4001)

## Verification Criterion (VC)
驗證韌體版本資訊與編譯日期在「Flash Setting (Vendor Minor Code)」與「UFS Vendor Command 0x4001 (Get Fw Version)」兩個數據源之間的一致性與正確性：
1. **版本號一致性**：確認 `FwVersion.payload[0]` 與 `FwVersion.payload[1]` 分別等於 Flash Setting 中的 `Vendor_Minor_Code` 與 `Vendor_Minor_Code2`。
2. **編譯日期一致性**：確認 `CompileVersion.payload` 中的日期欄位（年、月、日）與 Flash Setting 中 `Reserved_508_1023` 欄位解析出的日期完全匹配。其中年份需結合系統時間的前兩位（如 "23"）與 Flash 中的後兩位進行拼接驗證。
3. **控制器型號正確性**：確認 `ControllerNand.value` 解析後的 ASCII 字串以 "PS8329 B68S" 開頭，驗證韌體識別之硬體平台資訊正確。

## Test Case (TC) Checkpoints
1. [FW_Version_And_Date_Consistency_Check]：
   - 動作：
     1. 呼叫 `get_flash_setting()` 獲取 Flash Setting 結構，提取 `Vendor_Minor_Code`、`Vendor_Minor_Code2` 以及 `Reserved_508_1023`。
     2. 將 `Reserved_508_1023` 轉換為 Big-Endian 位元組陣列，提取前三個位元組分別作為 `year_in_fw` (MSB), `month_in_fw`, `day_in_fw`。
     3. 呼叫 `project_api.issue_4001_to_get_fw_version()` 發送 Vendor Command 0x4001，獲取韌體版本回應物件 `fw_value_by_vu`。
     4. 提取 `FwVersion.payload[0]` 與 `FwVersion.payload[1]`，分別與 `Vendor_Minor_Code` 和 `Vendor_Minor_Code2` 進行數值比對。
     5. 提取 `CompileVersion.payload[0]` 至 `[3]`，分別作為 `year_msb`, `year_lsb`, `month_in_vu`, `day_in_vu`。
     6. 獲取系統當前時間的前兩位年份（例如 "23"），與 `year_in_fw` 拼接形成完整年份 `year_in_flash_setting`。
     7. 將 `year_msb` 與 `year_lsb` 轉換為十六進制字串並拼接，再轉為整數得到 `year_in_vu`。
     8. 比對 `year_in_flash_setting` 與 `year_in_vu`，`month_in_fw` 與 `month_in_vu`，`day_in_fw` 與 `day_in_vu`。
     9. 提取 `ControllerNand.value`，轉換為 ASCII 字串，檢查是否以 "PS8329 B68S" 開頭。
   - 預期結果：
     - `FwVersion.payload[0]` 必須等於 `Vendor_Minor_Code`。
     - `FwVersion.payload[1]` 必須等於 `Vendor_Minor_Code2`。
     - `year_in_flash_setting` 必須等於 `year_in_vu`（驗證年份拼接邏輯正確）。
     - `month_in_fw` 必須等於 `month_in_vu`。
     - `day_in_fw` 必須等於 `day_in_vu`。
     - `ControllerNand` 解析字串必須以 "PS8329 B68S" 開頭。
     - 若任何一項比對失敗，應拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。