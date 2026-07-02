# Test Spec: UFS LUN Configuration & Vendor D098 SLC Mode Switching Verification

## Verification Criterion (VC)
驗證 UFS 裝置在動態配置 LUN 資源（SLC/Enhanced-1, TLC/Normal, Write Booster）後，透過 Vendor Command D098 切換 SLC Block Mode 時，硬體儲存介質的邏輯映射與資料完整性行為：Case 01 確認在 Mode 0 (Default/Normal) 下，SLC LUN (LUN 0) 與 TLC LUN (LUN 1) 的資料寫入與讀回一致；Case 02 確認切換至 Mode 1 (SLC Block Mode Active) 後，SLC LUN 的資料仍可正確讀回，驗證韌體在模式切換時未破壞已存在的 LUN 映射或資料；Case 03 確認切換至 Mode 2 (SLC Block Mode Inactive/Reset) 後，SLC LUN 資料讀回正常，確保 Vendor Command 的 Mode 切換僅影響後續寫入行為或內部狀態機，而不導致現有資料損毀或 LUN 失效。

## Test Case (TC) Checkpoints
1. [Case01_Mode0_WriteRead_Integrity_Check]：
   - 動作：透過 `config_lun` 函數配置 LUN 0 為 `MemoryType.ENHANCED_1` (SLC) 並分配 `total_au//2` 個 Allocation Units，配置 LUN 1 為 `MemoryType.NORMAL` (TLC) 並分配 `total_au//2` 個 Allocation Units，同時配置 Write Booster Buffer 為 `SHARED` 類型並分配 `max_wb_size` 個 Units。接著對 LUN 0 的 LBA 0 寫入 1 個 Block 資料，並透過 `api.set_flag(FlagIDN.WRITEBOOSTER_EN)` 啟用 Write Booster 後，對 LUN 1 的 LBA 0 寫入 1 個 Block 資料。最後執行 `issue_D098_to_set_slc_block_mode(mode=0)` 確保處於 Mode 0，並分別對 LUN 0 和 LUN 1 的 LBA 0 執行 Read10 指令讀取該 Block 資料。
   - 預期結果：Read10 指令回傳狀態碼為 SUCCESS；讀回的 LUN 0 資料必須與寫入時的原始資料完全一致；讀回的 LUN 1 資料必須與寫入時的原始資料完全一致。這驗證了在 Mode 0 下，Enhanced-1 (SLC) 與 Normal (TLC) LUN 的基礎 I/O 路徑及 Write Booster 啟用狀態下的資料寫入/讀出機制正常運作。

2. [Case02_Mode1_Switch_Data_Preservation_Check]：
   - 動作：在 Case 01 的資料寫入基礎上，執行 `issue_D098_to_set_slc_block_mode(mode=1)` 發送 Vendor Command D098 並將 Mode 參數設為 1。隨後，分別對 LUN 0 (SLC) 和 LUN 1 (TLC) 的 LBA 0 執行 Read10 指令讀取之前寫入的資料。
   - 預期結果：Read10 指令回傳狀態碼為 SUCCESS；讀回的 LUN 0 資料必須與 Case 01 寫入的資料完全一致；讀回的 LUN 1 資料必須與 Case 01 寫入的資料完全一致。這驗證了切換至 Mode 1 (通常代表啟用特定的 SLC 區塊模式或優化寫入路徑) 時，韌體不會清除或損壞已存在的 LUN 資料，且 SLC/TLC 的邏輯到物理映射在模式切換後依然有效。

3. [Case03_Mode2_Switch_Data_Preservation_Check]：
   - 動作：在 Case 02 的基礎上，執行 `issue_D098_to_set_slc_block_mode(mode=2)` 發送 Vendor Command D098 並將 Mode 參數設為 2。隨後，分別對 LUN 0 (SLC) 和 LUN 1 (TLC) 的 LBA 0 執行 Read10 指令讀取之前寫入的資料。
   - 預期結果：Read10 指令回傳狀態碼為 SUCCESS；讀回的 LUN 0 資料必須與 Case 01 寫入的資料完全一致；讀回的 LUN 1 資料必須與 Case 01 寫入的資料完全一致。這驗證了切換至 Mode 2 (通常代表關閉 SLC 區塊模式或恢復預設行為) 時，硬體狀態機正確重置或切換，且不會導致現有 LUN 的資料丟失或讀取錯誤，確保 Vendor Command 的 Mode 切換僅作為控制信號而不破壞資料持久性。