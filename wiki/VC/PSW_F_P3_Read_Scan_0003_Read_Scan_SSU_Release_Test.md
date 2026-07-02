# Test Spec: TLC Read Scan Safe Area & VB Release Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 TLC 寫入過程中，針對特定 WL (Write Line) 觸發的 SSU (Secure Storage Unit) Release 機制，以及 Read Scan 完成後 VB (Virtual Block) 狀態的正確釋放流程：
1. **SSU Release 觸發驗證**：確認當寫入進度達到特定物理 WL (`LWWL = READ_SCAN_SAFE_AREA * (SliceCnt + 2) - 1`) 時，系統正確執行 SSU Release 指令，確保安全區域的完整性。
2. **VB Scan 狀態檢查**：在寫入至特定 WL (`LWWL = READ_SCAN_SAFE_AREA * 4 - 1`) 時，透過 Vendor Command `0x40BF` 檢查當前 VB 的 Scan 狀態，預期狀態碼必須為 `1` (表示 Scan 已完成或處於可接受狀態)，否則視為 Fail。
3. **Parity 保護與 VB 釋放驗證**：寫入完成並等待 BKOPS Idle 後，透過 Vendor Command `0x4055` 查詢 Rain Parity 狀態，預期回應必須為 `TARGET_FAILURE` 且 Sense Key 為 `ILLEGAL_REQUEST` (代表 Parity 已隨 VB 關閉而失效/釋放)；最後透過 Vendor Command `0xC087` 將該 VB 加入 Booking Queue 並觸發 Refresh，最終確認該 VB 已從原 Pool 移動至 `FREE_BLK_QUEUE_TLC`。

## Test Case (TC) Checkpoints

1. **[SSU_Release_Trigger_Check]**：
   - 動作：在 TLC 寫入迴圈中，計算當前 Page 對應的物理 WL (`phy_WL`) 與 SliceCnt。當滿足條件 `LWWL == self.mConfig.READ_SCAN_SAFE_AREA.value * (SliceCnt + 2) - 1` 時，執行 `push_ssu()` 指令。
   - 預期結果：系統在指定的 WL 節點正確發送 SSU Release 指令，確保 Read Scan Safe Area 的硬體保護機制被正確觸發，無異常錯誤回報。

2. **[VB_Scan_Status_0x40BF_Check]**：
   - 動作：當寫入進度達到 `LWWL == self.mConfig.READ_SCAN_SAFE_AREA.value * 4 - 1` 時，發送 Write 指令並等待完成 (`ExecuteCMD.send`)。隨後呼叫 `get_sorted_VB_list()` 取得當前 VB 號碼 (`vb`)，並透過 `project_api.check_if_current_VB_scan_in_progress_completed(VB=vb)` 內部呼叫 Vendor Command `0x40BF` 查詢狀態。
   - 預期結果：`check_if_current_VB_scan_in_progress_completed` 回傳的狀態值必須嚴格等於 `1`。若不等於 1，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表韌體在該 WL 節點的 VB Scan 狀態檢查失敗。

3. **[Parity_Release_Verification_0x4055]**：
   - 動作：主寫入迴圈結束後，發送最後一個 Write 指令並等待完成，接著呼叫 `polling_bkops_idle()` 等待系統進入 BKOPS Idle 狀態。隨後呼叫 `project_api.issue_4055_to_get_rain_parity` (對應 Vendor Command `0x4055`)，參數設定為 `RainUser.HOST_TLC_RAIN` 且 `keep_error=True`。
   - 預期結果：回應的 UPIU 狀態必須符合以下組合：
     - `b6_response` 等於 `api.UPIUResponse.TARGET_FAILURE`
     - `b7_status` 等於 `api.ScsiStatus.CHECK_CONDITION`
     - `b32_sense_data.b2_sense_key` 等於 `api.SenseKey.ILLEGAL_REQUEST`
     此組合代表 Parity 資訊已隨 VB 關閉而無法存取或已釋放，若未符合此錯誤碼組合，則觸發 `SIGHTING_RESPONSE_UNEXPECTED`。

4. **[VB_Release_to_Free_Block_Check]**：
   - 動作：執行 Vendor Command `0xC087` (`project_api.issue_C087_to_add_VB_to_bookingQ_and_book_refresh`)，將前述確認的 VB (`vb`) 以 `MediumPriority` 加入 Booking Queue 並觸發 Book Refresh。等待 BKOPS Idle 後，再次呼叫 `get_sorted_VB_list()` 取得最新的 VB 列表 (`sorted_VB_list_dict_E`)。
   - 預期結果：在 `sorted_VB_list_dict_E` 中搜尋該 VB (`vb`)，其所在的 Pool (`pool`) 必須嚴格等於 `project_api.VBListNum.FREE_BLK_QUEUE_TLC`。若 VB 存在於其他 Pool (如 `CURRENT_L2_TLC` 或其他非 Free 狀態)，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，代表 VB 未正確釋放至 Free Block Queue。