# Test Spec: UFS Flash Controller UECC Injection & Read Status Verification

## Verification Criterion (VC)
驗證韌體在針對不同儲存模式（TLC/SLC/WB/PTE）及特定邏輯區塊（VB）的最後有效頁面（LVP）與 Host Block 頁面注入不可糾正錯誤（UECC）後，硬體讀取路徑能否正確識別並回報 `ReadStatus.UECC` 狀態碼。此測試涵蓋了從正常寫入流程、VB 封閉、到針對特定物理地址（Die/Plane/Page）進行底層資料破壞的完整鏈路，確保韌體在遭遇硬體層級 ECC 失敗時，不會錯誤地返回正常資料或無效狀態，而是嚴格遵循錯誤處理機制回報 UECC。

## Test Case (TC) Checkpoints
1. [TLC_SLC_WB_PTE_UECC_Read_Status_Check]：
   - 動作：
     1. 初始化測試環境，根據 `TestMode`（TEST_TLC, TEST_SLC, TEST_WB, TEST_PTE）配置對應的 LUN 與幾何參數。若為 WB 模式，啟用 Write Booster 標誌；否則清除。
     2. 執行全區擦除（Erase all data）以重置狀態。
     3. 針對當前測試模式寫入資料，直到建立一個完整的 VB（Virtual Block）。
        - 若為 TEST_PTE：寫入超過 1 個 Pageline 的資料，計算最後有效頁面（LVP）的物理地址（PCA），並根據無效 Plane 列表調整 Die/Plane 索引。
        - 若為其他模式：建立 Closed VB，並獲取最後寫入 LBA 對應的 PCA。
     4. 針對 LVP 注入 UECC：
        - 若為 TEST_PTE：LVP 頁面索引固定為計算出的 `pageline`。
        - 若為 TEST_TLC：LVP 頁面索引強制設為 3311。
        - 若為 TEST_SLC/WB：LVP 頁面索引強制設為 1103。
        - 計算 LVP 對應的 Die 與 Plane（使用 `max_ce_plane` 與 `max_plane` 進行模運算與整除運算），並呼叫 `inject_UECC`。
     5. 針對 Host Block 頁面（即最後寫入的 PCA）注入 UECC，呼叫 `inject_UECC`。
     6. 執行直接讀取原始資料指令（`direct_read_raw_data_and_check_status`），目標地址為 Host Block 的 PCA，啟用 REH（Read Error Handling），並預期狀態為 `project_api.ReadStatus.UECC`。
   - 預期結果：
     - `direct_read_raw_data_and_check_status` 函數必須返回成功，且內部檢查的狀態碼必須嚴格等於 `project_api.ReadStatus.UECC`。
     - 這代表無論是在 TLC（3311頁）、SLC/WB（1103頁）還是 PTE 模式下，當硬體控制器在指定的物理頁面（Die/Plane/Page）檢測到無法糾正的 ECC 錯誤時，韌體層級能正確捕捉並向上層回報 UECC 狀態，而非返回錯誤代碼或正常資料。