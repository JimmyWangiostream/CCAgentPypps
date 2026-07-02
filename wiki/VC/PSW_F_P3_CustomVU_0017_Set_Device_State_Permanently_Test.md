# Test Spec: UFS Device State Transition & E-Fuse Modification Limit Verification

## Verification Criterion (VC)
驗證 UFS 裝置在透過 Vendor Command (D0E2/D0F4) 修改 Device State 時的硬體限制與狀態機行為：
1. **State Transition Logic**：確認透過 SRAM 寫入或 Vendor Command 修改 Device State 後，裝置能正確讀取並更新內部狀態暫存器 (0xF8F80826) 及剩餘修改次數計數器 (NumOfRemainingStateChanges)。
2. **E-Fuse Write Protection**：確認當 Device State 設定為 1 (Active/Normal) 時，禁止執行 Vendor Command C083 (設定 Erase Count Table)，並預期返回 `CHECK_CONDITION` 與 Sense Key `0x24` (Illegal Request) / ASC `0x00` (Invalid Field in CDB)。
3. **Modification Limit Enforcement**：確認 Device State 最多僅允許修改 8 次 (`modify_limit = 8`)。在第 8 次修改後，狀態應鎖定為 2 (Failure Analysis/FA State)，剩餘次數歸零，且後續任何嘗試修改 State 為 0 的操作均應失敗。

## Test Case (TC) Checkpoints

1. [Case01_Initial_Setup_Efuse_Read]：
   - 動作：在測試初始化階段，透過 `api.read_Xmemory` 從 SRAM 地址 `0xF8F80800` 讀取初始 E-Fuse 資料，並設定修改上限 `modify_limit` 為 8。
   - 預期結果：成功讀取 SRAM 資料，`modify_cnt` 初始值為 0，為後續狀態變更計數建立基準。

2. [Case02_First_State_Set_HW_Reset]：
   - 動作：執行 `set_device_state_in_different_method` 將 Device State 設為 1，並透過 `direct_set_efuse=False` 使用 Vendor Command 路徑。隨後執行 `api.init_tester_to_unit_ready` 進行 HW_RESET 並帶入 SSU (Secure Storage Unit) 電源循環。
   - 預期結果：裝置成功重啟，內部狀態暫存器更新，為後續連續修改測試做準備。

3. [Case03_Verify_State_1_and_Remaining_Count]：
   - 動作：透過 Vendor Command 40E2 讀取裝置狀態，獲取 `device_state` 與 `NumOfRemainingStateChanges`。計算預期狀態值 `expect_value = (1 << 1) - 1 = 1`，預期剩餘次數為 `8 - 1 = 7`。
   - 預期結果：`device_state` 必須等於 1；`NumOfRemainingStateChanges` 必須等於 7。若不符則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

4. [Case04_C083_Rejection_Check]：
   - 動作：在 Device State 為 1 的情境下，執行 Vendor Command C083，參數設定為 `SET_EC_TABLE`，`RC_TH_Value=0`，並帶入 4KB Payload。設定 `keep_error=True` 以保留錯誤回應。
   - 預期結果：回應必須為 `TARGET_FAILURE` (UPIU b6) 且 SCSI Status 為 `CHECK_CONDITION` (UPIU b7)。Sense Data 中 ASC 必須為 `0x24`，ASCQ 必須為 `0x00`。此驗證裝置在特定 State 下拒絕 Erase Count 相關配置。

5. [Case05_Multiple_State_Transitions_Loop]：
   - 動作：執行 6 次循環 (i=0 to 5)。每次循環交替設定 Device State 為 0 或 1。前 3 次 (i<3) 使用 `direct_set_efuse=True` 直接寫入 SRAM 地址 `0xF8F80800+0x24` 的 E-Fuse 區域；後 3 次使用 Vendor Command 路徑。每次設定後均執行 HW_RESET + SSU。
   - 預期結果：
     - 每次循環後，透過 40E2 讀取的 `device_state` 必須等於 `(1 << modify_cnt) - 1`。
     - `NumOfRemainingStateChanges` 必須等於 `8 - modify_cnt`。
     - 驗證直接寫入 E-Fuse 與透過 Command 寫入在 HW_RESET 後均能正確反映在裝置狀態機中。

6. [Case06_Eighth_Modification_Failure_Check]：
   - 動作：嘗試將 Device State 設為 0。由於此前已進行 7 次修改 (`modify_cnt` 在 Case05 結束時應為 7)，此次為第 8 次嘗試。使用 `only_in_ram=False` 並設定 `keep_error=True`。
   - 預期結果：回應必須為 `TARGET_FAILURE` 且 SCSI Status 為 `CHECK_CONDITION`。此驗證當剩餘修改次數為 0 時，裝置拒絕任何 State 變更請求。

7. [Case07_Final_State_Lock_Verification]：
   - 動作：透過 Vendor Command 40E2 讀取最終裝置狀態。
   - 預期結果：
     - `device_state` 必須等於 2 (代表 Failure Analysis/FA State，即鎖定狀態)。
     - `NumOfRemainingStateChanges` 必須等於 0。
     - 此確認裝置在達到修改上限後，狀態機已永久鎖定於 FA State，且計數器歸零。