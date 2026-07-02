# Test Spec: UFS Controller UECC Injection & Unmap Recovery Verification

## Verification Criterion (VC)
驗證 UFS 韌體在處理 **UECC (Uncorrectable Error Correction Code)** 錯誤時的資料完整性與邏輯層行為：
1. **寫入與環境準備**：確認在 TLC/SLC/WB 三種模式下，針對特定 LUN 寫入足夠資料以建立有效的 VB (Version Block) 環境，並透過 SSU (Start Stop Unit) 命令觸發電源狀態切換（Sleep/Active），確保控制器狀態機穩定。
2. **硬體層錯誤注入**：透過 PCA (Physical Channel Address) 精確定位 LBA 對應的 LWP (Logical Write Page)，並針對非 LMU 0 的區塊注入 UECC 錯誤，模擬快閃記憶體讀取時的硬體重損壞。
3. **正常資料讀取驗證**：在注入錯誤後，讀取未受影響的 LBA 區域，驗證韌體能否正確恢復並回傳正確的資料內容，證明錯誤注入僅限於指定範圍。
4. **邏輯層移除與讀取驗證**：對已注入 UECC 的 LBA 執行 Unmap 操作，隨後再次讀取該 LBA。預期結果為韌體應將該 LBA 視為無效或已清除，讀取結果應反映 Unmap 後的狀態（通常為全 0 或特定 Pattern，取決於韌體實現），驗證韌體在邏輯層面對物理錯誤區塊的處理機制，確保不會因物理錯誤導致系統崩潰或資料洩漏。

## Test Case (TC) Checkpoints
1. [Case01_Mode_Preparation_and_SSU_Check]：
   - 動作：根據 `TestMode` (TLC/SLC/WB) 設定對應的 LUN 與參數。若為 WB 模式，設定 `WRITEBOOSTER_EN` Flag；否則清除。計算對應模式的 VB Size (`l88_vb_size_u1` 或 `l84_vb_size_u0`) 與 Chunk Size。執行 `sequential_write` 寫入 `vb_size // 2` 的資料量，並啟用 FUA (Force Unit Access) 確保資料落盤。接著發送兩筆 SSU 命令：第一筆 `power_condition=0x02` (Sleep)，第二筆 `power_condition=0x01` (Active)，並等待隊列清空。
   - 預期結果：寫入操作成功完成，資料已持久化；控制器成功進入 Sleep 狀態並恢復至 Active 狀態，韌體內部狀態機無異常，為後續錯誤注入提供穩定的硬體環境。

2. [Case02_UECC_Hardware_Injection_Check]：
   - 動作：透過 `random` 模組生成 24 個隨機 LBA (`UECC_cnt = 24`)，確保這些 LBA 對應的物理位置 `lmu != 0` (非 LMU 0，通常為數據區而非元數據區)。將這些 LBA 轉換為 PCA，並呼叫 `inject_UECC` 函數，根據 `SLC_enable` 標誌選擇 SLC 或 TLC 的注入參數，在對應的 LWP 中注入 UECC 錯誤。
   - 預期結果：指定的 24 個 LBA 對應的物理頁面資料被標記為包含 UECC 錯誤，但韌體尚未觸發讀取，因此錯誤處於「靜默」狀態，僅在後續讀取時才會被檢測到。

3. [Case03_Normal_Data_Read_Integrity_Check]：
   - 動作：計算所有未注入 UECC 的 LBA 範圍 (`read_range`)，透過 `split_range_excluding` 排除受污染的 LBA。針對每個連續範圍發送 `Read10` 命令，讀取對應長度的資料。
   - 預期結果：所有讀取操作成功完成，回傳的資料內容與之前 `sequential_write` 寫入的內容完全一致（SW_COMPARE 驗證通過）。證明 UECC 注入僅影響特定 LBA，未波及正常資料區域，韌體讀取路徑正常。

4. [Case04_Unmap_and_UECC_Area_Read_Check]：
   - 動作：針對所有注入 UECC 的 LBA (`UECC_LBA`)，發送 `Unmap` 命令，長度為 1 Block。記錄寫入資訊後，再次針對這些 LBA 發送 `Read10` 命令進行讀取。
   - 預期結果：
     1. `Unmap` 命令成功執行，韌體邏輯層將這些 LBA 標記為未映射 (Unmapped)。
     2. 後續的 `Read10` 操作應成功返回，但讀取的資料內容應符合 Unmap 後的預期狀態（通常為全 0x00 或根據韌體策略定義的 Pattern），而非之前的原始資料或錯誤資料。
     3. 驗證韌體在處理邏輯 Unmap 後，對於物理層存在 UECC 錯誤的區塊，能夠正確處理讀取請求而不產生未處理的異常 (Unhandled Exception) 或系統 Hang，確保系統穩定性。