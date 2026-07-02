# Test Spec: EM1 LUN SLC Page HECC Injection & SPOR Recovery Verification

## Verification Criterion (VC)
驗證 EM1 LUN (LUN 3) 在 SLC 模式下，針對特定 CE/Plane 的 Page 進行硬體級比特翻轉（Bit Flip）注入 HECC 錯誤後，系統執行無 SSU 保護的 HW_RESET 時，韌體對 LWP (Last Written Page) 狀態機與 Sporadic Write Fail Counter 的處理邏輯：Case 01 確認注入 HECC 後，LWP 指標應發生跳變（LWP_A != LWP_B），且 sporadic write fail counter 應精確增加 1，代表韌體正確識別了該次寫入失敗並更新了內部計數器，但未觸發 PTE 重建或數據修復機制。

## Test Case (TC) Checkpoints
1. [EM1_SLC_HECC_Injection_SPOR_Check]：
   - 動作：
     1. 配置 LUN，啟用 LUN 3 (EM1, Enhanced 1 Memory Type)，並寫入 2 個 SLC CE Page 的資料至 LUN 3 (Start LBA 0)。
     2. 透過 VU 0x4051 取得 LBA `slc_ce_page * ce_num + i * 4` 的 Physical Address (micron_pca)。
     3. 針對該 LBA 對應的 Page，透過 VU 0x4060 讀取 Raw Data (ECC Off)，使用 `flip_bits_one_per_byte` 函數在每個 Byte 翻轉 100 bits (共計 100 bits per byte)，生成錯誤 Payload。
     4. 使用 VU D060 擦除該 Block，並使用 VU C060 將翻轉後的 Raw Data 寫回該 Page (ECC Off)，模擬硬體介面的 HECC 錯誤。
     5. 執行 `collect_lwp_checks` 獲取重置前的 LWP 狀態 (LWP_A)。
     6. 讀取 Enhanced Health Report，記錄初始 `spor_write_fail_count`。
     7. 執行 `api.init_tester_to_unit_ready` 進行 HW_RESET (ResetType=HW_RESET, Powerdown=False)，模擬無 SSU 的異常掉電重啟。
     8. 系統恢復後，再次讀取 Enhanced Health Report，獲取當前 `spor_write_fail_count`。
     9. 再次執行 `collect_lwp_checks` 獲取重置後的 LWP 狀態 (LWP_B)。
     10. 比較 LWP_A 與 LWP_B 是否不同，並驗證資料完整性。
   - 預期結果：
     1. `current_spor_write_fail_counter` 必須等於 `original_spor_write_fail_counter + 1`，精確反映一次寫入失敗事件。
     2. LWP_A 與 LWP_B 必須不同 (`identical == False`)，代表 HW_RESET 後 LWP 指標已根據新的寫入狀態或錯誤狀態進行了更新，而非保持不變。
     3. 資料讀取比較 (SW_COMPARE) 應通過，代表儘管有 HECC 注入，韌體在無 SSU 保護下仍能維持基本的資料可讀性，但 LWP 狀態機的變化證實了錯誤已被記錄且狀態機已推進。