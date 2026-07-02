# Test Spec: Rain Functionality Verification (PTE/L1) with UECC Injection and D08B Control

## Verification Criterion (VC)
驗證韌體中 Rain (Randomization/Parity) 功能在異常電源或錯誤情境下的行為控制：
1. **UECC 檢測機制**：確認在 PTE 或 L1 模式下，當特定物理頁（Page）被注入 UECC 錯誤且 Rain 功能（Table and S_CHK）處於 **Disable** 狀態時，直接讀取（Direct Read）應返回 `ReadStatus.UECC`，證明硬體/韌體能正確識別未修復的 ECC 錯誤。
2. **Rain 修復機制**：確認當 Rain 功能（Table and S_CHK）處於 **Enable** 狀態時，針對同一個已注入 UECC 的頁面進行讀取比較（Read Compare），韌體應能透過 Rain 參數自動修復錯誤，返回 `expect_error=False`（成功）。
3. **最後有效頁（Last Valid Page, LVP）保護機制**：確認當 Rain 功能中的 `Rain_in_last_valid_page` 位元被 **Disable** 時，最後有效頁（LVP）不應包含 Parity 資訊。透過直接讀取 LVP 的 Spare Area，驗證其標記字元：
   - **L1 模式**：Spare Area `0x4004` 偏移處的 `FW_spare_mark` 必須為 `0x83` (DUMMY)。
   - **PTE 模式**：Spare Area `0x4000` 至 `0x4004` 偏移處的 `FW_spare_mark` 必須為 `0x44494152` ("DIAR" 字串)。
   此驗證確保韌體在禁用 LVP 保護時，不會錯誤地寫入 Parity 數據，從而避免數據損壞或狀態不一致。

## Test Case (TC) Checkpoints
1. [Case01_UECC_Detection_With_Rain_Disabled]：
   - 動作：
     1. 針對測試 LUN (TestNormalLun/TestEM1Lun/TestWBLun) 寫入超過 1 Pageline 的資料，取得最後寫入頁面的物理地址資訊 (PCE, Plane, VB, Page)。
     2. 透過 `inject_UECC` 在該頁面的 Payload 中注入 UECC 錯誤。
     3. 透過 Vendor Command `D08B` 設定 BYTE 12 的 BIT4/5 (Table and S_CHK)，將 Rain 功能 **Disable** (`Table_and_S_CHK_rain &= ~data_recovery`)。
     4. 執行 `direct_read_raw_data_and_check_status` 直接讀取該頁面，並檢查狀態碼。
   - 預期結果：讀取狀態必須等於 `project_api.ReadStatus.UECC`。這證明在 Rain 修復機制關閉的情況下，硬體/韌體能正確報告 UECC 錯誤，未進行任何掩飾或修復。

2. [Case02_Rain_Recovery_With_Rain_Enabled]：
   - 動作：
     1. 保持上述已注入 UECC 的頁面狀態。
     2. 透過 Vendor Command `D08B` 設定 BYTE 12 的 BIT4/5 (Table and S_CHK)，將 Rain 功能 **Enable** (`Table_and_S_CHK_rain |= data_recovery`)。
     3. 執行 `read_compare_rain_result` 對該頁面進行讀取比較操作。
   - 預期結果：讀取比較結果必須為 `expect_error=False` (Pass)。這證明當 Rain 功能啟用時，韌體能利用儲存的 Rain 參數自動修復 UECC 錯誤，恢復數據完整性。

3. [Case03_LVP_No_Parity_Check_L1]：
   - 動作：
     1. 透過 Vendor Command `D08B` 設定 BYTE 12 的 BIT0/1 (`Rain_in_last_valid_page`)，將 LVP 的 Rain 保護 **Disable** (`Table_and_S_CHK_rain &= ~Rain_in_last_valid_page`)。
     2. 寫入新的資料以產生新的 Last Valid Page (LVP)。
     3. 計算並構建指向該 LVP 的 `direc_read_pca` (包含正確的 CE, Plane, Block, Page)。
     4. 執行 `api.direct_read` 直接讀取該 LVP 的原始資料 (包含 FW Spare)。
     5. 檢查 Spare Area 中 `0x4004` 偏移處的 `FW_spare_mark` 欄位。
   - 預期結果：`FW_spare_mark` 必須等於 `0x83`。若不等於，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這驗證了在禁用 LVP Rain 保護後，韌體不會在 LVP 的 Spare Area 中寫入 Parity 數據，而是保留預期的 Dummy 標記。

4. [Case04_LVP_No_Parity_Check_PTE]：
   - 動作：
     1. 透過 Vendor Command `D08B` 設定 BYTE 12 的 BIT0/1 (`Rain_in_last_valid_page`)，將 LVP 的 Rain 保護 **Disable** (`Table_and_S_CHK_rain &= ~Rain_in_last_valid_page`)。
     2. 寫入新的資料以產生新的 Last Valid Page (LVP)。
     3. 計算並構建指向該 LVP 的 `direc_read_pca`。
     4. 執行 `api.direct_read` 直接讀取該 LVP 的原始資料 (包含 FW Spare)。
     5. 檢查 Spare Area 中 `0x4000` 到 `0x4004` 偏移處的 `FW_spare_mark` 欄位（Little Endian 解碼）。
   - 預期結果：`FW_spare_mark` 必須等於 `0x44494152` (對應 ASCII "DIAR")。若不等於，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。這驗證了在 PTE 模式下，禁用 LVP Rain 保護後，韌體不會在 LVP 的 Spare Area 中寫入 Parity 數據，而是保留預期的 FW Mark 標記。