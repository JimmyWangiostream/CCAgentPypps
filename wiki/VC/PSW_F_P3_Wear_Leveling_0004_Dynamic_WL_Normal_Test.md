# Test Spec: UFS Wear Leveling & VB Selection Logic Verification (TLC/SLC/PTE)

## Verification Criterion (VC)
驗證 UFS 韌體在多種寫入情境下， Wear Leveling (WL) 演算法對 Virtual Block (VB) 的選擇邏輯與狀態遷移是否符合預期：
1. **TLC L2 建立驗證**：確認在將特定 Free Blk 的 Erase Count (EC) 強制設為低值 (666) 且其餘為 0 的情境下，韌體能正確從 `FREE_BLK_QUEUE_TLC` 中選出 EC 最低的 VB 作為 `CURRENT_L2_TLC`，並在寫入關閉後遷移至 `USED_BLK_POOL_TLC`。
2. **PTE/L1 動態選區驗證**：驗證在不同 SLC Ratio 配置下，韌體依據 `Search_selection_range_length` 限制及 EC 閾值，從對應的 Free Queue (`FREE_BLK_QUEUE_TABLE`, `FREE_BLK_QUEUE_TLC`, `FREE_BLK_QUEUE_EM1`) 中選出 EC 最低 (10) 的 VB 作為 PTE 或 L1，並驗證其狀態遷移正確性。
3. **SLC L2 建立驗證**：確認在將特定 Free Blk 的 EC 強制設為低值 (10) 且其餘為高值 (666) 的情境下，韌體能正確從 `FREE_BLK_QUEUE_EM1` 中選出 EC 最低的 VB 作為 `CURRENT_L2_EM1`，並在寫入關閉後遷移至 `USED_BLK_POOL_EM1`。

## Test Case (TC) Checkpoints

