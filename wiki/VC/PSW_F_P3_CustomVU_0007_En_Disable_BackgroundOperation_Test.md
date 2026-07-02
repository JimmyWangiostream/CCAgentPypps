# Test Spec: UFS Vendor Command 0xD0FD Background/Foreground Operation Control & Power Cycle Persistence Test

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command (VC) 0xD0FD 控制背景/前景作業（Background/Foreground Operations）及 BG Trim 的硬體行為與韌體狀態持久性：
1. **Background Ops Control**: 驗證在 Write Booster (WB) 緩衝區滿載且 Flush 完成後，透過 VC 0xD0FD 0x00 禁用所有背景作業時，`BG_OP_STATUS` 應非零且 `WB_FLUSH_STATUS` 與 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 保持不變（不減少）；重新啟用（0x01）後，Flush 應正常完成且 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 恢復為 0xA。
2. **Power Cycle Persistence**: 驗證在禁用背景作業狀態下執行 HW_RESET，韌體應保留禁用狀態，導致重新初始化後 WB Flush 無法完成（或行為異常，需確認具體預期，此處代碼邏輯暗示禁用狀態在掉電後可能重置或需重新配置，但代碼中 Flow 13-18 顯示禁用後 Reset，再 Enable WB 並 Flush，預期結果是 Flush 成功且 Size 變 0xA，這暗示禁用背景作業的設定在 HW_RESET 後被清除或重置為預設啟用狀態，或者測試邏輯是驗證 Reset 後的初始狀態）。*修正分析*：Flow 13 禁用 BG，Flow 14 HW_RESET，Flow 15-18 重新 Enable WB 並 Flush，預期成功。這驗證了 **HW_RESET 會清除 VC 0xD0FD 的禁用狀態**，裝置恢復預設行為。
3. **Foreground GC Control**: 驗證在觸發 Wear Leveling (WL) GC 後，透過 VC 0xD0FD 0x02 禁用前景 GC，`BG_OP_STATUS` 應保持非零且穩定；重新啟用（0x03）或 HW_RESET 後，`BG_OP_STATUS` 應在 1 分鐘內歸零。
4. **BG Trim Control**: 驗證透過 VC 0xD0FD 禁用 BG Trim 後，執行 `FORMAT UNIT` 命令應觸發 `G_TIMEOUT_ALL`（裝置卡住/無回應）；恢復 BG Trim 或 HW_RESET 後，`FORMAT UNIT` 應正常完成。

## Test Case (TC) Checkpoints

1. [Case01_WB_Flush_Normal_Check]:
   - 動作：配置 Write Booster (WB) 為 0x1000 單位並啟用；隨機寫入直到 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 為 0x0；啟用 WB Flush (`WRITEBOOSTER_BUFFER_FLUSH_EN`)；輪詢 `WRITEBOOSTER_BUFFER_FLUSH_STATUS` 直到 `COMPLETED` (0x3)。
   - 預期結果：`AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 必須等於 0xA；`WRITEBOOSTER_BUFFER_FLUSH_STATUS` 必須等於 0x3。

2. [Case02_BG_Disabled_Stability_Check]:
   - 動作：重複 Case01 流程填充 WB 並 Flush 完成；禁用 WB Flush；再次填充 WB 直到 Size 為 0；啟用 WB Flush；發送 VC 0xD0FD 0x00 (Disable All BG Ops)；記錄當前的 `WB_FLUSH_STATUS` 與 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE`；輪詢 1000 次（每次間隔檢查），確認狀態未改變。
   - 預期結果：在禁用 BG Ops 期間，`WB_FLUSH_STATUS` 必須保持為 `IN_PROGRESS` (非 0x3)，且 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 必須保持為禁用前的值（不減少），代表背景 Flush 機制被硬體強制暫停。

3. [Case03_BG_Reenabled_Flush_Check]:
   - 動作：發送 VC 0xD0FD 0x01 (Enable All BG Ops)；輪詢 `WRITEBOOSTER_BUFFER_FLUSH_STATUS` 直到 `COMPLETED` (0x3)。
   - 預期結果：`WRITEBOOSTER_BUFFER_FLUSH_STATUS` 必須變更為 0x3；`AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 必須變更為 0xA，代表背景作業恢復後，緩衝區內容被成功寫入 Flash。

4. [Case04_PowerCycle_Reset_BG_Disable_Check]:
   - 動作：發送 VC 0xD0FD 0x00 (Disable All BG Ops)；執行 HW_RESET (Power Down/Up)；重新配置並啟用 WB；填充 WB 直到 Size 為 0；啟用 WB Flush；輪詢 Flush 狀態直到 `COMPLETED` (0x3)。
   - 預期結果：`WRITEBOOSTER_BUFFER_FLUSH_STATUS` 必須變更為 0x3；`AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 必須變更為 0xA。此結果驗證 **HW_RESET 會清除 VC 0xD0FD 的禁用狀態**，裝置恢復預設的 Background Operations 行為，Flush 得以正常進行。

5. [Case05_FG_GC_Disabled_BKOPS_Check]:
   - 動作：備份當前 VB Erase Count (EC)；觸發 Wear Leveling GC (設定 Source VB EC=0, Target VB EC=Threshold+1)；發送 VC 0xD0FD 0x02 (Disable All FG Ops)；讀取 `BG_OP_STATUS`；輪詢 1 分鐘，確認 `BG_OP_STATUS` 值保持不變且不等於 0x0。
   - 預期結果：`BG_OP_STATUS` 必須非 0x0（代表有未完成的背景/前景任務或狀態標記）；在 1 分鐘內該值必須保持恆定，代表前景 GC 被禁用後，相關的 BKOPS 狀態標記被鎖定且不會自動清除。

6. [Case06_FG_GC_Reenabled_BKOPS_Clear_Check]:
   - 動作：發送 VC 0xD0FD 0x03 (Enable All FG Ops)；輪詢 `BG_OP_STATUS` 直到其值等於 0x0，超時時間 1 分鐘。
   - 預期結果：`BG_OP_STATUS` 必須在 1 分鐘內變更為 0x0，代表前景作業重新啟用後，BKOPS 狀態標記被正確清除。
   - *備註*：若使用 HW_RESET 替代 VC 0x03，預期結果相同，驗證 Reset 亦能恢復 FG Ops 狀態。

7. [Case07_BG_Trim_Disabled_FormatTimeout_Check]:
   - 動作：隨機寫入大量資料；發送 VC 0xD0FD 0xXX (Disable BG Trim，具體值依 project_api 定義，通常為特定 Bitmask)；發送 `FORMAT UNIT` 命令 (LUN 0)。
   - 預期結果：`FORMAT UNIT` 命令必須觸發 `G_TIMEOUT_ALL` 異常（裝置無回應/卡住），代表禁用 BG Trim 後，裝置在格式化時因無法執行必要的背景清理操作而進入保護性停滯狀態。

8. [Case08_BG_Trim_Reenabled_FormatSuccess_Check]:
   - 動作：執行 HW_RESET (清除禁用狀態)；發送 `FORMAT UNIT` 命令；確認成功。
   - 預期結果：`FORMAT UNIT` 命令必須正常完成，無超時。
   - *後續驗證*：再次隨機寫入；禁用 BG Trim；發送 VC 0xD0FD Enable BG Trim；發送 `FORMAT UNIT`。
   - 預期結果：`FORMAT UNIT` 命令必須正常完成，代表重新啟用 BG Trim 後，格式化操作恢復正常。