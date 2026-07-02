# Test Spec: UFS Link Speed Transition & Command Gap Latency Verification

## Verification Criterion (VC)
驗證 UFS 主機控制器與裝置在動態鏈結速度切換（Link Speed Transition）過程中的時序行為與命令佇列處理機制：Case 01 確認單一 Gear 切換（TX Gear 4）後，系統能正確維持該速度狀態；Case 02 確認透過 `push_speed_change` 注入一系列交錯的 TX/RX Gear 切換指令（Gear 3/4 交替）並執行 `send()` 後，硬體層面能正確解析這些並行或串行的速度變更請求，並驗證在高速切換期間命令間隙時間（Command Gap Time）是否被壓縮或重組，確保無命令丟失或鏈結崩潰。

## Test Case (TC) Checkpoints
1. [Case01_Single_Gear4_Transition_Check]：
   - 動作：呼叫 `api.speed_change` 設定 TX Gear 為 `GEAR_4`（最高速度模式），保持 RX Gear 為當前預設值（通常為 GEAR_3 或 GEAR_4，視初始狀態而定），執行此單一速度切換動作。
   - 預期結果：UFS 鏈結應成功切換至 TX Gear 4 狀態；硬體狀態機應進入對應的高速傳輸模式，且無鏈結錯誤標誌（Link Error Flag）被觸發，確認基礎速度切換功能正常。

2. [Case02_Pushed_Multi_Gear_Transition_Check]：
   - 動作：連續呼叫 `api.push_speed_change` 四次，分別注入以下速度切換請求序列：
     1. TX Gear 3, RX Gear 3
     2. TX Gear 4, RX Gear 4
     3. TX Gear 3, RX Gear 3
     4. TX Gear 4, RX Gear 4
     隨後呼叫 `ExecuteCMD.send()` 將這些排隊的速度切換命令發送給硬體控制器。
   - 預期結果：硬體控制器應正確接收並依序處理這四個速度切換請求；鏈結狀態應在 GEAR 3 與 GEAR 4 之間進行動態切換；驗證在頻繁的速度切換過程中，命令間隙時間（Command Gap Time）被正確調整以適應新的傳輸速率，且鏈結保持穩定，無因速度切換衝突導致的鏈結重置或數據損壞。