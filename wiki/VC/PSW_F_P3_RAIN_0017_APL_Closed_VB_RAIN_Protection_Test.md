# Test Spec: UFS VB (Volume Block) Closure Stability under SPOR with UECC Injection

## Verification Criterion (VC)
驗證 UFS 韌體在異常掉電（SPOR）情境下，針對已注入 UECC 錯誤之 LBA 的 Volume Block (VB) 關閉機制與資料完整性：
1. **VB 關閉時序驗證**：確認在注入 UECC 後，透過不同延遲時間（100ms 至 1000ms）的 SPOR 序列，韌體能否正確偵測到 VB 狀態並將其從 Open 轉為 Closed。預期結果為 VB Logical ID 發生變更，代表 VB 已成功關閉且未因錯誤而卡死。
2. **資料完整性驗證**：在 VB 成功關閉且系統恢復 Idle 狀態後，驗證先前寫入的資料（包含受 UECC 影響的區域）是否可被正確讀取與比對，確保韌體在處理錯誤注入情境下的 Read/Write 路徑未發生邏輯崩潰或資料損毀。
3. **多模式兼容性**：此驗證涵蓋 TLC、SLC 及 Write Booster (WB) 三種運作模式，確認不同 Flash 映射策略下的 VB 關閉行為一致性。

## Test Case (TC) Checkpoints
1. [Case01_TLC_SLC_WB_VB_Closure_Check]：
   - 動作：
     1. 初始化測試環境，針對當前測試模式（TLC/SLC/WB）設定 Write Booster 開關（WB 模式開啟，其餘關閉）。
     2. 計算目標 VB 大小 (`vb_size`) 與剩餘空間 (`last_size`)，執行順序寫入 (`sequential_write`) 填充 VB 至接近關閉臨界點，記錄寫入記錄 (`write_record`)。
     3. 計算最後一個 LBA (`UECC_lba`)，取得其 PCA (Physical Channel Address)，並透過 `inject_UECC` 函數在該 LBA 對應的 Flash 頁面注入 UECC 錯誤。
     4. 記錄注入前的 Open VB Cursor (`old_cursor`)。
     5. 進入循環測試，針對延遲時間 `[100, 200, ..., 1000]` ms 執行以下 SPOR 序列：
        - 發送 `Write10` 命令寫入最後一塊資料 (`last_size`)，設定 `fua=1` 強制寫入。
        - 執行 `push_spor(delay)`：模擬全電源關閉 (`ALL_POWER_DOWN`)，等待隊列清空，執行電源控制序列，再執行鏈路啟動 (`LINK_START_UP`)，最後發送 NOP 確認鏈路穩定。
        - 系統重置後，讀取當前 Open VB Cursor (`new_cursor`)。
        - 比較 `old_cursor.logical_vb.value` 與 `new_cursor.logical_vb.value`。若不相等，跳出循環，標記 VB 關閉成功。
     6. 輪詢等待 BKOPS 進入 Idle 狀態 (`polling_bkops_idle`)。
     7. 執行 `read_compare_rain_result` 讀取並比對所有寫入資料。
   - 預期結果：
     1. **VB 狀態變更**：在特定的延遲時間點（通常為較短延遲如 100-300ms 或視韌體定時器而定），`new_cursor.logical_vb.value` 必須不等於 `old_cursor.logical_vb.value`，證明韌體在 SPOR 恢復後正確關閉了 VB，並分配了新的 VB ID 或更新了狀態。
     2. **資料比對通過**：`read_compare_rain_result` 必須返回成功，表示儘管存在 UECC 注入，韌體在 VB 關閉流程中未導致整體資料結構崩潰，且讀取路徑能正確處理或隔離該錯誤區域（或錯誤區域位於非關鍵比對區，視具體注入邏輯而定，但腳本邏輯要求整體 Write Record 比對通過）。
     3. **模式一致性**：TLC、SLC、WB 三種模式下均應觀察到上述 VB 關閉與資料完整性行為。