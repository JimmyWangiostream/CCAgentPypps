# Test Spec: UFS FW CIS Block Information Verification via Vendor Command 40B9

## Verification Criterion (VC)
驗證 UFS 韌體透過 Vendor Command 0x40B9 回傳的 CIS (Code Information Structure) 區塊資訊與 FTL (Flash Translation Layer) 內部狀態的一致性：
1. **物理位置一致性**：確認 Vendor Cmd 回傳的 CIS 區塊物理地址（CE, Block, Plane）與 FTL 結構體 `gUfsApiStruct.ftl->addr_rule.geometry` 中定義的 `CISCode1` 及 `CISCode2` 完全吻合。
2. **隱藏區塊映射與擦寫計數**：確認 Vendor Cmd 回傳的 CIS0/CIS1 擦寫計數（EC Count）與 FTL 隱藏區域（Hidden Area）中對應物理區塊的實際擦寫次數一致；同時確認 CIS2/CIS3 因未使用或壞塊標記，其 EC Count 應為 `0xFFFFFFFF`。
3. **狀態標記驗證**：確認 CIS0/CIS1 非壞塊（值為 0），而 CIS2/CIS3 為壞塊或未初始化狀態（值為 `0xFF`）。
4. **載入銀行與頁面範圍**：確認 Vendor Cmd 回傳的 `cis_copy_used_to_load_FE_bank` 與 `cis_copy_used_to_load_DM_bank` 狀態與全局變數 `gbyUseCode` 一致；並驗證韌體影像（FW Image）的起始/結束頁面索引（Page Start/End Index）以及 Bank 的頁面範圍與 FTL 結構體 `gUfsApiStruct.ftl->fvl[0]->fpl` 中的定義完全匹配。

## Test Case (TC) Checkpoints
1. [CIS_Physical_Address_Verification]：
   - 動作：發送 Vendor Command 0x40B9 獲取 CIS Block 資訊，讀取回傳結構體中的 `physical_blk_number_of_cis_vb`、`die_number_of_the_STC_copy`、`plane_number_of_the_STC_copy`。同時透過 `api.read_fw_value` 讀取 FTL 內部結構 `gUfsApiStruct.ftl->addr_rule.geometry` 下的 `CISCode1` 的 CE、Block、Plane 欄位。
   - 預期結果：Vendor Cmd 回傳的 `physical_blk_number_of_cis_vb` 必須等於 FTL 結構中的 `CISCode1.Block.value`；`die_number_of_the_STC_copy` 必須等於 `CISCode1.CE.value`；`plane_number_of_the_STC_copy` 必須等於 `CISCode1.Plane.value`。這證實了韌體報告的物理區塊映射與內部 FTL 配置一致。

2. [CIS_Bad_Block_Status_Check]：
   - 動作：讀取 Vendor Command 0x40B9 回傳結構體中的 `if_cis0_is_bad_blk`、`if_cis1_is_bad_blk`、`if_cis2_is_bad_blk`、`if_cis3_is_bad_blk`。
   - 預期結果：`if_cis0_is_bad_blk` 與 `if_cis1_is_bad_blk` 必須等於 `0`（代表正常區塊）；`if_cis2_is_bad_blk` 與 `if_cis3_is_bad_blk` 必須等於 `0xFF`（代表壞塊或未使用狀態）。這驗證了韌體正確識別了 CIS 複製品的健康狀態。

3. [CIS_EC_Count_Hidden_Area_Mapping]：
   - 動作：
     1. 從 `flash_setting_buffer` 偏移量 2284 開始，每 4 位元組讀取 8 個隱藏區塊的擦寫計數（Hidden Block EC），存入陣列 `erase_cnt_for_hidden_physical_block`。
     2. 讀取 FTL 隱藏區域地址陣列 `gUfsApiStruct.ftl->hidden_area.address[0..7]`，解析每個條目的 Block (`value & 0x1FFF`) 與 CE (`value >> 13`)。
     3. 計算 CIS0 的物理位置：Block = `(CISCode1.Block.value << 3) + CISCode1.Plane.value`，CE = `CISCode1.CE.value`。
     4. 計算 CIS1 的物理位置：Block = `(CISCode2.Block.value << 3) + CISCode2.Plane.value`，CE = `CISCode2.CE.value`。
     5. 在隱藏區域陣列中尋找與 CIS0/CIS1 物理位置匹配的索引 `cis0_index` 與 `cis1_index`。
     6. 讀取 Vendor Cmd 回傳的 `cis0_ec_count` 與 `cis1_ec_count`。
   - 預期結果：
     - `cis0_ec_count` 必須等於 `erase_cnt_for_hidden_physical_block[cis0_index]`。
     - `cis1_ec_count` 必須等於 `erase_cnt_for_hidden_physical_block[cis1_index]`。
     - `cis2_ec_count` 與 `cis3_ec_count` 必須等於 `0xFFFFFFFF`。
     這證實了 Vendor Cmd 報告的擦寫計數準確對應到 FTL 隱藏區域中特定物理區塊的硬體計數器。

4. [FE_DM_Bank_Load_Status_Check]：
   - 動作：讀取 FTL 全局變數 `gbyUseCode`，將其轉換為布林值（若值為 3 則為 True，否則 False）。讀取 Vendor Cmd 回傳的 `cis_copy_used_to_load_FE_bank` 與 `cis_copy_used_to_load_DM_bank`。
   - 預期結果：Vendor Cmd 回傳的 `cis_copy_used_to_load_FE_bank` 與 `cis_copy_used_to_load_DM_bank` 必須都等於 `gbyUseCode == 3` 的結果。這驗證了韌體正確報告了當前用於載入 Frontend (FE) 與 Data Management (DM) 銀行的是哪一個 CIS 複製品。

5. [FW_Image_Page_Range_Verification]：
   - 動作：
     1. 讀取 FTL 結構 `gUfsApiStruct.ftl->fvl[0]->fpl->code_start_page` 作為 `code_start_page`。
     2. 讀取 FTL 結構 `gby_code_bank_count` 作為 `value`。
     3. 計算預期值：
        - `fw_image_page_start_index` = `code_start_page`
        - `fw_image_page_end_index` = `code_start_page + 12 - 1`
        - `bank_page_start_index` = `code_start_page + 12`
        - `bank_page_end_index` = `code_start_page + 12 + value`
     4. 讀取 Vendor Cmd 回傳對應的頁面索引欄位。
   - 預期結果：
     - `fw_image_page_start_index` 必須等於 `code_start_page`。
     - `fw_image_page_end_index` 必須等於 `code_start_page + 11`。
     - `bank_page_start_index` 必須等於 `code_start_page + 12`。
     - `bank_page_end_index` 必須等於 `code_start_page + 12 + value`。
     這驗證了 Vendor Cmd 正確反映了韌體影像與 Bank 在 Flash 頁面上的邏輯分佈範圍。