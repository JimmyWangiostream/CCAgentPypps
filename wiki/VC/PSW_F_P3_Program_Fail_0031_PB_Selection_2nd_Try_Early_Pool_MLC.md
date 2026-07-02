# Test Spec: VC-55 (13.f) Program Fail Replacement Logic Verification

## Verification Criterion (VC)
驗證 UFS 韌體在遭遇 Program Fail (PF) 時的 Bad Block Table (BBT) 更新機制與替換區塊選擇邏輯：
1. **Early Replacement Pool (Normal Area)**：當寫入目標區塊（L2 VB）發生 PF，且韌體在 Early Replacement Pool 中找到可用替換區塊並成功寫入時，BBT 應正確標記原目標區塊與替換區塊為 Bad Block，且韌體不應 Assert（崩潰）。
2. **Late Replacement Pool (Shared/ICS)**：若韌體選擇 Late Replacement Pool（通常用於 ICS 或靜態區塊共享情境），成功寫入後應強制進入 Read-Only Mode。
本測試腳本主要驗證第一種情境（Early Replacement Pool），確認在注入 L2 區塊與預測替換區塊的 PF 後，BBT 計數增加 2，且這兩個區塊均被正確記錄在 BBT 中。

## Test Case (TC) Checkpoints
1. [PreProcess_FillToFirstEmptyMLC]：
   - 動作：執行迴圈寫入 LBA 0 開始的資料（每次 16 Blocks），持續直到 `get_open_vb_info` 返回的 `TLC_L2.first_empty_physical_page` 大於等於 1620。此步驟旨在消耗正常寫入區域，確保後續測試能觸發替換區塊的分配邏輯。
   - 預期結果：系統正常完成所有 Write10 指令，無錯誤回報，且當前 Open VB 的第一個空閒物理頁面指標已推進至 MLC 區域的特定閾值（>= 1620）。

2. [TC01_EarlyReplacement_PF_BBT_Update_Check]：
   - 動作：
     1. 獲取當前 Open VB 資訊，提取 `logical_VB` 與 `first_empty_physical_page`，並透過特定公式（根據物理頁面範圍 <1620, <1652, <3308 等）計算對應的 `logical_page`。
     2. 透過 VU 0x405E 讀取初始 Bad Block Count (`BB_count`)。
     3. 透過 VU 0x40D6 查詢 CE 0, Plane 0 的 Early Replacement Pool (`pool_type=1`) 下一個預測替換區塊 (`next_replacement_block`)。
     4. 透過 VU 0xC012 注入 Program Fail：
        - 目標 1：當前 L2 區塊 (`logical_VB`, `logical_page`)。
        - 目標 2：預測的替換區塊 (`next_replacement_block`, page 0)。
        - 失敗類型 (`fail_type`) 設為 3。
     5. 執行 Write10 指令（寫入最大長度 `WRITE_10_MAX_BLOCK_LEN`），並設定 `skip_response_check=True` 以允許指令返回錯誤狀態而不中斷腳本。
     6. 透過 VU 0x4013 讀取 BE (Block Error) Fail Status。
     7. 再次透過 VU 0x405E 讀取新的 Bad Block Count (`BB_count_new`) 並解析 BBT 數據。
   - 預期結果：
     1. **BBT 計數驗證**：`BB_count_new` 必須嚴格等於 `BB_count + 2`。這證明韌體正確識別了兩個失效區塊（原目標區塊與替換區塊）並將其標記為 Bad。
     2. **BBT 內容驗證**：解析後的 BBT 數據列表中，必須包含以下兩個實體地址資訊：
        - 原 L2 區塊：CE=`info.BlockInfoList_0_die`, Plane=`info.BlockInfoList_0_plane`, Block=`info.BlockInfoList_0_block`。
        - 替換區塊：CE=`info.BlockInfoList_1_die`, Plane=`info.BlockInfoList_1_plane`, Block=`info.BlockInfoList_1_block`。
     3. **系統穩定性**：整個流程中韌體未發生 Assert 或崩潰，證明在 Early Replacement Pool 情境下，韌體能正確處理雙重 PF 並更新內部結構。