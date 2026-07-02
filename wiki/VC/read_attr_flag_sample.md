# Test Spec: UFS Host Controller Attribute & Flag Register Access Latency & Consistency Test

## Verification Criterion (VC)
驗證 UFS 主機控制器（HCE）透過 UPIU Query Command 對特定屬性（Attribute）與旗標（Flag）進行讀寫操作時的硬體行為一致性與命令間隔（Command Gap）對效能的影響：
1. **Case 01 (Batched Execution)**：確認透過 `cmd_seq` 批次發送 `REF_CLK_FREQ` 讀取、`WRITEBOOSTER_EN` 的 Set/Read/Clear 操作，硬體能正確解析並執行這些 Query 命令，且由於命令間隔較小（lower gap），驗證在低延遲情境下韌體對屬性值與旗標狀態的即時響應能力。
2. **Case 02 (Direct API Execution)**：確認透過直接 API 呼叫發送 `BOOT_LUN_EN` 設定、`WRITEBOOSTER_EN` 的 Set/Read/Clear/Toggle 操作，硬體能正確處理這些命令，且由於命令間隔較大（bigger gap），驗證在高延遲或分散式發送情境下，旗標狀態機（State Machine）在 Set、Clear 與 Toggle 操作後的狀態轉換邏輯是否正確無誤。

## Test Case (TC) Checkpoints
1. [Case01_Batched_Attribute_Flag_Access_Check]：
   - 動作：透過 `ExecuteCMD` 序列建構並發送四個 Query 命令：
     1. `ReadAttribute` 讀取 `REF_CLK_FREQ` (IDN)。
     2. `SetFlag` 設定 `WRITEBOOSTER_EN` (IDN) 為 Enable。
     3. `ReadFlag` 讀取 `WRITEBOOSTER_EN` (IDN) 以確認狀態。
     4. `ClearFlag` 清除 `WRITEBOOSTER_EN` (IDN) 為 Disable。
     發送時設定 `clear_on_success=False` 以保留命令佇列狀態供後續檢查，隨後依次讀取並解析這四個命令的回應（Response），記錄每個回應中的 `idn`, `index`, `selector`, `val` 欄位數值。
   - 預期結果：
     - `REF_CLK_FREQ` 讀取回應的 `val` 必須為有效的參考時脈頻率數值（非 0 或錯誤碼），代表時脈屬性可正常讀取。
     - `WRITEBOOSTER_EN` 的 Set 回應 `val` 必須反映設定後的狀態（通常為 1 或 Enable 狀態）。
     - `WRITEBOOSTER_EN` 的 Read 回應 `val` 必須與 Set 後的狀態一致，確認旗標已生效。
     - `WRITEBOOSTER_EN` 的 Clear 回應 `val` 必須反映清除後的狀態（通常為 0 或 Disable 狀態）。
     - 所有回應的 `idn` 必須與請求的 IDN 完全匹配，確認命令路由正確。

2. [Case02_Direct_API_Flag_Toggle_Consistency_Check]：
   - 動作：透過 `api` 直接介面依序發送五個獨立 Query 命令：
     1. `write_attribute` 設定 `BOOT_LUN_EN` 為 `BOOT_LUN_A`。
     2. `read_attribute` 讀取 `BOOT_LUN_EN` 以驗證設定結果。
     3. `set_flag` 設定 `WRITEBOOSTER_EN` 為 Enable。
     4. `read_flag` 讀取 `WRITEBOOSTER_EN` 確認狀態。
     5. `clear_flag` 清除 `WRITEBOOSTER_EN` 為 Disable。
     6. `toggle_flag` 對 `WRITEBOOSTER_EN` 執行反轉操作（從 Disable 變為 Enable）。
   - 預期結果：
     - `BOOT_LUN_EN` 讀取回應的 `val` 必須等於 `api.BootLUNID.BOOT_LUN_A` 的對應數值，確認 Boot LUN 配置寫入成功。
     - `WRITEBOOSTER_EN` 在 Set 後讀取，其 `val` 必須為 Enable 狀態。
     - `WRITEBOOSTER_EN` 在 Clear 後，其內部狀態必須為 Disable。
     - `WRITEBOOSTER_EN` 在 Toggle 操作後，其 `val` 必須從 Disable 翻轉為 Enable 狀態，確認 Toggle 邏輯在直接 API 呼叫且命令間隔較大的情況下，仍能正確觸發硬體旗標狀態機的狀態翻轉，無狀態滯留或丟失。