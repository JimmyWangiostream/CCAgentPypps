# Test Spec: UFS Write-Once Flag & Attribute Persistence and Vendor Reset Verification

## Verification Criterion (VC)
驗證 UFS 裝置中 Write-Once Flag (PERMANENT_WP_EN, PERMANENTLY_DIS_FW_UPDATE) 與 Write-Once Attribute (OUT_OF_ORDER_DATA_EN, CONFIG_DESCR_LOCK) 的硬體持久化行為與 Vendor Command (D083) 的清除機制：
1. **Flag 寫入鎖定驗證**：確認首次 SetFlag 後狀態變為 1，再次 SetFlag 時裝置必須回傳 `QueryResponseCode.PARAM_ALREADY_WRITTEN` 錯誤碼，證明硬體層級已鎖定且不可逆。
2. **Attribute 寫入鎖定驗證**：確認首次 WriteAttribute 後狀態改變，再次寫入原始值時裝置必須回傳 `QueryResponseCode.PARAM_ALREADY_WRITTEN` 錯誤碼，證明硬體層級已鎖定。
3. **Vendor D083 清除機制驗證**：確認在硬體鎖定狀態下，透過 Vendor Command D083 執行後，上述 Flag 與 Attribute 的狀態必須被強制重置回初始值（Flag 回 0，Attribute 回原始值），證明 Vendor Command 具備穿透硬體鎖定進行韌體/配置重置的能力。

## Test Case (TC) Checkpoints

1. **[Flag_Persistence_Lock_Check]**：
   - 動作：針對 `PERMANENT_WP_EN` 與 `PERMANENTLY_DIS_FW_UPDATE` 兩個 Flag IDN 分別執行以下序列：
     1. `ReadFlag` 讀取初始狀態。
     2. `SetFlag` 寫入設定，隨後 `ReadFlag` 驗證狀態值 (`val`) 必須等於 `1`。
     3. 再次執行 `SetFlag`（嘗試重複寫入），捕獲回應。
     4. 檢查回應中的 `rsp.upiu.b6_query_response` 欄位。
   - 預期結果：
     - 第一次 `SetFlag` 後的 `ReadFlag` 返回值必須為 `1`。
     - 第二次 `SetFlag` 的回應中，`b6_query_response` 必須精確等於 `QueryResponseCode.PARAM_ALREADY_WRITTEN`，證明硬體已永久鎖定該 Flag，拒絕重複寫入。

2. **[Attribute_Persistence_Lock_Check]**：
   - 動作：針對 `OUT_OF_ORDER_DATA_EN` 與 `CONFIG_DESCR_LOCK` 兩個 Attribute IDN 分別執行以下序列：
     1. `ReadAttribute` 讀取初始值 (`origin_val`)。
     2. `WriteAttribute` 寫入相反值 (`set_val = 1 - origin_val`)，隨後 `ReadAttribute` 驗證狀態值 (`val`) 必須等於 `set_val`。
     3. 再次執行 `WriteAttribute` 寫入原始值 (`origin_val`)，捕獲回應。
     4. 檢查回應中的 `rsp.upiu.b6_query_response` 欄位。
   - 預期結果：
     - 第一次 `WriteAttribute` 後的 `ReadAttribute` 返回值必須等於寫入的 `set_val`。
     - 第二次 `WriteAttribute` 的回應中，`b6_query_response` 必須精確等於 `QueryResponseCode.PARAM_ALREADY_WRITTEN`，證明硬體已永久鎖定該 Attribute，拒絕重複寫入。

3. **[Vendor_D083_Reset_Flags_Check]**：
   - 動作：在 Flag 已被鎖定（狀態為 1）的情況下，呼叫 `project_api.issue_D083_clean_up_write_once()` 執行 Vendor Command D083。隨後對相同的 Flag IDN 執行 `ReadFlag`。
   - 預期結果：`ReadFlag` 讀取回來的狀態值 (`val`) 必須等於 `0`。這證明 Vendor Command D083 成功清除了硬體鎖定的 Flag 狀態，使其恢復為未設定狀態。

4. **[Vendor_D083_Reset_Attributes_Check]**：
   - 動作：在 Attribute 已被鎖定（狀態為非初始值）的情況下，呼叫 `project_api.issue_D083_clean_up_write_once()` 執行 Vendor Command D083。隨後對相同的 Attribute IDN 執行 `ReadAttribute`。
   - 預期結果：`ReadAttribute` 讀取回來的狀態值 (`val`) 必須等於執行 D083 前的 `origin_val`。這證明 Vendor Command D083 成功清除了硬體鎖定的 Attribute 狀態，使其恢復為初始配置值。