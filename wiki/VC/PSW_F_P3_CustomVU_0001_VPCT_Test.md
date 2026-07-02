# Test Spec: UFS FTL VB State Machine & Risky Type Verification

## Verification Criterion (VC)
驗證 UFS 韌體在多種寫入情境（PSA, TLC, SLC, WB, RPMB, SPOR）下的 Virtual Block (VB) 狀態機行為與屬性標記正確性：
1. **PSA 機制驗證**：確認在 `PRE_SOLDERING` 狀態下，系統不允許產生同時具備 `PSA` 與 `TLC` 標記的 VB；在 `LOADING_COMPLETE` 後，產生的 PSA VB 必須正確設定 `VPC` 大小及 `VBINFO_BIT_PSA`、`VBINFO_BIT_PMNTRAINEN` 標記。
2. **多模式 VB 狀態驗證**：確認 Normal LUN 寫入 TLC 資料後，Closed/Open VB 的 `VPC` 值符合預期（含多餘空間 `exceed_size`）；確認 EM1 LUN 寫入 SLC 資料後，VB 標記正確；確認 Write Booster (WB) LUN 啟用後產生的 VB 狀態正常。
3. **GC 佇列行為驗證**：透過 Vendor Command `0xC087` 將 VB 加入 Booking Queue，驗證 EM1 L2 VB 被標記為 `VBINFO_BIT_GC_BG_QUEUE`，TLC L2 VB 被標記為 `VBINFO_BIT_GC_FG_QUEUE`，且兩者皆具備 `VPCT_IS_PARTIAL_BLOCK` 標記；驗證 GC 完成後，Source VB 的 `VPCT_IS_GC_SRC` 與 `VBINFO_BIT_GC_SOURCE` 同步，Destination VB 的 `VBINFO_BIT_GC_DEST` 正確，且僅有一個 Destination VB。
4. **RPMB 與 SPOR 恢復驗證**：確認 RPMB 寫入後 `VPC` 計算正確；確認透過 SPOR (Power Cycle during Write) 建立的 APL (Active Partial Block) 具有 `VBINFO_BIT_IS_APL` 標記。
5. **溫度風險標記驗證**：透過 Vendor Command `0xD08A` 模擬 NAND 溫度超過 `XTEMP_REFRESH_T2 + 1`，驗證產生的 Closed/Open VB 正確標記 `VBINFO_BIT_HOT_RISKY`，且 Mconfig 參數 `XTEMP_ENABLE_PEC` 與 `XTEMP_REFRESH_T2` 被正確讀取與應用。

## Test Case (TC) Checkpoints

1. **[Case01_PSA_PreSoldering_Check]**：
   - 動作：將 `PSA_STATE` 屬性設為 `PRE_SOLDERING`，執行寫入以觸發 VB 建立，讀取所有 VB 的 `VPCT` 與 `VBINFO`。
   - 預期結果：遍歷所有 VB，若 `VBINFO_BIT_PSA` 為 1，則 `VPCT_IS_TLC` 必須為 0。若發現任何 VB 同時滿足 `VBINFO_BIT_PSA == 1` 且 `VPCT_IS_TLC == 1`，則測試失敗。此驗證 PSA 機制在預焊接階段不允許 TLC 區塊。

2. **[Case02_PSA_LoadingComplete_Check]**：
   - 動作：將 `PSA_STATE` 屬性設為 `LOADING_COMPLETE`，寫入 `slc_vb_size + slc_exceed_size` 資料至 Normal LUN，取得第一個 VB 的 PBA 並讀取其 `VPCT` 與 `VBINFO`。
   - 預期結果：該 VB 的 `VPCT.VPC` 必須等於 `slc_vb_size`；`VBINFO.VBINFO_BIT_PSA` 必須為 1；`VBINFO.VBINFO_BIT_PMNTRAINEN` 必須為 1。此驗證 PSA 區塊在載入完成後正確初始化其容量與保護標記。

