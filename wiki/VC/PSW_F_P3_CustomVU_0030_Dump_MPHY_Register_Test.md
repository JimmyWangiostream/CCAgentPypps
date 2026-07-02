# Test Spec: UFS MPHY Register Consistency & Specification Compliance Verification

## Verification Criterion (VC)
驗證 UFS Device 在初始化完成後，MPHY (Multi-Lane PHY) 暫存器狀態的一致性與規範符合度：
1. **數據一致性驗證**：確認透過 Vendor Command (VU 0x4083) 讀取的 MPHY 暫存器資料，與直接透過 Vendor Command 讀取 SRAM 地址 `0xF8F86000` 所獲取的資料完全一致，排除讀取路徑差異導致的數據錯誤。
2. **特定欄位清零驗證**：確認在偏移量 `0x750` 至 `0x754` 的 5 個位元組區域，無論透過哪種讀取方式，其數值均為 `0x00`（此步驟在腳本中強制置零以模擬或驗證該區域應為保留/未使用狀態，或作為數據清洗步驟）。
3. **規範符合度驗證**：將 VU 0x4083 讀取的 MPHY 暫存器資料與預定義的 `project_api.MPHY_REG_CHECKS` 規範進行逐位元比對，確保所有關鍵暫存器的值落在預期範圍內，無任何偏移量（offset）的數值錯誤。

## Test Case (TC) Checkpoints
1. [MPHY_Reg_Consistency_and_Compliance_Check]：
   - 動作：
     1. 執行 `project_api.issue_4083_dump_the_MPHY_register()` 獲取 VU 0x4083 回應的 MPHY 暫存器資料（長度 2048 bytes），並儲存為 `MPHY_register_from_customVU`。
     2. 執行 `api.ufs_api.vendor_cmd.read_Xmemory(sram_address = 0xF8F86000)` 直接讀取 SRAM 中的 MPHY 暫存器資料，並儲存為 `MPHY_register_from_SRAM`。
     3. 將 `MPHY_register_from_customVU` 與 `MPHY_register_from_SRAM` 在偏移量 `0x750` 到 `0x754` 的 5 個位元組強制設為 `[0, 0, 0, 0, 0]`，並分別 dump 檔案記錄此清洗後的狀態。
     4. 比對清洗後的 `MPHY_register_from_customVU` 與 `MPHY_register_from_SRAM` 是否完全相等。
     5. 若相等，則使用 `compare_payload` 函數，將 `MPHY_register_from_customVU` 與 `project_api.MPHY_REG_CHECKS` 中的檢查項目列表進行比對，檢查每個指定 offset 的 actual value 是否等於 expected value。
   - 預期結果：
     1. `MPHY_register_from_customVU` 與 `MPHY_register_from_SRAM` 必須完全相等，若不相等則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。
     2. `compare_payload` 回傳的 `check_result` 必須為 `True`，且 `error_offset` 列表必須為空。這代表 MPHY 暫存器中所有被規範檢查的 offset 位元，其讀取值均嚴格符合 `project_api.MPHY_REG_CHECKS` 定義的預期數值。若有任何 offset 的數值不符，則拋出 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。