# Test Spec: Thermal Protection Hard Stuck Recovery & Assert Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 Hard Thermal Protection (Hard TP) 啟用且 Shipping Mode 設定後，韌體對溫度閾值違規的強制停止機制與 Assert 記錄行為：
1.  **正常操作驗證**：確認在 Hard TP 關閉或閾值設定於安全範圍內時，4KB Write/Read 操作可正常完成且資料完整性無誤。
2.  **Shipping Mode 保護驗證**：確認在設定 Shipping Mode 後，即使發送 VU D0F3 嘗試關閉 Hard TP，硬體保護機制仍強制生效，閾值設定無效。
3.  **Hard Stuck 觸發驗證**：確認當溫度閾值設定為極端值（TD_TOOLOW_AREA_ENTER = 100C，TD_SUPER_HIGH_AREA_ENTER = 0C）時，執行 Write 操作會導致韌體進入 Hard Stuck 狀態（無回應/Timeout）。
4.  **Assert 記錄與恢復驗證**：確認 Hard Stuck 發生後，透過 DME Get 讀取的 Assert Code 非 0x0（代表有記錄錯誤），且 HW_RESET 後未寫入的 LBA 資料應為無效或舊資料（讀取比較失敗或預期 CRC 為 0），證明寫入操作被完全中止。

## Test Case (TC) Checkpoints

1.  **[Case01_Normal_Write_Read_Check]**：
    -   動作：初始化測試環境，執行 FormatUnit 於 UFS_DEVICE。透過 VU D0F3 關閉 Hard TP。針對 `self.TpThreshold` 中的兩組閾值（冷區與熱區），分別透過 VU D0F1 寫入閾值，隨後對 LUN 0 的 LBA 0 執行 4KB Write，並立即執行 Read Compare (HW_COMPARE)。
    -   預期結果：所有 Write 與 Read Compare 操作均成功返回，無 Timeout 或錯誤碼，代表在閾值設定合理且 Hard TP 關閉時，儲存媒體運作正常。

2.  **[Case02_ShippingMode_HardTP_Ignore_Check]**：
    -   動作：恢復閾值設定，透過 VU D0F3 啟用 Hard TP (TP_HARD_HOT_ONLY)。接著透過 VU D0FC 設定 Shipping Mode (Device_state=1, only_in_ram=True)。隨後發送 VU D0F3 嘗試關閉 Hard TP (TP_DISABLE)。
    -   預期結果：此步驟主要驗證 Shipping Mode 下 Hard TP 的強制性。雖然腳本未在此處直接觸發寫入失敗，但後續步驟依賴此狀態。預期裝置處於 Shipping Mode，且 Hard TP 機制被硬體層級鎖定，無法透過軟體指令關閉。

3.  **[Case03_ExtremeThreshold_Write_Stuck_Check]**：
    -   動作：在 Shipping Mode 下，透過 VU D0F1 將低溫閾值設為 180 (對應實際溫度約 100C，即 TD_TOOLOW_AREA_ENTER)，高溫閾值設為 180 (對應實際溫度約 100C，但邏輯上用於觸發極端條件，腳本註解提及 TD_SUPER_HIGH_AREA_ENTER = 0C 的意圖，實際代碼設定為 `TpThreshold[0]` 即 low=180, high=180)。隨後對 LBA `TestLBA + TestSize` (即 LBA 1) 執行 4KB Write。
    -   預期結果：Write 操作應觸發 Hard Stuck 機制，導致 Host 端收到 Timeout 異常 (`TIMEOUT_EXCEPTIONS`)。韌體應進入 Assert 狀態，停止處理後續命令。

4.  **[Case04_AssertCode_Verification]**：
    -   動作：在 Catch 到 Timeout 後，立即透過 `api.get_fw_assert_number()` 讀取韌體 Assert 編號。
    -   預期結果：讀取的 `assert_code` 必須不等於 0x0。若為 0x0，則判定為測試失敗 (`SIGHTING_FAIL_DATA_COMPARE_FAIL`)，因為這代表韌體未正確記錄 Hard Stuck 的 Assert 事件。

5.  **[Case05_PowerCycle_UnwrittenData_Check]**：
    -   動作：執行 HW_RESET (Power Cycle) 恢復裝置。隨後對之前嘗試寫入但未成功的 LBA (`TestLBA + TestSize`) 執行 Read10，並設定預期 CRC 為 0 (`ExpectedCRC = 0`)。
    -   預期結果：讀取操作應成功返回。由於之前的 Write 因 Hard Stuck 而中止，該 LBA 的內容應保持為 Reset 前的狀態（可能是 Format 後的 0x00 或舊資料）。腳本預期讀取結果與 `ExpectedCRC=0` 比對，若讀取到的資料 CRC 符合預期（通常為全 0 或無效資料），則代表寫入確實被阻止，未污染儲存空間。