# Test Spec: UFS Device Health Descriptor Retrieval & Field Validation

## Verification Criterion (VC)
驗證 UFS 主機端韌體透過標準 NVMe/UFS 管理命令（Get Device Health Descriptor）成功讀取裝置健康狀態描述符（Device Health Descriptor）的完整性與正確性。重點在於確認 `api.get_device_health_descriptor()` 能正確解析並返回 `DeviceHealthDescriptor410` 結構體，並驗證其中關鍵的健康指標欄位（如 Pre-End-of-Life 狀態、設備壽命估算、Refresh 總計數與進度）是否被正確映射至 Python 物件屬性，確保韌體對硬體健康狀態的監控數據可讀且結構符合規範。

## Test Case (TC) Checkpoints
1. [Descriptor_Retrieval_and_Struct_Parsing_Check]：
   - 動作：呼叫 `api.get_device_health_descriptor()` 獲取裝置健康描述符物件，並將其強轉為 `api.DeviceHealthDescriptor410` 類型。記錄並輸出以下特定欄位的數值與名稱：
     - `b0_length`：描述符長度。
     - `b1_descriptor_idn`：描述符 ID。
     - `b2_pre_eol_info`：預先結束生命週期資訊（需轉換為 `api.PreEndOfLifeInfo` 枚舉名稱）。
     - `b3_device_life_time_est_a`：設備壽命估算 A。
     - `b4_device_life_time_est_b`：設備壽命估算 B。
     - `q5` 至 `q29`：四個 Vendor Proprietary Info 欄位（分別為 `vendor_prop_info_1` 到 `vendor_prop_info_4`）。
     - `l37_refresh_total_count`：Refresh 總計數。
     - `l41_refresh_progress`：Refresh 進度。
   - 預期結果：
     - API 呼叫成功返回非空物件，且類型為 `DeviceHealthDescriptor410`。
     - `b1_descriptor_idn` 應為預期的 UFS 健康描述符 ID（通常為 0x01 或特定 Vendor 定義值，視規格而定）。
     - `b2_pre_eol_info` 應能正確映射為 `api.PreEndOfLifeInfo` 枚舉中的有效名稱（例如 "Normal", "Warning", "Critical" 等），代表韌體正確解碼了硬體回報的 EOL 狀態。
     - `l37_refresh_total_count` 與 `l41_refresh_progress` 應為有效的整數數值，反映當前 Flash 介面的 Refresh 操作統計，證明韌體能正確讀取並解析硬體內部計數器。
     - 所有 Vendor Proprietary Info 欄位應包含有效的十六進位或整數數據，確認 Vendor 特定健康資訊的傳輸通道正常。