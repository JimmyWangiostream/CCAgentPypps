# Test Spec: UFS Vendor Command SRAM Read/Write Integrity & Memory Map Validation

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command (VC) 對內部 SRAM/記憶體區域的直接存取能力與資料完整性：
1. **寫入驗證**：確認 VC 0xC0F0 能正確將特定資料 (0x5A5A5A5A) 寫入指定的保留測試區塊 (0x7FDA8000)，並透過讀取確認資料無損。
2. **讀取完整性與記憶體映射驗證**：確認 VC 0x4027 能正確讀取多個關鍵記憶體區域（ICCM, ROM, COP0, MRAM, DCCM）的起始、中間及結束地址，確保韌體與硬體記憶體映射 (Memory Map) 在關閉電源節省模式 (Suspend) 後仍可被外部工具正確訪問，且讀回資料格式符合預期（無報錯或資料截斷）。

## Test Case (TC) Checkpoints
1. [Case01_Disable_Suspend_Write_Read_Back_Check]：
   - 動作：
     1. 透過 `api.HwSetting` 將 `POWER_SAVING_CTRL_ENABLE` 欄位設定為 `0x3A`，強制關閉裝置的 Suspend 功能，確保在後續直接記憶體存取時裝置不會進入低功耗狀態導致通訊中斷。
     2. 針對寫入測試區塊 `0x7FDA8000` (Reserved block for test)，透過 Vendor Command 0xC0F0 寫入 4 位元組資料 `0x5A5A5A5A`。
     3. 立即透過 Vendor Command 0x4027 讀取同一地址 `0x7FDA8000` 的資料。
     4. 比對讀回資料的前 4 位元組是否與寫入資料 `0x5A5A5A5A` 完全一致。
   - 預期結果：讀回資料必須等於 `0x5A5A5A5A`；若不相等則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。此步驟驗證 VC 0xC0F0 寫入機制與 VC 0x4027 讀取機制在特定保留區塊的資料一致性。

2. [Case02_Memory_Map_Read_Integrity_Check]：
   - 動作：
     1. 遍歷預定義的讀取記憶體區段列表 (`read_ram_segments`)，涵蓋 ICCM+ROM (`0x00000000`), COP0 (`0x4C100000`, `0x4C200000`), MRAM (`0x7FDA4000`), 以及部分可訪問的 DCCM (`0x80000000`, `0x8001CE00`)。
     2. 對每個區段，計算並測試三個關鍵地址：區段起始地址 (`start_addr`)、區段中間對齊地址 (`mid_addr`)、區段結束地址 (`end_addr`)。
     3. 對每個測試地址，透過 Vendor Command 0x4027 讀取 4 位元組資料。
     4. 記錄並列印每個地址讀取的十六進位資料值。
   - 預期結果：所有指定的記憶體地址讀取操作必須成功返回資料，無通訊錯誤或逾時；讀回資料應反映該記憶體區域的實際內容（如韌體代碼、配置數據或隨機值），證明在關閉 Suspend 狀態下，UFS 控制器允許外部主機透過 Vendor Command 訪問這些關鍵硬體記憶體區域，且記憶體映射範圍符合預期。