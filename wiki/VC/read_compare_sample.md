# Test Spec: UFS Unmap Data Integrity & Read Compare Mechanism Verification

## Verification Criterion (VC)
驗證 UFS 韌體在執行 Unmap 指令後，針對已邏輯刪除（Unmapped）之 LBA 區域的資料完整性保護機制：Case 01 確認透過 HW Compare（硬體比較）讀取 Unmapped 區域時，控制器能正確識別該區域為無效/空值狀態並通過驗證（通常預期為全 0 或特定 Pattern，取決於控制器實現，此處重點在於驗證流程不報錯）；Case 02 確認透過 SW Compare（軟體 CRC 校驗）讀取同一 Unmapped 區域時，韌體能正確計算並比對 CRC，確保資料一致性。此測試旨在排除 Unmap 操作後，讀取指令誤讀到舊資料或產生 Data Integrity Error 的風險。

## Test Case (TC) Checkpoints
1. [Case01_HW_Compare_Unmapped_Zone_Check]：
   - 動作：
     1. 初始化寫入記錄 `write_record_1`。
     2. 透過 `ExecuteCMD.Write10` 對 LUN 1 的 LBA 1 寫入 3 個 LBA 的資料，並對 LBA 2 寫入 100 個 LBA 的資料（總共寫入 LBA 1-101）。
     3. 透過 `ExecuteCMD.Unmap` 對 LUN 1 的 LBA 1 解除映射長度 1（即邏輯刪除 LBA 1 的資料有效性）。
     4. 發送命令序列並等待隊列清空。
     5. 呼叫 `api.read_compare` 並指定 `api.CompareMethod.HW_COMPARE`，讀取包含 LBA 1 在內的寫入區域進行硬體層級資料比對。
   - 預期結果：HW Compare 流程必須成功完成且無錯誤返回。這代表當控制器硬體嘗試讀取已被 Unmap 的 LBA 1 時，其內部邏輯（如返回零值或特定無效標記）與預期行為一致，未觸發 Data Integrity Error 或 Read Retry 機制，驗證了 Unmap 後硬體讀取路徑的穩定性。

2. [Case02_SW_CRC_Compare_Unmapped_Zone_Check]：
   - 動作：
     1. 保持相同的寫入與 Unmap 狀態（LBA 1 已 Unmap，LBA 2-101 為有效資料）。
     2. 呼叫 `api.read_compare` 並指定 `api.CompareMethod.SW_COMPARE`，讀取相同區域進行軟體層級 CRC 校驗。
   - 預期結果：SW Compare 流程必須成功完成且無錯誤返回。這代表韌體在軟體層面計算讀取資料的 CRC 值時，能正確處理 Unmapped 區域（LBA 1）的資料內容（無論其物理值為何，只要邏輯上被標記為 Unmap，軟體校驗邏輯應能正確解析或忽略該區域的無效性，而不因資料殘留導致 CRC 比對失敗），驗證了韌體資料完整性檢查邏輯對 Unmap 狀態的正確處理。