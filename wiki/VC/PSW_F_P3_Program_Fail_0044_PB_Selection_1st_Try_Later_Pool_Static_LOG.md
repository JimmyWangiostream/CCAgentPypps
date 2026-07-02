# Test Spec: VC-32 (12.h) Program Fail - Normal Area & LOG Area Handling Verification

## Verification Criterion (VC)
驗證韌體在快閃記憶體程式/擦除失敗（Program/Erase Fail, PF）情境下的硬體行為與韌體恢復機制：
1. **Normal Area (L2) PF Handling**：當在 Normal 區域（L2 VB）強制注入擦除失敗（Erase Fail, EF）時，韌體應正確更新 Bad Block Table (BBT)，將該區塊標記為失效，並強制進入 Read-Only 模式。驗證指標為：BB Count 增加 1，且該 L2 區塊被正確記錄在 BBT 中。
2. **LOG Area PF Handling**：當在 LOG 區域（LOG VB）強制注入程式失敗（Program Fail, PF）時，韌體應觸發 Assert 機制（Assert 0x203），導致裝置進入非回應狀態（Unresponsive），且 LOG VB 號碼不應發生改變（代表韌體未嘗試修復或切換 LOG，而是直接崩潰/掛起）。驗證指標為：捕捉到 FW Assert 0x203，且裝置在初始化後仍保持非回應狀態，未進入 Read-Only 模式。

## Test Case (TC) Checkpoints

1. **[Case01_Normal_L2_EF_BBT_Update_Check]**：
   - 動作：
     1. 透過 Vendor Command (VU 40C1) 讀取當前 L2 Open Logical VB 號碼 (`L2_vb`)。
     2. 透過 VU 40DC 讀取下一個預期的 L2 Open VB 號碼 (`L2_vb_next`)。
     3. 透過 VU 405E 記錄初始 Bad Block Count (`BB_count`)。
     4. 透過 VU 40D6 確認替換區塊池狀態。
     5. 透過 Vendor Command (VU C012) 針對 `L2_vb_next` 區塊（CE=0, Plane=0）強制注入擦除失敗（`fail_type=1`）。
     6. 執行連續 Write10 指令（LBA 從 0 開始累加），直到 VU 40C1 返回的 `L2_vb` 發生變化（表示韌體已將新區塊設為 Open VB，舊區塊被替換）。
     7. 透過 VU 4013 讀取 BE Fail Status。
     8. 透過 VU 405E 再次讀取 Bad Block Information，計算新的 BBT (`BB_data_new`) 並比較 `BB_count_new`。
   - 預期結果：
     - `BB_count_new` 必須等於 `BB_count + 1`。
     - `BB_data_new` 中必須包含目標區塊資訊（Block=`L2_vb_next`, CE=0, Plane=0），代表該區塊已被正確標記為 Bad Block。
     - 韌體成功處理了 Normal 區域的擦除失敗，更新了 BBT 並推進了 L2 VB 指針。

2. **[Case02_LOG_PF_Assert_0x203_Check]**：
   - 動作：
     1. 透過 VU 40C1 讀取當前 LOG Block VB 號碼 (`LOG_vb`)。
     2. 透過 VU 40DC 讀取下一個預期的 LOG VB 號碼 (`LOG_vb_next`)。
     3. 透過 Vendor Command (VU C012) 針對 `LOG_vb_next` 區塊（CE=0, Plane=0）強制注入程式失敗（`fail_type=0`）。
     4. 執行隨機 Write10 指令（LBA 隨機選擇），並設置 `skip_response_check=True` 以捕捉超時。
     5. 監控是否觸發 `G_TIMEOUT_ALL` 異常。
     6. 若觸發超時，檢查韌體 Assert 號碼 (`api.get_fw_assert_number()`)。
     7. 檢查 VU 40C1 返回的 `LOG_vb_new` 是否與初始 `LOG_vb` 相同。
   - 預期結果：
     - 必須觸發 `G_TIMEOUT_ALL` 異常，表示裝置在初始化後仍處於非回應狀態。
     - `api.get_fw_assert_number()` 必須返回 `0x203`（代表 Device remains unresponsive after initialization）。
     - `LOG_vb_new` 必須等於 `LOG_vb`，確認韌體在 LOG 區域發生 PF 時未進行任何狀態恢復（如切換 VB），而是直接進入 Assert 狀態，且未進入 Read-Only 模式。