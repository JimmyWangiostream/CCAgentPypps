# Test Spec: EM1 LUN SLC SPOR with Non-LWP UECC Injection Test

## Verification Criterion (VC)
驗證 EM1 LUN (LUN 3) 在 SLC 模式下，於未觸發 LWP (Last Write Page) 的特定物理頁面注入 UECC (Uncorrectable ECC) 錯誤後，執行無 SSU (Secure Storage Unit) 的 HW_RESET 硬體重啟，韌體是否正確識別並保留該錯誤標記，且 LWP (Last Write Page) 指標發生預期跳變以跳過錯誤頁面。具體驗證：1. 注入 UECC 後，LWP 指標應指向錯誤頁面之後；2. HW_RESET 後，LWP 指標必須改變（證明韌體重新掃描並更新了寫入狀態）；3. 讀取資料時，包含 UECC 注入頁面的舊資料應被讀出（代表錯誤未被修復且數據未覆蓋），而其他新寫入頁面資料正常。

## Test Case (TC) Checkpoints
1. [EM1_SLC_UECC_Injection_and_SPOR_Check]：
   - 動作：
     1. 配置 LUN 3 (EM1 LUN) 為 Normal 類型，並執行 `sequential_write` 寫入 2 個 SLC CE Page 的資料（總長度 `slc_ce_page * ce_num * 2`），確保 LWP 指標更新。
     2. 透過 `get_and_print_open_vb_information` (VU 0x40C1) 獲取當前 EM1 LUN 的 Open VB 號碼。
     3. 針對特定物理位置注入錯誤：
        - 計算目標 LBA：`slc_ce_page * ce_num + i * 4`（對應 Page 1, CE 0, Plane i）。
        - 呼叫 `flipbit_on_SLC_lba_smart`：
          - 使用 VU 0x4051 獲取該 LBA 的 Physical Address (PCA)。
          - 使用 VU 0x4060 (ECC Off) 讀取該 Page 的 Raw Data。
          - 在 Raw Data 中翻轉 100 bits (`flip_bits_one_per_byte`)。
          - 使用 Vendor Command D060 擦除該 Block。
          - 使用 Vendor Command C060 寫入翻轉後的 Raw Data（此時 ECC 為 0，數據已損壞）。
          - 驗證寫入後的錯誤位數（VU 0x409E）。
     4. 針對 Page 0 (LWP 之前的頁面) 注入 UECC：
        - 構造 `uecc_pca`，設定 `b10_block_l` 和 `b11_block_h` 為當前 VB，`b5_ce = 0`，`b6_plane = i`，`l12_fpage = 0`。
        - 呼叫 `inject_UECC(uecc_pca)` 在 Page 0 注入 UECC 錯誤。
     5. 記錄注入錯誤後的 LWP 狀態：呼叫 `collect_lwp_checks` 獲取 LWP_A。
     6. 執行無 SSU 的 HW_RESET：呼叫 `api.init_tester_to_unit_ready`，設定 `resetmode = HW_RESET`，`powerdown = False`。
     7. 重啟後獲取新的 LWP 狀態：再次呼叫 `collect_lwp_checks` 獲取 LWP_B。
     8. 比較 LWP_A 與 LWP_B，並執行資料驗證：
        - 呼叫 `compare_lwp_checks` 確認兩者不同。
        - 呼叫 `read_compare` (SW_COMPARE) 驗證資料完整性，特別關注包含 UECC 注入頁面的舊資料是否被正確讀出。
   - 預期結果：
     - LWP_A 與 LWP_B 必須不同 (`identical == False`)，證明 HW_RESET 後韌體重新掃描了 Flash 並更新了 LWP 指標。
     - 若 LWP_A 與 LWP_B 相同，測試應報錯 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     - 資料讀取驗證通過，確認韌體在無 SSU 保護下，能正確處理非 LWP 頁面的 UECC 錯誤（通常表現為該頁面數據保留或標記為壞塊，具體取決於韌體策略，但關鍵在於 LWP 指標的變化與錯誤的殘留）。