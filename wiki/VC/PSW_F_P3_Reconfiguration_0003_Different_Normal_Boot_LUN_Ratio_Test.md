# Test Spec: UFS LUN Configuration & Boundary Condition Stress Test

## Verification Criterion (VC)
驗證 UFS 裝置在不同 LUN 配置比例（EM1/Normal/Boot）下，韌體對 LBA 邊界條件的處理邏輯與 SCSI 命令響應機制：
1. **配置驗證**：確認 `config_lun` 函數能正確根據輸入比例計算並寫入 `Enhanced 1`、`Normal` 及 `Boot LUN A` 的分配單元（AU）數量，且 `Boot LUN A` 的屬性寫入正確。
2. **邊界寫入驗證**：針對各 LUN 的最大有效 LBA（`block_counts - 1`）執行 4KB WRITE10 命令，預期響應為 `SUCCESS`，驗證韌體能正確處理最後一個邏輯區塊的寫入。
3. **越界寫入驗證**：針對各 LUN 的 `block_counts`（即超出配置範圍的第一個 LBA）執行 4KB WRITE10 命令，預期響應為 `TARGET_FAILURE`，狀態碼為 `CHECK_CONDITION`，Sense Key 為 `ILLEGAL_REQUEST`，且 ASC (Additional Sense Code) 必須精確等於 `0x21` (LOGICAL BLOCK ADDRESS OUT OF RANGE)，驗證韌體具備嚴格的 LBA 範圍檢查機制。
4. **邊界擦除驗證**：針對各 LUN 的最大有效 LBA 執行 UNMAP 命令預期成功，並對越界 LBA (`block_counts`) 執行 UNMAP 命令，預期響應與 WRITE10 越界檢查一致（`TARGET_FAILURE`, `CHECK_CONDITION`, `ILLEGAL_REQUEST`, `ASC=0x21`），驗證擦除操作同樣受 LBA 範圍限制。

## Test Case (TC) Checkpoints
1. [LUN_Configuration_AU_Allocation_Check]：
   - 動作：透過 `generate_test_cases` 產生包含 EM1/Normal/Boot 不同比例組合的測試案例（如 100% EM1, 99% EM1/1% Boot 等），呼叫 `config_lun` 函數。該函數計算 `em1_au_size`, `normal_au_size`, `boot_au_size`，並透過 `push_write_config` 寫入 Configuration Descriptor。設定 `TestEM1Lun=0`, `TestNormalLun=2`, `TestBootLun=1`。寫入後透過 `api.write_attribute(idn=api.AttributeIDN.BOOT_LUN_EN, val=api.BootLUNID.BOOT_LUN_A)` 啟用 Boot LUN A。
   - 預期結果：Configuration Descriptor 中的 `b3_memory_type` 必須正確對應 LUN 類型（EM1/Normal），`l4_num_alloc_units` 必須等於計算出的 AU 數量。`BOOT_LUN_EN` 屬性必須被設為 `BOOT_LUN_A`。

2. [WRITE_Boundary_Success_Check]：
   - 動作：針對 `enable_lun_list` 中的每個 LUN（EM1, Normal, Boot），取得其 `q11_logical_block_count`。執行 `api.random_write` 進行隨機寫入後，針對每個 LUN 的最大有效 LBA (`block_counts - 1`) 發送 `Write10` 命令，長度為 1 (4KB)。
   - 預期結果：所有 `Write10` 命令必須返回 `UPIUResponse.TARGET_SUCCESS`，且無 Sense Data 錯誤，代表韌體允許在配置範圍內的最後一個邏輯區塊進行寫入。

3. [WRITE_Boundary_OutOfRange_Fail_Check]：
   - 動作：針對每個 LUN，針對 LBA `block_counts`（超出配置範圍）發送 `Write10` 命令。捕獲回應並檢查 `rsp.upiu.b6_response`, `rsp.upiu.b7_status`, `rsp.b32_sense_data.b2_sense_key`, 以及 `rsp.b32_sense_data.b12_asc`。
   - 預期結果：
     - `rsp.upiu.b6_response` 必須等於 `UPIUResponse.TARGET_FAILURE`。
     - `rsp.upiu.b7_status` 必須等於 `ScsiStatus.CHECK_CONDITION`。
     - `rsp.b32_sense_data.b2_sense_key` 必須等於 `SenseKey.ILLEGAL_REQUEST`。
     - `rsp.b32_sense_data.b12_asc` 必須精確等於 `0x21`。
     - 此結果證明韌體嚴格拒絕訪問未配置的 LBA 空間，並返回標準的 SCSI 越界錯誤碼。

4. [UNMAP_Boundary_Success_Check]：
   - 動作：針對每個 LUN，針對最大有效 LBA (`block_counts - 1`) 發送 `Unmap` 命令。
   - 預期結果：命令必須返回 `UPIUResponse.TARGET_SUCCESS`，代表韌體允許在配置範圍內執行邏輯擦除操作。

5. [UNMAP_Boundary_OutOfRange_Fail_Check]：
   - 動作：針對每個 LUN，針對 LBA `block_counts`（超出配置範圍）發送 `Unmap` 命令。捕獲回應並檢查相同的狀態欄位。
   - 預期結果：
     - `rsp.upiu.b6_response` 必須等於 `UPIUResponse.TARGET_FAILURE`。
     - `rsp.upiu.b7_status` 必須等於 `ScsiStatus.CHECK_CONDITION`。
     - `rsp.b32_sense_data.b2_sense_key` 必須等於 `SenseKey.ILLEGAL_REQUEST`。
     - `rsp.b32_sense_data.b12_asc` 必須精確等於 `0x21`。
     - 此結果證明 UNMAP 命令同樣受到 LBA 範圍的嚴格約束，越界操作會被硬體/韌體層級攔截並報告錯誤。