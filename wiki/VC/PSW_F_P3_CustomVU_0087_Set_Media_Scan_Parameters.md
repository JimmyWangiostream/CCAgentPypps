# Test Spec: UFS Media Scan Parameter Control & Timing Verification

## Verification Criterion (VC)
驗證 UFS 韌體中 Media Scan 機制在多種 Vendor Command 參數設定下的硬體行為與狀態機轉換：
1. **BIN_LOW/HIGH 閾值檢查**：確認當 TLC Block 的 BFEA Bin 值低於或高於設定的 `bin_low`/`bin_high` 時，`VU_4028` 指令回傳的 `media_scan_status` 能正確區分「需掃描 (0xFF)」與「不需掃描 (0x0D)」的狀態。
2. **掃描進度與頻率控制**：驗證透過 `VU_C085` 設定 `last_scan_spend_time` 後，Media Scan 能否在 Idle 狀態下正確觸發並推進 `scan_group`，且進度計數器 (`cur_scan_vb`, `cur_scan_page`) 能正確歸零或遞增。
3. **Full Scan 重置機制**：確認設定 `last_full_scan_group_spend_time` 觸發 Full Scan 後，`media_scan_percentage` 是否正確重置為預設值 4。
4. **Open Block 掃描頻率**：驗證設定 `set_open_blk_freq_in_secs` 後，Media Scan 觸發間隔是否嚴格符合設定值（±3s 誤差），且掃描目標 VB Group 是否僅限於 `media_scan_open_vb_group_scan_map` 定義的特定群組。
5. **縮短掃描時間因子**：驗證設定 `set_scale_factor_reduce_scan_time` 後，相鄰兩次 Media Scan 觸發的間隔時間是否縮短至約 6 分鐘（360s ±3s），而非預設的較長間隔。

## Test Case (TC) Checkpoints

1. **[TC01_BIN_LOW_Low_Bin_Check]**：
   - 動作：配置 LUN 0 (TLC) 與 LUN 1 (SLC) 並各寫入一個 WL 大小資料。透過 `VU_C085` 設定 `set_media_scan_bin_low = 10`。取得 TLC 區塊的 PBA 資訊後，透過 `VU_4028` 觸發 Media Scan VHC，設定 `bfea_bin = 9` (小於 BIN_LOW)，`page_attr = 3` (TLC_LP)，`is_partial_block = 1`。讀取回傳的 `payload.media_scan_status`。
   - 預期結果：`payload.media_scan_status.value` 必須等於 `0xFF`。代表當 Block 的 BFEA Bin 值低於設定的 BIN_LOW 閾值時，韌體判定該區塊需要被 Media Scan 處理。

2. **[TC02_BIN_LOW_High_Bin_Check]**：
   - 動作：重置 LUN 配置並重新寫入 TLC/SLC 資料。透過 `VU_C085` 設定 `set_media_scan_bin_low = 10`。透過 `VU_4028` 觸發 Media Scan VHC，設定 `bfea_bin = 11` (大於 BIN_LOW)，其他參數同 TC01。讀取回傳的 `payload.media_scan_status`。
   - 預期結果：`payload.media_scan_status.value` 必須等於 `0x0D`。代表當 Block 的 BFEA Bin 值高於設定的 BIN_LOW 閾值時，韌體判定該區塊不需要被 Media Scan 處理（或已符合品質標準）。

3. **[TC03_BIN_HIGH_Low_Bin_Check]**：
   - 動作：重置 LUN 配置並重新寫入 TLC/SLC 資料。透過 `VU_C085` 設定 `set_media_scan_bin_high = 10`。透過 `VU_4028` 觸發 Media Scan VHC，設定 `bfea_bin = 9` (小於 BIN_HIGH)，其他參數同 TC01。讀取回傳的 `payload.media_scan_status`。
   - 預期結果：`payload.media_scan_status.value` 必須等於 `0x0D`。代表當 Block 的 BFEA Bin 值低於設定的 BIN_HIGH 閾值時，韌體判定該區塊不需要被 Media Scan 處理（處於安全範圍內）。

