# Test Spec: UFS Flash Randomizer & ECC Counter Dependency Verification

## Verification Criterion (VC)
驗證 UFS 控制器在直接 NAND 模式（Direct NAND Mode）下，資料隨機化（Randomizer/Scrambler）機制與虛擬區塊擦除計數器（VB Erase Count, EC）的依賴關係：
1. **隨機化啟用驗證**：確認當 Scramble_Enable=0 與 Scramble_Enable=1 時，讀取的原始資料（Raw Data）在 Payload 與 Spare Area 必須完全不同，證明硬體隨機化引擎正常運作。
2. **EC 依賴性驗證（週期性）**：確認隨機化種子（Seed）基於 EC 值。當對同一物理位置寫入相同資料，但 EC 值增加 1 時，讀回資料應不同；當 EC 值增加 8 時，讀回資料應與 EC 增加 1 時相同（暗示隨機化週期或模數為 8）。
3. **EC 恢復驗證**：確認將 EC 值重置回原始值後，再次寫入相同資料，讀回資料應與初始寫入（EC 為原始值時）完全一致，證明 EC 是隨機化狀態的唯一決定因素。

## Test Case (TC) Checkpoints
1. [Case01_Randomizer_Engine_Check]：
   - 動作：針對指定 LUN（依 Case 類型為 SLC/TLC/WB/PTE/LOG）寫入 1 個 VB 大小的資料。透過 Vendor Command (VUC 420D 或 4051) 取得該 VB 的 PCA（Physical Cell Address，包含 Die, Plane, Block, Page）。接著發送 Vendor Command 4060 讀取原始資料，分別設定 `Scramble_Enable=0` 與 `Scramble_Enable=1`（`SLC_Enable` 依記憶體類型設定，`ECC_Enable=1`）。比較兩次讀取結果的 Payload 區段（前 16KB）與 Spare Area 區段（偏移 0x4004 後的 64 位元組）。
   - 預期結果：`Scramble_Enable=0` 與 `Scramble_Enable=1` 讀取的資料在 Payload 與 Spare Area 必須完全不同（`compare_payload` 回傳 False）。若相同則觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`，證明硬體隨機化引擎在啟用時確實改變了資料位元。

2. [Case02_EC_Dependency_Increment_Check]：
   - 動作：
     1. 讀取當前 VB 的 EC 值（透過 VUC 4097）。
     2. 發送 VUC 4060 讀取初始原始資料（記為 `Data_Initial`，Scramble=0）。
     3. 發送 VUC 40F6 擦除該 VB。
     4. 發送 VUC C083 將 RAM 中的 EC 值設定為 `EC_Initial + 1`。
     5. 發送 VUC C060 寫入與初始寫入相同的 Payload 資料（從 `Data_Initial` 提取 metadata 並填入 0x4000-0x4040 欄位）。
     6. 發送 VUC 4060 讀取寫入後的資料（記為 `Data_EC+1`）。
     7. 比較 `Data_Initial` 與 `Data_EC+1`。
   - 預期結果：`Data_Initial` 與 `Data_EC+1` 必須不同。這證明隨機化狀態隨 EC 計數器的改變而改變，即使寫入的邏輯資料相同。

3. [Case03_EC_Dependency_Periodicity_Check]：
   - 動作：
     1. 發送 VUC 40F6 擦除該 VB。
     2. 發送 VUC C083 將 RAM 中的 EC 值設定為 `EC_Initial + 8`。
     3. 發送 VUC C060 寫入與初始寫入相同的 Payload 資料。
     4. 發送 VUC 4060 讀取寫入後的資料（記為 `Data_EC+8`）。
     5. 比較 `Data_EC+1`（來自 Case02）與 `Data_EC+8`。
   - 預期結果：`Data_EC+1` 與 `Data_EC+8` 必須完全相同。這驗證了隨機化算法基於 EC 的週期性（Periodicity），即 EC 模 8 的結果決定了隨機化種子，`1 % 8 == 9 % 8` 的邏輯在此得到硬體層面的驗證。

4. [Case04_EC_Recovery_Check]：
   - 動作：
     1. 發送 VUC 40F6 擦除該 VB。
     2. 發送 VUC C083 將 RAM 中的 EC 值重置為 `EC_Initial`。
     3. 發送 VUC C060 寫入與初始寫入相同的 Payload 資料。
     4. 發送 VUC 4060 讀取寫入後的資料（記為 `Data_Recovered`）。
     5. 比較 `Data_Initial`（來自 Case01/02 的初始讀取）與 `Data_Recovered`。
   - 預期結果：`Data_Initial` 與 `Data_Recovered` 必須完全相同。這證明只要 EC 值恢復到原始狀態，硬體隨機化狀態即完全復原，確保資料一致性與可預測性。