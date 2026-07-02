# Test Spec: UFS Write Booster & Host Write Status Lifecycle Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 Write Booster (WB) 啟用/禁用、WB 緩衝區生命周期耗盡、以及不同記憶體類型 (Normal vs Enhanced) 寫入情境下，Host Write Status (VU 0x4064) 的狀態機轉換邏輯：
1.  **VC1 (Init State)**：裝置初始化後，Host Write Status 應為 `2: sustain`。
2.  **VC2 (WB Enable Transition)**：配置並啟用 WB 後，狀態應轉為 `1: burst`；禁用 WB 後，狀態應恢復為 `2: sustain`。
3.  **VC3 (WB Buffer Full)**：持續寫入直到 WB 緩衝區可用空間 (`AVAILABLE_WRITEBOOSTER_BUFFER_SIZE`) 歸零，此時即使 WB 仍啟用，Host Write Status 應強制轉為 `2: sustain`，表示 WB 已無法處理 Burst 寫入。
4.  **VC4 (WB Lifetime Exceeded)**：透過 Vendor Command 修改內部 EC (Error Correction/Endurance Counter) 閾值，模擬 WB 生命周期耗盡。當 `WRITEBOOSTER_BUFFER_LIFETIME_EST` 屬性讀回 `0xB` (表示 WB 壽命已過) 時，Host Write Status 應轉為 `2: sustain`。
5.  **VC5 (Memory Type Dependency)**：在 LUN1 (Enhanced Memory Type 1, 通常對應 SLC/SLC-like 緩衝區) 寫入時，狀態應為 `1: burst`；切換至 LUN0 (Normal Memory, TLC) 寫入時，狀態應轉為 `2: sustain`，驗證 WB 僅對特定記憶體類型生效。
6.  **VC6 (GC Impact)**：觸發 Foreground GC (透過 Vendor Command 設定 MLC GC Threshold 為 10 並確認 BKOPS 狀態為 `0x2`) 後，Host Write Status 應轉為 `3: dirty`，表示裝置處於內部整理狀態，無法接受外部 Burst 寫入。

## Test Case (TC) Checkpoints

1.  **[VC1_Init_Status_Check]**：
    -   動作：在 `pre_process` 完成後，直接呼叫 `project_api.issue_4064_get_device_status_of_host_write()` 讀取裝置狀態。
    -   預期結果：讀取到的 `device_status` 整數值必須等於 `0x2`，對應狀態為 `sustain`。

2.  **[VC2_WB_Enable_Disable_Check]**：
    -   動作：
        1.  讀取 Configuration Descriptor，設定 `b17_write_booster_buffer_type = 1`，`b16_write_booster_buffer_preserve_user_space_en = 1`，`l18_num_shared_write_booster_buffer_alloc_units = 0x400`，並推送配置。
        2.  驗證配置後、啟用 WB 前，Host Write Status 為 `0x2`。
        3.  呼叫 `api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)` 啟用 WB。
        4.  再次讀取 Host Write Status。
        5.  呼叫 `api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)` 禁用 WB。
    -   預期結果：
        1.  配置後未啟用 WB 前，狀態必須為 `0x2`。
        2.  啟用 WB 後，狀態必須變更為 `0x1` (`burst`)。
        3.  禁用 WB 後，狀態必須恢復為 `0x2`。

3.  **[VC3_WB_Buffer_Full_Check]**：
    -   動作：
        1.  確保 WB 已啟用。
        2.  進入迴圈，每次寫入 `1GB` (`api.BLOCK4K_SIZE_1G_BYTE`) 至 LUN0，起始 LBA 遞增。
        3.  每次寫入後讀取 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 屬性。
        4.  當 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 等於 `0x0` 時，停止寫入。
        5.  執行最後一次寫入以確保緩衝區狀態穩定。
        6.  讀取 Host Write Status。
    -   預期結果：當 WB 緩衝區可用空間為 0 時，Host Write Status 必須為 `0x2` (`sustain`)，證明當 WB 緩衝區滿載時，裝置自動退回到 Sustained 模式。

