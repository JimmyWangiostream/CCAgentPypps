# Test Spec: VC-36 (13.h) Program Fail with Replacement Block Exhaustion and FW Assert Check

## Verification Criterion (VC)
驗證當快閃記憶體控制器的備用區塊池（Replacement Pool）耗盡且連續寫入觸發 Program Fail 時，韌體的錯誤處理機制：
1. **前置條件驗證**：確認系統已通過多次擦寫失敗循環，使得 `bbt.revoke_cnt` 達到最大值 `bbt.max_revoke_cnt`，且預測的下一個備用區塊（Next Replacement Block）已非空值（0xFFFF），代表備用資源即將耗盡。
2. **雙重 Program Fail 注入**：針對當前開放的 L2 VB 及其預測的下一個備用區塊，同時注入 Program Fail 錯誤（fail_type=0）。
3. **韌體 Assert 行為檢查**：在觸發寫入命令導致硬體層級 Program Fail 後，設備應進入非響應狀態（Unresponsive），並觸發特定的韌體 Assert 錯誤碼 `0x203`。
4. **狀態排除**：確認設備在 Assert 發生時**未**進入強制唯讀模式（Read-Only Mode），而是處於韌體崩潰/掛起狀態，以此區分於正常的錯誤恢復流程。

## Test Case (TC) Checkpoints

1. [Pre_Process_BBT_Exhaustion_Check]：
   - 動作：
     1. 透過 Vendor Command `VU 40C1` 讀取當前開放的 L2 VB 號碼 (`L2_vb`)。
     2. 透過 Vendor Command `VU 40DC` 讀取下一個開放的 L2 VB 號碼 (`L2_vb_next`)。
     3. 透過 Vendor Command `VU 405E` 讀取當前 Bad Block (BB) 計數 (`BB_count`)。
     4. 透過 Vendor Command `VU 40D6` 讀取預測的接下來 2 個備用區塊號碼 (`next_replacement_block_1`, `next_replacement_block_2`)。
     5. 透過 `read_fw_value` 讀取韌體內部變數 `gUfsApiStruct.ftl->bbt.max_revoke_cnt` 與 `gUfsApiStruct.ftl->bbt.revoke_cnt`。
     6. 若 `revoke_cnt` 未達 `max_revoke_cnt` 或第二個備用區塊為 `0xFFFF`，則執行 `VU C012` 對 `L2_vb_next` 注入擦寫失敗（fail_type=1），並持續寫入直到 L2 VB 切換，重複上述檢查直到滿足條件。
   - 預期結果：
     - `bbt_revoke_cnt` 必須等於 `bbtmax_revoke_cnt`。
     - `next_replacement_block_2` 必須不等於 `0xFFFF`。
     - 此步驟確保測試環境處於備用區塊池接近耗盡的臨界狀態。

2. [Step1_Dual_Block_PF_and_Assert_0x203_Check]：
   - 動作：
     1. 透過 `VU 40C1` 獲取當前 L2 VB (`L2_vb`)。
     2. 透過 `VU 40D6` 獲取下一個備用區塊號碼 (`next_replacement_block`)。
     3. 建構 `PhysicalAddressInformation`，指定兩個目標區塊：
        - Block 0: 當前 L2 VB (`L2_vb`)
        - Block 1: 下一個備用區塊 (`next_replacement_block`)
        - 設定 `fail_type=0` (Program Fail) 並透過 `VU C012` 同時注入這兩個區塊的 Program Fail。
     4. 發送標準 SCSI Write10 命令（LUN 0, LBA 0, Length 4KB, FUA=1）。
     5. 捕獲 `G_TIMEOUT_ALL` 異常，表示設備無響應。
     6. 呼叫 `api.get_fw_assert_number()` 讀取韌體 Assert 編號。
   - 預期結果：
     - 寫入命令必須導致設備超時無響應。
     - `api.get_fw_assert_number()` 返回的值必須嚴格等於 `0x203`。
     - 此結果確認韌體在備用區塊失效且無法恢復時，觸發了特定的 Assert 機制，且根據 VC 描述，此狀態下設備**未**進入 Read-Only Mode（若進入 RO 模式通常不會觸發此類 Assert 或會返回特定錯誤碼而非掛起）。