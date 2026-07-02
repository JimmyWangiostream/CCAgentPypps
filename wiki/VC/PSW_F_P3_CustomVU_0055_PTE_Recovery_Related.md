# Test Spec: UFS PTE Recovery Vendor Command (0x40F5) Sub-opcode Validation

## Verification Criterion (VC)
驗證 Vendor Command `0x40F5` (PTE Recovery) 在不同 Sub-opcode (1, 2, 3, 4, 5, 6) 下的硬體行為與韌體狀態機轉換邏輯：
- **Sub-opcode 1 & 2**：驗證 PTE 對 VB 狀態的讀取正確性。針對 Free VB (Group 27) 應回傳狀態碼 `1` (Free)，針對 Used VB (Group 17) 應回傳狀態碼 `2` (Used)。
- **Sub-opcode 3 & 4**：驗證 PTE 對無效/隨機 VB 索引的邊界檢查與錯誤處理。針對任意隨機 VB 索引，應回傳狀態碼 `1` (代表 Invalid/Not Found 或特定錯誤標記，依此腳本預期)。
- **Sub-opcode 5**：驗證 PTE 對特定 VB 的查詢機制。針對已寫入資料的 Used VB，應回傳狀態碼 `0` (代表 Valid/Found)；針對所有 VB 列表遍歷，應能正確識別出至少一個狀態為 `1` 的 VB (此處邏輯與 Sub-opcode 1/2 的定義需對照韌體實作，腳本預期為 `1`)。
- **Sub-opcode 6**：驗證 PTE 的 VB 狀態遷移機制 (Used -> Free)。針對指定的 Used VB 執行 Recovery 後，該 VB 必須從 Used List (Group 17) 移除並加入 Free List (Group 27)，且該 LWP 的資料應被標記為 UECC (Bit 4 Set)，代表資料無效化。

## Test Case (TC) Checkpoints

1. [SubOp1_FreeVB_Status_Check]：
   - 動作：透過 `get_target_vb_list(27)` 取得 Free VB 列表，取出第一個 Free VB 索引。呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=1, vb_index=free_vb)`。
   - 預期結果：回傳的 payload 第一個欄位 (`payload[0]`) 必須等於 `1`。代表 PTE 正確識別該 VB 為 Free 狀態。

2. [SubOp1_UsedVB_Status_Check]：
   - 動作：透過 `get_target_vb_list(17)` 取得 Used VB 列表，取出第一個 Used VB 索引。呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=1, vb_index=used_vb)`。
   - 預期結果：回傳的 payload 第一個欄位 (`payload[0]`) 必須等於 `2`。代表 PTE 正確識別該 VB 為 Used 狀態。

3. [SubOp2_FreeVB_Status_Check]：
   - 動作：透過 `get_target_vb_list(27)` 取得 Free VB 列表，取出第一個 Free VB 索引。呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=2, vb_index=free_vb)`。
   - 預期結果：回傳的 payload 第一個欄位 (`payload[0]`) 必須等於 `1`。代表 PTE 正確識別該 VB 為 Free 狀態。

4. [SubOp2_UsedVB_Status_Check]：
   - 動作：透過 `get_target_vb_list(17)` 取得 Used VB 列表，取出第一個 Used VB 索引。呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=2, vb_index=used_vb)`。
   - 預期結果：回傳的 payload 第一個欄位 (`payload[0]`) 必須等於 `2`。代表 PTE 正確識別該 VB 為 Used 狀態。

5. [SubOp3_RandomVB_Boundary_Check]：
   - 動作：產生一個隨機整數 `random.randint(0x1, 0xFFFFFFFF)` 作為 VB 索引。呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=3, vb_index=random_vb)`。
   - 預期結果：回傳的 payload 第一個欄位 (`payload[0]`) 必須等於 `1`。代表 PTE 對無效或超出範圍的 VB 索引進行了正確的邊界檢查與錯誤處理。

6. [SubOp4_RandomVB_Boundary_Check]：
   - 動作：產生一個隨機整數 `random.randint(0x1, 0xFFFFFFFF)` 作為 VB 索引。呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=4, vb_index=random_vb)`。
   - 預期結果：回傳的 payload 第一個欄位 (`payload[0]`) 必須等於 `1`。代表 PTE 對無效或超出範圍的 VB 索引進行了正確的邊界檢查與錯誤處理。

7. [SubOp5_UsedVB_Query_Check]：
   - 動作：寫入 4KB 資料至 LUN 0 以建立一個 Used VB，並透過 `ori_lba_to_pba` 取得其對應的 Block Index (`target_used_vb`)。呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=5, vb_index=target_used_vb)`。
   - 預期結果：回傳的 payload 第一個欄位 (`payload[0]`) 必須等於 `0`。代表 PTE 成功查詢到該 Used VB 並確認其有效性。

8. [SubOp6_VB_Transition_UECC_Check]：
   - 動作：
     1. 寫入 4KB 資料至 LUN 0 建立 Used VB (`target_vb`)。
     2. 使用 `ori_lba_to_pba` 取得該 VB 的 PBA (Block, CE, Plane, Page)。
     3. 透過 Vendor Direct Write 在該 PBA 寫入全 0x00 資料，並在另一個 Plane 寫入全 0xFF 資料以確保硬體層面的資料狀態。
     4. 呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=6, vb_index=target_vb)` 觸發 PTE Recovery。
     5. 使用 `vendor_cmd.direct_read` 讀取該 PBA 的資料，並檢查 offset `128 + DATA_SIZE_4K_BYTE` 處的 `status_of_blk` 欄位。
     6. 檢查 `is_bit4_set(status_of_blk)` 是否為 True。
   - 預期結果：
     - `status_of_blk` 的第 4 bit (Bit 4) 必須被設定 (Set)，代表該 LWP 資料已被標記為 UECC (Unrecoverable ECC) 或無效狀態。
     - 這驗證了 Sub-opcode 6 不僅改變了 VB 的邏輯狀態，還確保了底層 Flash 資料被無效化。

9. [SubOp6_VB_List_Migration_Check]：
   - 動作：
     1. 在執行 Sub-opcode 6 之前，記錄 `target_vb` 在 Used VB List (Group 17) 中。
     2. 執行 `issue_40F5_to_PTE_Recovery(sub_opcode=6, vb_index=target_vb)`。
     3. 重新呼叫 `get_target_vb_list(17)` 獲取新的 Used VB 列表，確認 `target_vb` **不在**列表中。
     4. 重新呼叫 `get_target_vb_list(27)` 獲取新的 Free VB 列表，確認 `target_vb` **在**列表中。
   - 預期結果：
     - `target_vb` 必須從 Used List (Group 17) 中移除。
     - `target_vb` 必須出現在 Free List (Group 27) 中。
     - 這驗證了 PTE 的 VB 狀態遷移機制正確將 VB 從 Used 狀態轉換為 Free 狀態。

10. [SubOp5_Global_VB_Scan_Check]：
    - 動作：
      1. 獲取所有 VB 列表 (`get_vb_list`)。
      2. 遍歷每個 VB，呼叫 `issue_40F5_to_PTE_Recovery(sub_opcode=5, vb_index=vb)`。
      3. 檢查回傳的 `payload[0]`。
    - 預期結果：
      - 必須在遍歷過程中找到至少一個 VB，其回傳的 `payload[0]` 等於 `1`。
      - 這驗證了 PTE 能夠正確掃描並識別出系統中存在狀態為 `1` (在此腳本邏輯中對應 Free 或特定標記) 的 VB，確保 VB 列表的一致性。