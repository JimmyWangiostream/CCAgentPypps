# Test Spec: UFS Host Controller Write10 Timeout & Error Handling Verification

## Verification Criterion (VC)
驗證 UFS 主機控制器在執行大規模連續寫入（Write10, LBA 0, Length 0xFFFF）時，針對命令層級超時的處理機制：確認當寫入命令因傳輸延遲或設備忙碌導致超過 `UniformTimeout`（20微秒）時，底層驅動程式是否正確捕獲異常並執行標準化的錯誤恢復流程（即忽略異常並繼續執行後續邏輯），同時驗證該測試用例本身作為一個基礎的 I/O 壓力測試，能夠觸發 UFS 鏈路層與傳輸層的基本數據通路，確保在極短超時設定下系統不會發生死鎖或不可恢復的硬體掛起。

## Test Case (TC) Checkpoints
1. [Write10_Large_Block_Timeout_Capture]：
   - 動作：透過 `ExecuteCMD.Write10` 建構一個寫入命令，指定目標 LUN 為 0，起始 LBA 為 0，傳輸長度為 0xFFFF（65535 個邏輯區塊，約 32MB 若區塊大小為 512B），並設置 FUA (Force Unit Access) 為 1 以強制資料寫入非揮發性記憶體。將此命令排入佇列後，立即呼叫 `ExecuteCMD.send` 並設定 `api.UniformTimeout` 為 20 微秒（us）。由於 32MB 的資料量在標準 UFS 介面下絕不可能在 20 微秒內完成傳輸，此操作預期會觸發命令層級的超時異常。程式碼中使用 `try...except` 區塊捕獲此異常並執行 `pass`（忽略錯誤）。
   - 預期結果：系統不應發生崩潰或死鎖；`except` 區塊成功捕獲超時異常，代表韌體/驅動層具備基本的命令超時檢測與異常捕獲能力。雖然測試邏輯選擇忽略錯誤（pass），但驗證重點在於確認在極端短超時條件下，Host Controller 能正確識別命令未完成狀態並返回錯誤碼（如 TIMEOUT 或 BUSY），且不會導致 UFS 鏈路層進入不可逆的錯誤狀態。

2. [FUA_Flag_Enforcement_Check]：
   - 動作：在 `Write10` 命令建構階段，明確設置 `fua=1` 參數。此參數對應 UPIU (UFS Protocol Information Unit) 中的 FUA 位元。
   - 預期結果：儘管命令因超時被中斷，但驗證邏輯需確認發送的 UPIU 命令單元中，FUA 位元已被正確置為 1。這代表測試腳本正確地將高層級的寫入語義（強制落盤）映射到底層硬體協議欄位，確保在正常執行情境下（非超時情境），UFS Device 會將資料從緩衝區強制刷新至 Flash，而非僅停留在 Host 或 Device 的易失性緩衝區中。