4. **[TC04_BIN_HIGH_High_Bin_Check]**：
   - 動作：重置 LUN 配置並重新寫入 TLC/SLC 資料。透過 `VU_C085` 設定 `set_media_scan_bin_high = 10`。透過 `VU_4028` 觸發 Media Scan VHC，設定 `bfea_bin = 11` (大於 BIN_HIGH)，其他參數同 TC01。讀取回傳的 `payload.media_scan_status`。
   - 預期結果：`payload.media_scan_status.value` 必須等於 `0xFF`。代表當 Block 的 BFEA Bin 值高於設定的 BIN_HIGH 閾值時，韌體判定該區塊需要被 Media Scan 處理（品質惡化）。

5. **[TC05_Scan_Group_Advancement_Check]**：
   - 動作：配置 LUN 並寫入資料。透過 `VU_40CF` 記錄初始 `cur_scan_vb`, `cur_scan_page`, `scan_group`。啟用 Media Scan (`VU_C08B enable`)。迴圈執行 5 次：設定 `last_scan_spend_time = 0x1000000`，等待 5 秒，透過 `VU_40CF` 讀取新狀態。檢查 `scan_group` 是否遞增（若當前為 22 則應歸零為 0），且 `cur_scan_vb` 與 `cur_scan_page` 在掃描期間不應為 `0xFFFFFFFF`，掃描結束後應恢復為 `0xFFFFFFFF`。
   - 預期結果：每次觸發後，`new_scan_group` 必須等於 `old_scan_group + 1`（或從 22 變為 0）。`cur_scan_vb` 和 `cur_scan_page` 在掃描進行中必須有有效值，掃描完成後必須重置為 `0xFFFFFFFF`，證明 Media Scan 進度計數器運作正常。

6. **[TC06_Full_Scan_Reset_Check]**：
   - 動作：禁用 Media Scan。配置 LUN 並寫入資料。啟用 Media Scan。迴圈執行 2 次：設定 `last_scan_spend_time = 0x1000000`，等待 5 秒，讀取 `scan_percentage`。最後設定 `last_full_scan_group_spend_time` 觸發 Full Scan，等待 5 秒後讀取 `media_scan_percentage`。
   - 預期結果：在 Full Scan 觸發後，`new_scan_percentage` 必須等於 `4`。證明 Full Scan 機制正確重置了掃描進度百分比計數器。

7. **[TC07_Open_Blk_Freq_Timing_Check]**：
   - 動作：禁用 Media Scan。配置 LUN 並寫入資料。啟用 Media Scan。透過 `VU_40CF` 確認 `media_scan_open_freq_in_sec` 已寫入為 30。等待 Media Scan 完成當前批次（`cur_scan_vb` 變為 `0xFFFFFFFF`）。開始計時，等待下一次 Media Scan 觸發（`cur_scan_vb` 變為非 `0xFFFFFFFF`）。計算兩次觸發間的 `elapsed_time`。檢查新掃描的 VB Group 索引是否在 `media_scan_open_vb_group_scan_map` 列表中。
   - 預期結果：`elapsed_time` 必須在 `27s` 到 `33s` 之間（30s ± 3s）。新掃描的 VB Group 必須屬於 `media_scan_open_vb_group_scan_map` 定義的群組（如 CURRENT_L2_MLC, CURRENT_PTE 等），證明 Open Block 掃描頻率設定生效且目標群組正確。

8. **[TC08_Scale_Factor_Timing_Check]**：
   - 動作：禁用 Media Scan。配置 LUN 並寫入資料。啟用 Media Scan。設定 `last_scan_spend_time = 0x1000000` 觸發第一次掃描。設定 `set_scale_factor_reduce_scan_time = 150`。等待第一次掃描完成。開始計時，等待下一次 Media Scan 觸發。計算兩次觸發間的 `elapsed_time`。
   - 預期結果：`elapsed_time` 必須在 `357s` 到 `363s` 之間（360s ± 3s）。證明 `scale_factor` 設定成功將 Media Scan 的觸發間隔縮短至約 6 分鐘，而非預設的較長間隔。