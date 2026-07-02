# Test Spec: UFS Flash Controller Power Loss Analysis (PLA) & Error Injection Verification

## Verification Criterion (VC)
驗證 UFS 韌體在異常掉電（SPOR）情境下的 Power Loss Analysis (PLA) 機制與錯誤恢復能力：
1.  **LWP 狀態一致性檢查**：透過 Vendor Command `0x409D` 讀取特定 LUN 與 VB 的 LWP (Last Written Page) 狀態，驗證在連續寫入不同 WL (Write Level) 區域（TLC/MLC/SLC）後，韌體記錄的 LWP 指標是否精確對應到最後一個成功寫入的 Page Line，並確認 LWPStatus 與 FEPStatus 的邏輯正確性。
2.  **Index Mirror Page UECC 恢復機制**：針對 PTE (Parameter Table Entry) 的 Index Mirror Page LWP 注入 UECC (Uncorrectable ECC) 錯誤，執行無 SSU 的 HW_RESET。驗證韌體在無安全儲存單元保護下，無法自動修復 Index 錯誤，導致 Open VB 資訊（Table2 vs Table3）發生預期內的差異或異常，確認 Index 刷新機制在錯誤狀態下的行為。
3.  **PTE Smart Bit Flip 與 ECC 計數驗證**：針對 PTE LWP 頁面進行 Smart Bit Flip（每 Byte 翻轉 1 bit，共 100 bits），透過 Vendor Command `0x4060` 讀取原始資料並寫回，隨後使用 `0x409E` 獲取錯誤位元數。驗證韌體是否能正確識別並計數這些被注入的錯誤位元，確認 ECC 引擎的錯誤檢測與計數邏輯。
4.  **Open VB 資訊差異分析**：比較 SPOR 前後的 Open VB 資訊結構（透過 `0x40C1`），驗證在特定錯誤注入或正常寫入流程後，Logical VB、Physical VB、First Empty CE/Plane/Page 等欄位的變化是否符合預期，確保韌體內部狀態機的一致性。

## Test Case (TC) Checkpoints

1.  **[LWP_Consistency_Check_TLC_SLC_WB]**：
    -   動作：
        1.  配置 LUN：Normal LUN (0), EM1 LUN (1), WB LUN (3)。
        2.  針對指定 LUN (如 `_TestNormalLun`) 執行 `write_data_until_dedicate_lwp`，寫入資料直到達到特定的 `dedicate_lwp` 值。
        3.  在寫入過程中，根據 WL 區域（GroupA_TLC, GroupB_MLC, GroupC_TLC, GroupD_SLC）動態調整寫入長度（`tlc_ce_page`, `mlc_ce_page`, `slc_pageline`）。
        4.  每次寫入後，呼叫 `issue_409D_to_do_power_loss_analysing` 讀取 LWP Check 結果。
        5.  收集所有 CE (0~Max_Fdevice-1) 與 Plane (0~Plane_Per_Die-1) 的 LWP 檢查結果，並透過 `compare_lwp_checks` 比對前後兩次檢查結果是否一致。
    -   預期結果：
        -   LWP 值應精確反映最後寫入的 Page Line 位置。
        -   在正常寫入流程中，前後兩次 `issue_409D` 的 LWP 檢查結果（包含 LWP, LWPStatus, FEPStatus）必須完全一致（`_compare_one` 回傳 True）。
        -   若寫入跨越不同 WL 區域，LWP 的增長步長應符合該區域的 Page Line 定義（如 TLC 區域每 3 pages 一個 Page Line，SLC 區域每 1 page 一個 Page Line）。

