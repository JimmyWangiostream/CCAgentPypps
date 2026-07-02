# Test Spec: UFS Direct NAND Erase & PTE Status Verification (Vendor Cmd 0x40F6)

## Verification Criterion (VC)
驗證透過 Vendor Command `0x40F6` 在 Direct NAND Mode 下對特定 CE (Chip Enable) 與 Block 執行 Erase 操作後，硬體狀態機與韌體資料結構的一致性：
1. **Case 01 (Single Plane Erase)**：確認對 LUN 0 寫入 1.5 個 TLC VB 容量資料後，透過 `ori_lba_to_pba` 取得對應之 PBA (Block Address)，並針對該 Block 執行單 CE (CE Bit=1) 的 Direct NAND Erase。驗證目標為確認 Erase 後的 Spare Area 中特定偏移量 (`128 + 4096`) 的第 3 位元 (Bit 3) 被正確設定為 1，代表 Erase 狀態標記 (ERASE Status) 已生效。
2. **Case 02 (Control/Debug Check)**：確認對 LUN 0 寫入大量資料 (65535 * 6 個 4K) 後，針對對應 Block 執行 CE Bit=1 的 Direct NAND Erase。此步驟主要用於驗證 Direct Read 機制能否正確讀取到包含 FW Spare 的 Payload，並檢查相同偏移量的狀態位元，作為後續異常處理或不同 Erase 參數的基準對照。

## Test Case (TC) Checkpoints

1. **[Case01_Single_CE_Erase_Status_Check]**：
   - 動作：
     1. 獲取 FW Geometry 與 Flash Setting，計算 SLC/TLC VB Size。
     2. 針對 LUN 0，從 LBA 0 開始寫入總量為 `1.5 * tlc_vb_size` 的資料 (Chunk Size 65535)。
     3. 呼叫 `ori_lba_to_pba(lun=0, lba=0)` 取得對應的 PCA (Physical Channel Address) 結構，並解析出 Block 編號 `blk` (由 `pca.b11_block_h` 和 `pca.b10_block_l` 組合)。
     4. 呼叫 `issue_40F6_to_erase_in_direct_nand_mode`，參數設定為：`ce_bit=1` (僅針對 CE 0), `plane=3`, `start_blk=blk`, `end_blk=blk+1`, `slc_enable=0` (TLC Mode)。
     5. 呼叫 `vendor_cmd.direct_read(pca, 1, include_FW_spare=True)` 讀取該 Block 的原始資料。
     6. 檢查 Payload 中偏移量 `128 + DATA_SIZE_4K_BYTE` (即 0x1000 + 0x80 = 0x1080) 的位元組值 `status_of_blk`。
   - 預期結果：
     - `status_of_blk` 的第 3 位元 (Bit 3, Mask 0x08) 必須為 1 (`is_bit3_set(status_of_blk)` 返回 True)。
     - 若 Bit 3 不為 1，則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常，代表 Direct NAND Erase 未正確更新 Spare Area 中的 Erase Status 標記。

2. **[Case02_Multi_LBA_Erase_Readback_Check]**：
   - 動作：
     1. 針對 LUN 0，從 LBA 0 開始寫入總量為 `65535 * 6` 個 4K 區塊的資料 (使用 HW_FIX Pattern)。
     2. 呼叫 `ori_lba_to_pba(lun=0, lba=0)` 取得對應的 PCA 並解析出 Block 編號 `blk`。
     3. 呼叫 `issue_40F6_to_erase_in_direct_nand_mode`，參數設定為：`ce_bit=1` (僅針對 CE 0), `plane=3`, `start_blk=blk`, `end_blk=blk+1`, `slc_enable=0`。
     4. 呼叫 `vendor_cmd.direct_read(pca, 1, include_FW_spare=True)` 讀取該 Block 的原始資料。
     5. 列印並檢查 Payload 中偏移量 `128 + DATA_SIZE_4K_BYTE` 的位元組值。
   - 預期結果：
     - 此步驟為 Debug/Control 性質，預期 Direct Read 能成功返回非空 Payload。
     - 驗證 Direct NAND Mode 下，即使寫入大量資料，Vendor Command 仍能正確解析 LBA 至 PBA 並執行 Erase，且 Readback 機制能正確抓取包含 FW Spare 的完整 Page 資料，無記憶體越界或解析錯誤。