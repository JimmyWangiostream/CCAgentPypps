# Test Spec: UFS Vendor Command 4022 NAND Feature Register Default State Verification

## Verification Criterion (VC)
驗證 UFS 裝置透過 Vendor Command 0x4022 讀取 NAND Flash 特定 Feature Address (0xEB) 時，不同 CE (Channel/Engine) 數量下的硬體預設值一致性與正確性：
1. 當 CE 數量不等於 4 時，驗證所有 CE 的 P1-P4 欄位均為預設零值 (0x00000000)，確認無特殊配置干擾。
2. 當 CE 數量等於 4 時，驗證每個 CE 的 P1-P4 欄位符合特定硬體定義的預設特徵碼（P1 為 0x81/0x89/0x91/0x99，P2 為 0x14，P3 為 0x6E/0x2E，P4 為 0x00），確認 NAND 控制器與 Flash 介面的初始化狀態符合規格書定義。

## Test Case (TC) Checkpoints
1. [CE_Count_Non4_DefaultZero_Check]：
   - 動作：獲取 Flash 設定中的 CE 總數 (`self.CE`)，若 `self.CE != 4`，則針對範圍 `0` 至 `self.CE-1` 的每個 CE，發送 Vendor Command 0x4022 並指定 Feature Address 為 `0xEB`。解析返回的 Data Payload，提取 P1, P2, P3, P4 四個欄位的數值。
   - 預期結果：所有 CE 的 P1, P2, P3, P4 欄位數值必須嚴格等於 `0x00000000`。若任何欄位不為零，則判定為測試失敗，代表 NAND 特性寄存器未處於標準復位或預設狀態。

2. [CE_Count_4_SpecificFeatureCode_Check]：
   - 動作：若 `self.CE == 4`，則針對 CE 0, 1, 2, 3 分別發送 Vendor Command 0x4022 並指定 Feature Address 為 `0xEB`。解析返回的 Data Payload，並針對每個 CE 的 P1-P4 欄位進行精確比對。
   - 預期結果：
     - **CE 0**：P1=`0x81`, P2=`0x14`, P3=`0x6E`, P4=`0x00`。
     - **CE 1**：P1=`0x89`, P2=`0x14`, P3=`0x2E`, P4=`0x00`。
     - **CE 2**：P1=`0x91`, P2=`0x14`, P3=`0x2E`, P4=`0x00`。
     - **CE 3**：P1=`0x99`, P2=`0x14`, P3=`0x2E`, P4=`0x00`。
     任何欄位數值與上述預期不符，即代表 NAND 控制器初始化異常或 Flash 設備響應錯誤。