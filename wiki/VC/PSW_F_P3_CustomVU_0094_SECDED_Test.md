# Test Spec: SRAM SER/SECDED Error Injection & FW Assert Recovery Test

## Verification Criterion (VC)
驗證 UFS 韌體在針對不同內部 SRAM 區塊（RS, COP0/1, BMU, DBUF, SEC, FIP）注入 SER/SECDED 錯誤後，硬體數據通路與韌體異常處理機制的正確性：
1. **Baseline (Step 1)**：確認在禁用錯誤注入時，所有關鍵 SRAM 區域均可正常讀取，無異常中斷。
2. **Data Path Asserts (Steps 2, 3, 4, 5, 8)**：針對 RS_SRAM, COP0/1_SRAM, BMU_SRAM, FIP_SRAM 注入錯誤後，執行 1GB 順序寫入與讀取比較。預期韌體在資料通路發生不可糾正錯誤時觸發 FW Assert，並透過 HW_RESET 恢復。需精確比對 Assert Number 以區分不同模組的錯誤源（如 RS/BMU 為 0x8297，COP0/1 為 0x8298/0x8299，FIP 為 0xF500）。
3. **Security/Probe Assert (Step 7)**：針對 SEC_SRAM 注入錯誤後，透過 `write_Xmemory` 對三個特定探針地址（0xF8F82810, 0xF8F83010, 0xF8F83810）進行寫入。預期至少一次寫入觸發 FW Assert (0xF500)，驗證安全模組的錯誤攔截機制。
4. **Recovery**：每次 Assert 後，系統必須能透過 `init_tester_to_unit_ready` 成功恢復至 Unit Ready 狀態，確保韌體狀態機無死鎖。

## Test Case (TC) Checkpoints

1. [Step1_Baseline_SRAM_Read_Check]：
   - 動作：透過 Vendor Command 發送 `issue_40BD_to_inject_SER_SECDED_event` 並設定 `opCode` 為 `ErrorInjection.DISABLE_ERROR_INJECTION` 以關閉錯誤注入。隨後遍歷 `self.sram_test_address` 字典中的所有 SRAM 地址（包含 FIP, RS, COP0, COP1, BMU, DBUF, SEC 對應的地址），對每個地址執行 `read_Xmemory` 操作。
   - 預期結果：所有 `read_Xmemory` 操作的 `response.upiu.b6_response` 必須等於 `api.UPIUResponse.TARGET_SUCCESS`。代表在無錯誤注入情況下，韌體與硬體對所有關鍵 SRAM 區域的讀取通路正常，無誤碼或存取失敗。

2. [Step2_RS_SRAM_Write_Read_Assert_0x8297]：
   - 動作：注入 `ErrorInjection.RS_SRAM` 錯誤（`keep_error=True`）。取得第一個啟用的 LUN，執行 1GB (4KB chunk) 順序寫入 (`sequential_write`)，隨後執行讀取比較 (`read_compare`)。若發生超時 (`G_TIMEOUT_ALL`) 則捕獲異常。最後檢查 FW Assert Number 是否在 `[0x8297]` 中，並執行 HW_RESET 恢復。
   - 預期結果：韌體必須觸發 FW Assert，且 Assert Number 必須為 `0x8297`。這代表 Reed-Solomon (RS) 編碼/解碼單元在處理 1GB 大資料流時檢測到不可糾正的 SECDED 錯誤，觸發了特定的 RS 模組 Assert 機制。HW_RESET 後系統需恢復正常。

3. [Step3_COP0_SRAM_Write_Read_Assert_0x8298_0x8299]：
   - 動作：注入 `ErrorInjection.COP0_SRAM` 錯誤。執行與 Step 2 相同的 1GB 順序寫入與讀取比較流程。捕獲可能的 `G_TIMEOUT_ALL`。檢查 FW Assert Number 是否在 `[0x8298, 0x8299]` 中，並執行 HW_RESET 恢復。
   - 預期結果：韌體必須觸發 FW Assert，且 Assert Number 必須為 `0x8298` 或 `0x8299`。這代表 COP0 (Command/Control Processor 0) 相關的 SRAM 在資料處理過程中發生錯誤，觸發了 COP0 模組的 Assert 機制。

4. [Step4_COP1_SRAM_Write_Read_Assert_0x8298_0x8299]：
   - 動作：注入 `ErrorInjection.COP1_SRAM` 錯誤。執行與 Step 2 相同的 1GB 順序寫入與讀取比較流程。捕獲可能的 `G_TIMEOUT_ALL`。檢查 FW Assert Number 是否在 `[0x8298, 0x8299]` 中，並執行 HW_RESET 恢復。
   - 預期結果：韌體必須觸發 FW Assert，且 Assert Number 必須為 `0x8298` 或 `0x8299`。這代表 COP1 相關的 SRAM 錯誤同樣被歸類至 COP 模組的 Assert 處理路徑，驗證 COP1 錯誤攔截機制與 COP0 一致或共用同一 Assert 碼範圍。

5. [Step5_BMU_SRAM_Write_Read_Assert_0x8297]：
   - 動作：注入 `ErrorInjection.BMU_SRAM` 錯誤。執行與 Step 2 相同的 1GB 順序寫入與讀取比較流程。捕獲可能的 `G_TIMEOUT_ALL`。檢查 FW Assert Number 是否在 `[0x8297]` 中，並執行 HW_RESET 恢復。
   - 預期結果：韌體必須觸發 FW Assert，且 Assert Number 必須為 `0x8297`。這代表 BMU (Buffer Management Unit) 在資料緩衝或搬移過程中檢測到 SRAM 錯誤，觸發了與 RS 模組相同的 Assert 碼 `0x8297`，需確認韌體對 BMU 錯誤的識別邏輯。

6. [Step7_SEC_SRAM_Probe_Assert_0xF500]：
   - 動作：注入 `ErrorInjection.SEC_SRAM` 錯誤。定義三個探針地址：`0xF8F82810`, `0xF8F83010`, `0xF8F83810`。依序對這三個地址執行 `write_Xmemory`（寫入 4KB 資料，`keep_error=False`）。若任何一次寫入觸發 `G_TIMEOUT_ALL`，則標記為已觸發 Assert。最後檢查 FW Assert Number 是否在 `[0xF500]` 中，並執行 HW_RESET 恢復。
   - 預期結果：至少有一個探針地址的寫入操作觸發 FW Assert，且 Assert Number 必須為 `0xF500`。這代表 SEC (Security) 模組的 SRAM 錯誤在寫入探針點時被檢測到，並觸發了安全相關的 Assert 機制 (`0xF500`)，驗證安全區域的錯誤保護與中斷機制。

7. [Step8_FIP_SRAM_Write_Read_Assert_0xF500]：
   - 動作：注入 `ErrorInjection.FIP_SRAM` 錯誤。執行與 Step 2 相同的 1GB 順序寫入與讀取比較流程。捕獲可能的 `G_TIMEOUT_ALL`。檢查 FW Assert Number 是否在 `[0xF500]` 中，並執行 HW_RESET 恢復。
   - 預期結果：韌體必須觸發 FW Assert，且 Assert Number 必須為 `0xF500`。這代表 FIP (Firmware Image Processor/Loader) 相關的 SRAM 錯誤在資料通路中被檢測到，觸發了與 SEC 模組相同的 Assert 碼 `0xF500`，驗證 FIP 模組的錯誤處理機制。