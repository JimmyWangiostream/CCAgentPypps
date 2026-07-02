# Test Spec: VC-32 (12.h) Write Booster Program Fail & BB Table Update Verification

## Verification Criterion (VC)
驗證韌體在 Write Booster (WB) L2 區塊遭遇 Program Fail 時的錯誤處理與 Bad Block Table (BBT) 更新機制：
1. **Pre-process (Normal Area)**：確認在 Normal LUN 區域透過 Vendor Command (VU C012) 注入 Erase Fail 後，執行連續寫入觸發 L2 VB 切換時，系統能正確識別該區塊為 Bad Block，並將其加入 BBT，且 BB Count 增加 1。
2. **Step1 (WB Area)**：確認在 Write Booster L2 區塊透過 VU C012 注入 Program Fail 後，執行 Write10 指令時，韌體應觸發 Assert 0x203 並進入非唯讀模式（Device remains unresponsive），同時驗證 WB 功能標誌 (WRITEBOOSTER_EN) 已設定。此步驟旨在驗證 WB 區塊發生 Program Fail 時的特定韌體行為路徑。

## Test Case (TC) Checkpoints

1. [PreProcess_Normal_LUN_EF_BBT_Update_Check]：
   - 動作：
     1. 初始化測試環境，配置 LUN 0 (Normal), LUN 1 (EM1), LUN 2 (WB)。
     2. 透過 VU 40C1 讀取當前 L2 VB (`L2_vb`)，透過 VU 40DC 讀取下一個 L2 VB (`L2_vb_next`)。
     3. 透過 VU 405E 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 VU 40D6 預測替換區塊，確保替換池中有足夠資源 (`next_replacement_block_2 != 0xFFFF`)。
     5. 使用 Vendor Command VU C012 針對 `L2_vb_next` (CE=0, Plane=0) 注入 Erase Fail (`fail_type=1`)。
     6. 從 LBA 0 開始執行連續 Write10 指令，每次寫入 `WRITE_10_MAX_BLOCK_LEN` 長度，並持續透過 VU 40C1 監控 L2 VB 狀態。
     7. 當偵測到 L2 VB 發生變化 (`L2_vb_new != L2_vb`) 時停止寫入。
     8. 再次透過 VU 405E 讀取新的 Bad Block Count (`BB_count_new`) 及 BBT 資料。
     9. 檢查 BBT 資料中是否包含目標區塊 (`target_data_L2`)。
   - 預期結果：
     - `BB_count_new` 必須嚴格等於 `BB_count + 1`。
     - BBT 查詢結果中必須找到目標區塊 (`target_data_L2`)，代表韌體已正確將發生 Erase Fail 的區塊標記為 Bad Block 並更新表格。

2. [Step1_WB_LUN_PF_Assert_0x203_Check]：
   - 動作：
     1. 透過 VU 40C1 讀取 Write Booster L2 的當前 VB (`L2_vb`)。
     2. 設定標誌 `api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)` 啟用 WB 功能。
     3. 使用 Vendor Command VU C012 針對該 WB L2 區塊 (CE=0, Plane=0) 注入 Program Fail (`fail_type=0`)。
     4. 針對 LUN 2 (WB LUN) 執行單次 Write10 指令 (LBA=0, Length=`WRITE_10_MAX_BLOCK_LEN`)。
     5. 捕獲執行期間可能發生的異常，特別是 `G_TIMEOUT_ALL`。
     6. 若發生超時，檢查韌體 Assert 編號。
   - 預期結果：
     - 寫入指令應觸發 `G_TIMEOUT_ALL` 異常，表示裝置進入非回應狀態。
     - 韌體 Assert 編號必須等於 `0x203`。
     - 此行為確認韌體在 WB 區塊遭遇 Program Fail 時，並未進入 Read-Only 模式，而是觸發了特定的 Assert 機制 (0x203)，符合 VC-32 對於 WB 區域 Program Fail 的預期硬體行為。