3. **[Case03_MultiMode_VB_State_Check]**：
   - 動作：
     1. 寫入 `tlc_vb_size + tlc_exceed_size` 至 Normal LUN，記錄 Closed (`TLC_closed_pca`) 與 Open (`TLC_open_pca`) VB。
     2. 寫入 `slc_vb_size + slc_exceed_size` 至 EM1 LUN，記錄 Closed (`SLC_closed_pca`) 與 Open (`SLC_open_pca`) VB。
     3. 啟用 `WRITEBOOSTER_EN` 旗標，寫入 `slc_vb_size` 至 WB LUN。
     4. 讀取所有 VB 的 `VPCT` 與 `VBINFO` 並進行比對。
   - 預期結果：
     - `TLC_closed_pca` 的 `VPCT.VPC` 等於 `tlc_vb_size`。
     - `TLC_open_pca` 的 `VPCT.VPC` 等於 `tlc_exceed_size`。
     - `SLC_closed_pca` 的 `VPCT.VPC` 等於 `slc_vb_size`。
     - `SLC_open_pca` 的 `VPCT.VPC` 等於 `slc_exceed_size`。
     - 所有屬於 `CURRENT_L2` 或 `CURRENT_L3` 等活躍狀態的 VB，其 `VPCT_IS_OPEN` 必須為 1。
     - 屬於 `INCOMPLETE_BLK` 的 VB，其 `VPCT_IS_PARTIAL_BLOCK` 必須為 1。
     - 屬於 `CURRENT_DATA_GC_BLK` 的 VB，其 `VBINFO_BIT_GC_DEST` 必須為 1。

4. **[Case04_GC_Queue_Behavior_Check]**：
   - 動作：
     1. 透過 Vendor Command `0x40C1` 取得當前 Open VB 資訊，識別 EM1 L2 VB (`vb_EM1`) 與 TLC L2 VB (`vb_TLC`)。
     2. 禁用所有 BG/FG 操作。
     3. 透過 Vendor Command `0xC087` 將 `vb_EM1` 以 `LowPriority` 加入 Booking Queue，將 `vb_TLC` 以 `MediumPriority` 加入 Booking Queue。
     4. 等待 3 秒後，讀取這兩個 VB 的 `VPCT` 與 `VBINFO`。
     5. 重新啟用 BG/FG 操作，等待 GC 完成 (`polling_bkops_idle`)。
     6. 掃描所有 VB，檢查 GC Source 與 Destination 標記。
   - 預期結果：
     - `vb_EM1` 的 `VBINFO_BIT_GC_BG_QUEUE` 必須為 1，且 `VPCT_IS_PARTIAL_BLOCK` 必須為 1。
     - `vb_TLC` 的 `VBINFO_BIT_GC_FG_QUEUE` 必須為 1，且 `VPCT_IS_PARTIAL_BLOCK` 必須為 1。
     - GC 完成後，所有標記為 `VBINFO_BIT_GC_SOURCE == 1` 的 VB，其 `VPCT_IS_GC_SRC` 或 `VPCT_IS_RPMB_EM1_GC_SRC` 必須為 1。
     - 所有標記為 `VPCT_IS_GC_SRC == 1` 的 VB，其 `VBINFO_BIT_GC_SOURCE` 必須為 1。
     - 整個系統中，`VBINFO_BIT_GC_DEST` 為 1 的 VB 數量必須恰好為 1。

5. **[Case05_RPMB_and_SPOR_APL_Check]**：
   - 動作：
     1. 寫入 8KB 資料至 RPMB LUN，讀取 RPMB VB 的 `VPCT`。
     2. 呼叫 `create_VB_with_SPOR` 函數，該函數透過在寫入過程中執行 Power Cycle (SPOR) 來強制建立 APL，並記錄返回的 PCA。
     3. 讀取 RPMB VB 的 `VPC` 與 APL VB 的 `VBINFO`。
   - 預期結果：
     - RPMB VB 的 `VPCT.VPC` 必須等於 `8KB / 4KB = 2`。
     - APL VB 的 `VBINFO_BIT_IS_APL` 必須為 1。此驗證 SPOR 機制能正確識別並標記非正常關閉的區塊。

6. **[Case06_Temperature_Risky_Type_Check]**：
   - 動作：
     1. 讀取 Mconfig 中的 `XTEMP_ENABLE_PEC` 與 `XTEMP_REFRESH_T2`。
     2. 若 `XTEMP_ENABLE_PEC` 不等於 10，則寫入 10 並執行 HW_RESET 重置。
     3. 透過 Vendor Command 設定 EC 值為 `XTEMP_ENABLE_PEC * 100`。
     4. 執行 HW_RESET。
     5. 透過 Vendor Command `0xD08A` 設定 NAND 溫度為 `XTEMP_REFRESH_T2 + 1`。
     6. 等待 `XTEMP_TIME_DETECTION_VALUE` 秒。
     7. 寫入 1.5 倍 TLC VB 大小資料至 Temperature LUN，取得 Closed 與 Open VB 的 `VBINFO`。
   - 預期結果：
     - Temperature LUN 產生的 Closed VB 與 Open VB，其 `VBINFO_BIT_HOT_RISKY` 必須均為 1。此驗證當模擬溫度超過閾值時，韌體能正確將新產生的 VB 標記為 Hot Risky，以觸發後續的風險管理機制（如避免用於 GC 目標等）。