4.  **[VC4_WB_Lifetime_Exceeded_Check]**：
    -   動作：
        1.  讀取 HwSetting 中的 `PE_COUNT_THRESHOLD_LSB` 和 `MSB`，組合成 `PE_count_threshold`。
        2.  備份當前 Device EC 值 (`get_device_ec`)。
        3.  透過 Vendor Command (`set_device_ec`) 將 Device EC 設定為 `PE_count_threshold`。
        4.  重新配置 WB 參數 (`l18_num_shared_write_booster_buffer_alloc_units = 0x400`) 並啟用 WB。
        5.  讀取 `WRITEBOOSTER_BUFFER_LIFETIME_EST` 屬性。
        6.  讀取 Host Write Status。
        7.  呼叫 `recover_ec` 恢復備份的 EC 值。
    -   預期結果：
        1.  `WRITEBOOSTER_BUFFER_LIFETIME_EST` 必須等於 `0xB`，代表 WB 緩衝區壽命已耗盡。
        2.  Host Write Status 必須為 `0x2` (`sustain`)，證明當 WB 壽命計數器觸發閾值時，WB 功能被邏輯禁用，狀態回歸 Sustained。

5.  **[VC5_Memory_Type_Dependency_Check]**：
    -   動作：
        1.  配置 LUN0 為 `NORMAL` 記憶體類型，LUN1 為 `ENHANCED_1` 記憶體類型，且兩者均分配 `total_au / 2` 的 Alloc Units，WB 配置為 0 (但在後續寫入前需確認 WB 狀態或依賴硬體預設行為，根據代碼邏輯，此處主要驗證不同 LUN 類型對 Host Write Status 的影響，代碼中未明確重新 Enable WB，但根據 VC2/VC3 上下文，此處應假設 WB 機制活躍或驗證硬體對不同 Memory Type 的預設 Host Write 行為)。*修正：代碼中 VC5 前未明確 Enable WB，但根據 VC2/VC3 的 `clear_flag`，此時 WB 應為 Disable 狀態。然而，VC5 預期 LUN1 寫入後狀態為 `1: burst`。這暗示 `ENHANCED_1` 類型可能內建類似 SLC 的硬體加速機制，或者測試環境預設 WB 為 Enable。根據代碼 `verify_device_status_of_host_write(0x1)` 在 LUN1 寫入後，預期為 Burst。*
        2.  對 LUN1 (`ENHANCED_1`) 執行 32 次隨機寫入，大小 64MB-128MB。
        3.  讀取 Host Write Status。
        4.  對 LUN0 (`NORMAL`) 執行 32 次隨機寫入，大小 64MB-128MB。
        5.  讀取 Host Write Status。
    -   預期結果：
        1.  在 LUN1 (`ENHANCED_1`) 寫入後，Host Write Status 必須為 `0x1` (`burst`)。
        2.  在 LUN0 (`NORMAL`) 寫入後，Host Write Status 必須為 `0x2` (`sustain`)。
        3.  這驗證了 WB 或硬體加速機制僅對 `ENHANCED` 類型的 LUN 生效，對 `NORMAL` 類型則視為一般寫入。

6.  **[VC6_GC_Foreground_Impact_Check]**：
    -   動作：
        1.  恢復預設配置。
        2.  對 LUN0 執行 5 次隨機寫入。
        3.  讀取當前 MLC GC Threshold (`mlc_gc_threhold`)。
        4.  透過 Vendor Command 將 MLC GC Threshold 設定為 `10`。
        5.  讀取 `BG_OP_STATUS` (BKOPS Status) 屬性。
        6.  讀取 Host Write Status。
        7.  恢復 MLC GC Threshold。
    -   預期結果：
        1.  `BG_OP_STATUS` 必須等於 `0x2`，代表裝置正在執行 Background Operation (Foreground GC)。
        2.  Host Write Status 必須為 `0x3` (`dirty`)，代表當裝置處於 GC 狀態時，Host Write 狀態標記為 Dirty，拒絕 Burst 寫入請求。