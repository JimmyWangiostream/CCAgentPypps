# Test Spec: UFS PSA (Pre-Soldering Area) Lifecycle & State Transition Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 PSA (Pre-Soldering Area) 機制下的完整生命週期與狀態機轉換邏輯：
1. **硬體容量與配置一致性**：確認 `Geometry Descriptor` 中的 `q4_total_raw_device_capacity` 與 `Device Descriptor` 中的 `dPSAMaxDataSize` (SLC Pre-programming Capacity) 符合特定 CE (Chip Enable) 數量下的預期硬體規格，並驗證 LUN0 配置為佔用全部 AU 的 Normal 類型。
2. **PSA 狀態機轉換**：驗證從 `PRE_SOLDERING` 寫入資料後，狀態必須正確轉換為 `LOADING_COMPLETE`；隨後執行 HW_RESET 並對 LUN0 進行首次有效寫入，狀態必須鎖定為 `SOLDERED`。
3. **資料完整性與保護機制**：驗證在 `LOADING_COMPLETE` 狀態下寫入 LUN0 的資料可讀回；在 `SOLDERED` 狀態下，LUN0 的 PSA 區域資料與 LUN1/LUN2 (BootA/BootB) 的 Boot 資料均保持完整且可通過 Read-Compare 驗證，證明 PSA 機制未破壞正常 LUN 的資料完整性。

## Test Case (TC) Checkpoints

1. [Capacity_Configuration_Verification]：
   - 動作：讀取 `Geometry Descriptor` 的 `q4_total_raw_device_capacity` (單位 512 Byte) 並乘以 512 轉換為 Byte；讀取 `Device Descriptor` 的 `l37_psa_max_data_size` (單位 4K Byte) 並乘以 4096 轉換為 Byte。根據 `flash_setting.Max_Fdevice` (1/2/4) 比對預期值：
     - Max_Fdevice=1: Total Raw = 127,984,992,256 Bytes; dPSAMaxDataSize = 42,661,662,720 Bytes.
     - Max_Fdevice=2: Total Raw = 255,944,818,688 Bytes; dPSAMaxDataSize = 85,314,936,832 Bytes.
     - Max_Fdevice=4: Total Raw = 511,864,471,552 Bytes; dPSAMaxDataSize = 170,621,489,152 Bytes.
     - 同時執行 `config_LUN0_with_total_AU`，將 LUN0 設為 `MemoryType.NORMAL`，`ProvisioningType.THIN_PROVISIONING_ERASE`，並分配所有 Allocation Units (AU)。
   - 預期結果：讀取的容量數值必須精確等於上述對應 CE 數量的預期值，否則拋出 `SIGHTING_FAIL_WRONG_CE_NUMBER_VALUE`；LUN0 配置必須成功寫入並反映在 Unit Descriptor 中。

2. [PSA_State_Transition_Pre_to_Loading]：
   - 動作：
     1. 寫入 Attribute `BOOT_LUN_EN=1` 與 `CONFIG_DESCR_LOCK=1` 鎖定配置。
     2. 寫入 Attribute `PSA_DATA_SIZE=0x100000` (1MB)。
     3. 寫入 Attribute `PSA_STATE` 設為 `api.PSAState.PRE_SOLDERING`。
     4. 對 LUN0 執行連續 Write10 指令，寫入總量略小於 0x400,000 KB (約 64MB) 的資料，使用 `HW_FIX` pattern，並記錄寫入資訊至 `write_record_PSA_data`。
     5. 寫入 Attribute `PSA_STATE` 設為 `api.PSAState.LOADING_COMPLETE`。
     6. 執行 `api.read_compare` 驗證 LUN0 上寫入的 PSA 資料。
   - 預期結果：`PSA_STATE` 成功設為 `PRE_SOLDERING` 後允許寫入；設為 `LOADING_COMPLETE` 後，LUN0 上的所有寫入資料必須通過 Read-Compare 驗證，無資料損壞或 ECC 錯誤。

3. [Boot_LUN_Data_Integrity_Pre_PowerCycle]：
   - 動作：
     1. 對 LUN1 (BootA, `MemoryType.ENHANCED_1`) 寫入其全部容量 (`gLUCapacity[1]`) 的資料，使用 `HW_FIX` pattern，記錄至 `write_record_Boot_data`。
     2. 對 LUN2 (BootB, `MemoryType.ENHANCED_1`) 寫入其全部容量 (`gLUCapacity[2]`) 的資料，使用 `HW_FIX` pattern，記錄至 `write_record_Boot_data`。
     3. 執行 `api.read_compare` 驗證 LUN1 和 LUN2 的資料完整性。
   - 預期結果：LUN1 與 LUN2 的 Boot 資料寫入成功，且 Read-Compare 驗證通過，證明在 PSA 配置階段，Boot LUN 的資料寫入與讀取機制正常運作。

4. [PSA_State_Transition_Loading_to_Soldered]：
   - 動作：
     1. 執行 `api.init_tester_to_unit_ready` 觸發 `HW_RESET` 與 `powerdown` (電源循環)。
     2. 裝置重新上電後，對 LUN0 執行一次 Write10 指令，寫入 LBA `0x100000-1`，長度 4KB，使用 `HW_FIX` pattern。
     3. 讀取 Attribute `PSA_STATE`。
   - 預期結果：
     1. 裝置能正常從 HW_RESET 恢復。
     2. 讀取到的 `bPSAState` 數值必須等於 `api.PSAState.SOLDERED`。若不等於此值，拋出 `SIGHTING_RESPONSE_UNEXPECTED`。這驗證了 PSA 機制在首次寫入後會自動鎖定狀態，防止後續修改。

5. [Final_Data_Integrity_Post_Soldered]：
   - 動作：
     1. 在 `SOLDERED` 狀態下，執行 `api.read_compare` 驗證 LUN0 上的 PSA 資料 (包含步驟 2 寫入的 <64MB 資料及步驟 4 寫入的 4KB 資料)。
     2. 執行 `api.read_compare` 驗證 LUN1 和 LUN2 上的 Boot 資料。
   - 預期結果：所有 LUN (LUN0, LUN1, LUN2) 的資料均通過 Read-Compare 驗證，證明 PSA 狀態轉換為 `SOLDERED` 後，既有的 PSA 資料與 Boot 資料均保持完整，未因狀態鎖定或電源循環而丟失或損壞。