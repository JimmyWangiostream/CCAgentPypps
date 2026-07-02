# Test Spec: UFS PSA State Machine & Media Scan Interaction Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 PSA (Pre-Soldering Area) 狀態機轉換過程中，Media Scan（媒體掃描）機制的行為一致性與隔離性：
1. **PSA OFF 狀態**：確認 Media Scan 機制正常運作，掃描指標（VB/Page/Group）必須發生位移，證明背景掃描未被禁用。
2. **PSA PRE_SOLDERING 狀態**：確認進入此狀態後，Media Scan 機制被暫停，掃描指標必須保持不變，證明韌體在 PSA 初始化階段凍結了掃描進度。
3. **PSA LOADING_COMPLETE 狀態**：確認在 PSA 區塊寫入完成並進入 Loading Complete 後，Media Scan 仍被暫停，指標保持不變。
4. **PSA SOLDERED 狀態**：確認經過 HW_RESET 進入 Soldered 狀態後，Media Scan 恢復運作（指標位移），且關鍵的 PSA VB 區塊被正確排除在掃描範圍之外（Scanned Blocks 列表中不包含 PSA VB），證明 PSA 區域的保護機制生效。

## Test Case (TC) Checkpoints

1. [Case01_PSA_OFF_MediaScan_Active_Check]：
   - 動作：將 LUN0 配置為 Normal LU，LUN1 配置為 EM1 LU；寫入 RPMB Key 並透過 VUC D085 解鎖 Config Descriptor；透過 VUC C083 將所有 VB 的 Erase Count 設為 1；設定 PSA Data Size 為最大值；對 LUN0 執行 Unmap 命令清空 PSA 空間；確認 PSA State 為 OFF (0x00)；透過 VU 40CF 讀取當前 Media Scan 指標 (`cur_scan_vb`, `cur_scan_page`, `scan_group`) 記錄為 `old_*`；透過 VU C08B 啟用 Media Scan；透過 VU C085 觸發 Media Scan 並設定 `spend_time_set = 0x1000000`；再次透過 VU 40CF 讀取新指標 `new_*`。
   - 預期結果：`new_scan_vb`、`new_scan_page` 或 `new_scan_group` 中至少有一項與 `old_*` 不同。這代表在 PSA OFF 狀態下，韌體允許 Media Scan 正常進行，掃描指標隨時間推移而更新。

2. [Case02_PSA_PRE_SOLDERING_MediaScan_Paused_Check]：
   - 動作：透過 WriteAttribute 將 PSA State 設為 PRE_SOLDERING (0x01) 並等待隊列清空；確認 PSA State 讀回為 PRE_SOLDERING；透過 VU C085 觸發 Media Scan 並增加 `spend_time_set` (+=0x100)；透過 VU 40CF 讀取當前 Media Scan 指標 `new_*`。
   - 預期結果：`new_scan_vb`、`new_scan_page` 及 `new_scan_group` 必須分別等於上一階段記錄的 `old_scan_vb`、`old_scan_page` 及 `old_scan_group`。這代表進入 PRE_SOLDERING 狀態後，韌體強制暫停 Media Scan 進度，指標保持靜止。

3. [Case03_PSA_LOADING_COMPLETE_MediaScan_Paused_Check]：
   - 動作：先將 PSA State 設為 OFF 再設回 PRE_SOLDERING 以重置狀態；確認 PSA State 為 PRE_SOLDERING；對 LUN0 (PSA LUN) 的 LBA 0 開始寫入 16MB (BLOCK4K_SIZE_16M_BYTE) 的固定模式資料 (HW_FIX)；讀取該區塊的 PCA (Physical Cluster Address) 並計算出對應的 PSA VB 號碼 (`psa_vb`)；透過 WriteAttribute 將 PSA State 設為 LOADING_COMPLETE (0x02) 並設定超時時間；確認 PSA State 讀回為 LOADING_COMPLETE；透過 VU C085 觸發 Media Scan；透過 VU 40CF 讀取當前 Media Scan 指標 `new_*`。
   - 預期結果：`new_scan_vb`、`new_scan_page` 及 `new_scan_group` 必須等於上一階段記錄的 `old_*` 值。這代表在 LOADING_COMPLETE 狀態下，即使有 PSA 資料寫入，Media Scan 仍被暫停，指標不發生位移。

4. [Case04_PSA_SOLDERED_MediaScan_Resume_And_PSA_Isolation_Check]：
   - 動作：執行 HW_RESET (Power Cycle) 硬體重啟裝置；重啟後對 LUN0 (PSA LUN) 的 LBA 0 再次寫入 16MB 固定模式資料；確認 PSA State 自動恢復為 SOLDERED (0x03)；透過 VU 40CF 讀取當前 Media Scan 指標 `old_*` 及 `scanned_blocks` 列表；透過 VU C085 觸發 Media Scan；透過 VU 40CF 讀取新指標 `new_*` 及新的 `scanned_blocks` 列表。
   - 預期結果：
     1. `new_scan_vb`、`new_scan_page` 或 `new_scan_group` 必須與 `old_*` 不同，證明進入 SOLDERED 狀態後 Media Scan 恢復運作。
     2. 在 `scanned_blocks` 列表中，絕對不能包含之前計算出的 `psa_vb` 號碼。這證明韌體在 Media Scan 演算法中正確識別並跳過了 PSA 保護區域，防止對 PSA 區塊進行不必要的掃描或標記。