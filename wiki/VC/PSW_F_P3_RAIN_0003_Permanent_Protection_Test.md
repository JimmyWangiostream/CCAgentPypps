# Test Spec: Rain Pattern APL Creation & UECC Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在 Rain Pattern 測試環境下，針對 APL (Active Page List) 建立機制的正確性及其對 UECC (Uncorrectable ECC) 錯誤的恢復能力：
1. **APL 建立驗證**：確認在寫入半個 VB (Virtual Block) 資料後，透過隨機延遲的 SPOR (System Power Off Recovery) 觸發 HW_RESET，韌體能正確識別並建立 APL 標記（APL Flag = 1），確保未完成的寫入操作在恢復後能被追蹤。
2. **全 VB 寫入後的 UECC 恢復**：在 APL 建立且 VB 寫滿後，注入 PTE LWP 的 UECC 錯誤並執行 HW_RESET，驗證韌體能否透過 APL 機制或內部重建流程修復錯誤，使讀取資料恢復正常（Payload 0x4000-0x4004 為 0x00000000）。
3. **半 VB 寫入後的 UECC 恢復**：在僅寫入半個 VB 的情境下，於隨機 LBA 注入 UECC 錯誤並寫入剩餘半個 VB 以關閉 VB，隨後執行 HW_RESET，驗證韌體在處理不連續寫入與錯誤注入混合情境下的資料完整性與恢復機制。

## Test Case (TC) Checkpoints

1. [Case01_APL_Creation_Verification]：
   - 動作：針對指定 LUN 寫入半個 VB 大小的資料（`vb_size//2`），隨後進入 `write_1_VB_with_SPOR` 循環。在該循環中，持續發送固定模式（HW_FIX）的 Write10 命令至遞增的 LBA，並在每次發送後執行 `push_spor`（包含 ALL_POWER_DOWN 與 LINK_START_UP 的完整電源循環，延遲時間從 100000us 開始遞減）。當 `api.read_compare` 拋出 `DLL_CRC32_COMPARE_FAIL` 異常時，標記 `apl_created = True`，結束循環並寫入剩餘 VB 資料。最後讀取該 VB 的 PCA 資訊，並透過 `project_api.get_APL_flag_of_VB` 讀取該 VB 的 APL Flag。
   - 預期結果：`apl_created` 必須為 True，代表韌體成功在 SPOR 後識別出未完成的寫入操作；讀回的 `APL_flag` 必須等於 1，代表 APL 標記已正確寫入並保留在韌體狀態中，證明 APL 建立機制運作正常。

2. [Case02_Full_VB_UECC_Recovery_Check]：
   - 動作：在完成 Case01 的全 VB 寫入後，透過 `get_PCA_and_print` 取得當前 VB 的 PCA 資訊。根據測試模式（TLC/SLC/WB）設定 `SLC_enable` 旗標，並呼叫 `inject_UECC` 在 PTE LWP 注入 UECC 錯誤。接著執行 `api.init_tester_to_unit_ready` 觸發 HW_RESET。韌體恢復後，呼叫 `read_compare_rain_result` 對之前寫入的 `write_record` 進行 SW_COMPARE 讀取比對。
   - 預期結果：`read_compare_rain_result` 必須成功通過，無異常拋出；代表在 HW_RESET 後，韌體成功修復了 PTE LWP 中的 UECC 錯誤，讀取回來的資料與原始寫入資料一致，驗證了全 VB 情境下的錯誤恢復能力。

3. [Case03_Half_VB_Random_UECC_Recovery_Check]：
   - 動作：重置 LUN 配置並清空寫入記錄。根據測試模式設定 Write Booster 旗標。寫入半個 VB 大小的資料（`vb_size//2`）至 LBA 0。透過 `random.randint(0, vb_size//2)` 產生隨機 LBA，取得該 LBA 對應的 PCA，並呼叫 `inject_UECC` 在該隨機位置的 PTE LWP 注入 UECC 錯誤。隨後，寫入剩餘半個 VB 大小的資料以關閉該 VB。最後呼叫 `read_compare_rain_result` 對整個 VB 的寫入記錄進行讀取比對。
   - 預期結果：`read_compare_rain_result` 必須成功通過，無異常拋出；代表即使 UECC 錯誤發生在半 VB 寫入的隨機位置，且隨後進行了後續寫入操作，韌體在 HW_RESET 後仍能正確恢復該隨機位置的資料完整性，驗證了半 VB 情境下隨機錯誤注入的恢復機制。