2.  **[Index_Mirror_UECC_No_SSU_Recovery_Fail]**：
    -   動作：
        1.  透過 `get_and_print_open_vb_information` 獲取 SPOR 前的 Open VB 資訊（Table2），記錄 `INDEX_VB_number_logical` 與 `INDEX_block_First_free_physical_page`。
        2.  計算 Index Mirror Page 的 PCA 位置（Block, CE, Plane, Page），並透過 `check_ics` 確保該位置非 ICS Bad Block。
        3.  呼叫 `inject_UECC(direc_read_pca_2)` 在 Index Mirror Page LWP 注入 UECC 錯誤（寫入全 0xAA 資料以破壞 ECC）。
        4.  執行 `api.init_tester_to_unit_ready` 進行 HW_RESET，且 `powerdown=False`（無 SSU 流程）。
        5.  重新獲取 Open VB 資訊（Table3），並計算新的 Index Mirror Page PCA。
        6.  比對 Table2 與 Table3 的 Index Mirror Page PCA 資訊（`compare_pca_info`）。
    -   預期結果：
        -   由於無 SSU 保護且 Index 頁面存在 UECC 錯誤，韌體無法自動修復 Index 數據。
        -   `compare_pca_info(direc_read_pca_2, direc_read_pca_3)` 必須回傳 `False`，表示 Index 刷新機制在錯誤狀態下未能恢復到一致狀態，或導致 Open VB 資訊發生預期外的差異，驗證無 SSU 時 UECC 錯誤會殘留並影響 Index 恢復。

3.  **[PTE_Smart_Bit_Flip_ECC_Count_Verification]**：
    -   動作：
        1.  針對 PTE LUN 的特定 LBA，透過 `issue_4051_to_get_physical_address` 獲取其 PCA。
        2.  計算 PTE Block 的 First Free Page，並透過 `issue_4060_to_read_raw_data` (Ecc_Enable=0) 讀取原始資料。
        3.  呼叫 `flip_bits_one_per_byte` 在第一個 4KB 區塊內隨機翻轉 100 個位元（每個 Byte 翻 1 bit）。
        4.  透過 `issue_D060_to_erase_specific_block` 擦除該 Block。
        5.  將翻轉後的資料透過 `issue_C060_to_write_raw_data` (Ecc_Enable=0) 寫回。
        6.  透過 `issue_4060_to_read_raw_data` (Ecc_Enable=1) 讀回資料，並呼叫 `issue_409E_to_get_error_bit_numbers` 獲取錯誤位元數。
    -   預期結果：
        -   `issue_409E` 回傳的 `errorBitNumber1`, `errorBitNumber2`, `errorBitNumber3`, `errorBitNumber4` 總和應等於或接近注入的 100 個錯誤位元（考慮 ECC 分組與糾錯能力，若超出糾錯範圍則可能報告 UECC 或最大糾錯數）。
        -   讀回的資料在 ECC 啟用下應被修正（若未超出糾錯能力），或報告錯誤。
        -   驗證韌體能正確識別並計數這些特定的 Bit Flip 錯誤。

4.  **[Open_VB_Info_Diff_Analysis]**：
    -   動作：
        1.  在執行任何寫入或錯誤注入前，呼叫 `get_and_print_open_vb_information` 獲取初始 Open VB 資訊。
        2.  執行特定的寫入操作（如 `write_data_more_than_N_pageline`）或錯誤注入。
        3.  再次呼叫 `get_and_print_open_vb_information` 獲取更新後的 Open VB 資訊。
        4.  使用 `show_diff_open_vb_p2` (若啟用) 或手動比對 `OpenVBInfoUnit` 中的關鍵欄位：`logical_vb`, `physical_vb`, `first_empty_CE`, `first_empty_plane`, `first_empty_physical_page`。
    -   預期結果：
        -   在正常寫入後，`first_empty_physical_page` 應增加，`logical_vb` 可能在 VB 滿時遞增。
        -   在錯誤注入後，若韌體觸發恢復機制，`physical_vb` 或 `first_empty_*` 欄位應反映恢復後的狀態（如指向新的 VB 或 Page）。
        -   所有比對欄位的變化必須符合韌體狀態機的設計邏輯，無未定義的跳躍或損壞。