1. **[TLC_L2_Selection_and_Transition_Check]**：
   - 動作：
     1. 透過 Vendor Command `0x4098` 讀取初始 WL 資訊 (`wear_leveling_A`)。
     2. 透過 Vendor Command `0x406D` 取得排序後的 VB 列表，並從 `FREE_BLK_QUEUE_TLC` 中取出前 6 個 VB (index 0-5)。
     3. 透過 Vendor Command `0xC083` 修改 RAM 中的 EC 資料：將 index 5 的 VB EC 設為 `666`，其餘 Free Blk EC 設為 `0`。
     4. 對 TLC LUN 執行順序寫入，總大小為 `1.5 * tlc_vb_size`，觸發 L2 層級建立。
     5. 透過 `get_open_vb_info` 取得新建立的 PTE/L2 的 logical_vb (`vb`)。
     6. 再次透過 `0x4098` 讀取 WL 資訊 (`wear_leveling_B`)，比對該 `vb` 的 EC 與 VBListNum。
     7. 繼續對同一 LUN 寫入 `1 * tlc_vb_size` 資料以關閉該 VB。
     8. 透過 `lba_to_pba` 取得該 VB 的 block index，並再次透過 `0x4098` 讀取 WL 資訊，檢查其狀態。
   - 預期結果：
     - **建立前**：`wear_leveling_B.EC_data_of_VBs[vb].VBListNum` 必須等於 `FREE_BLK_QUEUE_TLC`。
     - **建立後**：`wear_leveling_B.EC_data_of_VBs[vb].VBListNum` 必須等於 `CURRENT_L2_TLC`，且選出的 `vb` 必須等於 `free_MLC[5]` (即 EC 被設為 666 的那個 VB，因其他為 0 故 666 為最小？*註：代碼邏輯中 0 < 666，故 0 為最小。若代碼意圖是選最小，則應選 EC=0 的 VB。但代碼中 `if idx < select_idx: set 666 else: set 0`。`select_idx=5`。故 index 0-4 為 666, index 5 為 0。因此 index 5 的 EC=0 是最小的。預期選出 `free_MLC[5]`*。
     - **關閉後**：該 VB 的 `VBListNum` 必須等於 `USED_BLK_POOL_TLC`。

2. **[PTE_L1_Dynamic_Selection_Check]**：
   - 動作：
     1. 根據 `ConfigCase` (EM1_larger_than_30 或 EM1_less_than_30) 配置 SLC Ratio (0.5 或 0.25)。
     2. 透過 `0x4098` 讀取初始 WL 資訊 (`wear_leveling_B`) 以獲取 `Search_selection_range_length`。
     3. 透過 `0x406D` 取得 `FREE_BLK_QUEUE_TABLE`, `FREE_BLK_QUEUE_TLC`, `FREE_BLK_QUEUE_EM1` 的 VB 列表。
     4. 透過 `0xC083` 修改 EC：
        - 所有 VB 隨機設為 100-500。
        - 在每個 Queue 中，若 index > `Search_selection_range_length`，設 EC 為 0 (排除在選區外)。
        - 在每個 Queue 中，若 index 在 `[5, 6]`，設 EC 為 `10` (作為候選最小值)。
     5. 透過 `0xC087` 將現有的 PTE 和 L1 VB 加入 Booking Queue 並刷新。
     6. 計算各 Partition 的平均 EC (`PEC_AVG_partition`)。
     7. 分別對 TLC LUN 和 SLC LUN 寫入 16KB 資料，觸發 PTE 和 L1 建立。
     8. 透過 `get_open_vb_info` 取得 `pte_vb` 和 `L1_vb`。
     9. 透過 `0x4098` 讀取 WL 資訊 (`wear_leveling_C`)，比對 `pte_vb` 和 `L1_vb` 的 `VBListNum` 與 EC 值。
   - 預期結果：
     - **VB 選擇邏輯**：
       - 若 `ConfigCase.EM1_less_than_30`：
         - `pte_vb` 應來自 `FREE_BLK_QUEUE_TABLE`。
         - `L1_vb` 應來自 `FREE_BLK_QUEUE_TLC`。
       - 若 `ConfigCase.EM1_larger_than_30`：
         - 若 `PEC_AVG[1] > PEC_AVG[0] * 1.1`，`pte_vb` 來自 `FREE_BLK_QUEUE_TABLE`，否則來自 `FREE_BLK_QUEUE_EM1`。
         - 若 `PEC_AVG[1] > PEC_AVG[2] * 1.1`，`L1_vb` 來自 `FREE_BLK_QUEUE_TLC`，否則來自 `FREE_BLK_QUEUE_EM1`。
     - **狀態遷移**：選出的 VB 在建立前的 `VBListNum` 必須等於上述對應的 `FREE_BLK_QUEUE_*`，建立後的 `VBListNum` 必須等於對應的 `CURRENT_L1` 或 `PTE_POOL` (視具體實現而定，代碼中檢查的是建立前的 Pool 和建立後的 Pool 變化，預期建立後應為 `CURRENT_L1` 或 `PTE_POOL` 相關狀態，代碼中主要驗證建立前的 Pool 正確性及選出的 VB 是否在預期的候選列表 `expect_vb` 中)。
     - **EC 值**：選出的 VB 的 EC 值應為 `10` (因其在選區內且被設為最小)。

3. **[SLC_L2_Selection_and_Transition_Check]**：
   - 動作：
     1. 透過 `0x4098` 讀取初始 WL 資訊 (`wear_leveling_A`)。
     2. 透過 `0x406D` 取得 `FREE_BLK_QUEUE_EM1` 的 VB 列表。
     3. 透過 `0xC083` 修改 EC：
        - 若 index > `Search_selection_range_length_of_static_pool`，設 EC 為 `0`。
        - 若 index == `select_idx` (5)，設 EC 為 `10`。
        - 其他設為 `666`。
     4. 對 SLC LUN 執行順序寫入，總大小為 `1.5 * slc_vb_size`，觸發 SLC L2 建立。
     5. 透過 `get_open_vb_info` 取得 `vb`。
     6. 透過 `0x4098` 讀取 WL 資訊 (`wear_leveling_B`)，比對該 `vb` 的 EC 與 VBListNum。
     7. 繼續對同一 LUN 寫入 `1 * slc_vb_size` 資料以關閉該 VB。
     8. 透過 `lba_to_pba` 取得該 VB 的 block index，並再次透過 `0x4098` 讀取 WL 資訊，檢查其狀態。
   - 預期結果：
     - **建立前**：`wear_leveling_B.EC_data_of_VBs[vb].VBListNum` 必須等於 `FREE_BLK_QUEUE_EM1`。
     - **建立後**：`wear_leveling_B.EC_data_of_VBs[vb].VBListNum` 必須等於 `CURRENT_L2_EM1`，且選出的 `vb` 必須等於 `free_SLC[5]` (即 EC 被設為 10 的那個 VB，因 10 < 666 且 10 < 0? *註：代碼中 index > range 設為 0。若 index 5 在 range 內，則 EC=10。若 range 內有其他 VB 設為 0，則 0 < 10。需確認 `select_idx` 是否在 range 內。代碼邏輯：`if idx > range: set 0 elif idx == select_idx: set 10 else: set 666`。若 `select_idx` (5) <= range，則 EC=10。若 range 內有其他 index (如 0-4) 設為 666，則 10 是最小的。若 range 外設為 0，則 0 < 10。因此，若 `select_idx` 在 range 內，且 range 內其他 VB 為 666，則 `select_idx` 的 VB (EC=10) 是 range 內最小的。但 range 外的 VB (EC=0) 更小。韌體 WL 演算法通常只在 `Search_selection_range` 內尋找。因此，預期選出的是 range 內 EC 最小的 VB，即 `free_SLC[5]` (EC=10)。
     - **關閉後**：該 VB 的 `VBListNum` 必須等於 `USED_BLK_POOL_EM1`。