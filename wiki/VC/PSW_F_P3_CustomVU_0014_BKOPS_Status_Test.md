# Test Spec: UFS BKOPS Status & WriteBooster Event Mechanism Verification

## Verification Criterion (VC)
驗證 UFS 裝置在多種背景操作（BKOPS）情境下的 `bBackgroundOpStatus` (Attribute IDN 05h) 狀態機行為與 Vendor Command (VU 40DB) 的一致性，以及 WriteBooster (WB) 機制觸發 Event Alert 的邏輯：
1.  **Idle State**: 確認無背景任務時，Attribute 與 VU 40DB 均返回 0。
2.  **Write-Triggered BKOPS**: 確認在 TLC LUN 進行大量寫入後，觸發 BKOPS 且狀態碼為 1，並驗證 Attribute 與 VU 40DB 數值一致。
3.  **WB Flush & Urgent BKOPS**: 確認配置 4GB WriteBooster 並寫滿後，觸發 `urgent_bkops_en` (Event Status Bit 2) 與 `WRITEBOOSTER_EVENT_EN` (Event Status Bit 5)，此時 BKOPS 狀態應為 2；驗證 WB Flush 完成後狀態歸零且 Available WB Size 恢復為 0xA。
4.  **Refresh Triggered BKOPS**: 確認透過 VU C088 停止 Refresh 並強制觸發特定 VB 的 Refresh 作業後，BKOPS 狀態應為 3，且 Event Status Bit 2 設為 1，但 Event Alert 不應被 raise (0)。

## Test Case (TC) Checkpoints

1.  **[Case01_Idle_BKOPS_Status_Check]**：
    -   動作：讀取 `AttributeIDN.BG_OP_STATUS` (05h) 獲取 `value_from_attribute`，並透過 `project_api.issue_40DB_to_get_bkops_status()` 發送 Vendor Command 40DB 獲取 `value_from_vu`。
    -   預期結果：`value_from_attribute` 與 `value_from_vu` 必須均等於 `0`，代表裝置處於空閒狀態，無任何背景操作進行。

2.  **[Case02_Write_Triggered_BKOPS_Check]**：
    -   動作：配置 LUN 1 (TLC) 為全容量，透過 `my_40DB_vu_cmd()` 在每次 Write10 後發送 VU 40DB 指令並記錄回傳值。發送所有 Write10 指令後，輪詢檢查所有 VU 40DB 回應，確認至少有一個回應值為 `1`。
    -   預期結果：至少有一個 VU 40DB 回應值等於 `1`，代表寫入操作觸發了背景 BKOPS 機制，且裝置已進入 BKOPS 狀態 1。

3.  **[Case03_WB_Flush_Urgent_BKOPS_Check]**：
    -   動作：
        1.  配置 WriteBooster 大小為 4GB (`config_wb_size`) 並啟用 `WRITEBOOSTER_EN`。
        2.  設定 `EXC_EVENT_CONTROL` Attribute 為 `BIT2 | BIT5` (啟用 Urgent BKOPS 與 WB Event)。
        3.  向 LUN 0 寫入兩倍於 WB 容量的資料以填滿 Buffer。
        4.  讀取 `EXC_EVENT_STATUS`，確認 Bit 5 (`WRITEBOOSTER_EVENT_EN`) 為 1。
        5.  呼叫 `check_event_alert(expect_event_alert_val=1)`，確認 Read/Write(FUA)/Write/Query 指令的 `b9_device_information` 欄位均為 1 (Event Alert Raised)。
        6.  啟用 `WRITEBOOSTER_BUFFER_FLUSH_EN` 並輪詢 `BG_OP_STATUS` 直到值為 `2`。
        7.  讀取 `BG_OP_STATUS` 與 VU 40DB 並比較。
        8.  輪詢 VU 40DB 直到值為 `0`，並輪詢 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 直到值為 `0xA`。
    -   預期結果：
        -   寫滿 WB 後 `EXC_EVENT_STATUS` Bit 5 必須為 1。
        -   所有測試指令的 `b9_device_information` 必須為 1。
        -   BKOPS 狀態在 Flush 期間必須穩定為 `2`，且 Attribute 與 VU 40DB 數值一致。
        -   Flush 完成後，VU 40DB 必須歸零，且 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 必須恢復為 `0xA`。

4.  **[Case04_Refresh_Triggered_BKOPS_Check]**：
    -   動作：
        1.  配置 LUN 0 (SLC) 與 LUN 1 (TLC) 各半容量。
        2.  設定 `EXC_EVENT_CONTROL` 為 `BIT2` (Urgent BKOPS)。
        3.  向 LUN 1 寫入一個完整的 TLC VB 大小資料。
        4.  透過 `api.lba_to_pba` 取得 LBA 0 對應的 PBA，提取 `vb_number`。
        5.  發送 VU C088 參數 `StopRefresh` 停止自動 Refresh。
        6.  呼叫 `api.force_trigger_refresh_job(vb_number)` 強制觸發該 VB 的 Refresh。
        7.  輪詢 `BG_OP_STATUS` 直到值為 `3`。
        8.  讀取 `EXC_EVENT_STATUS`，確認 Bit 2 (`urgent_bkops_en`) 為 1。
        9.  呼叫 `check_event_alert(expect_event_alert_val=0)`，確認所有測試指令的 `b9_device_information` 均為 0 (No Event Alert)。
        10. 發送 VU C088 參數 `StartRefresh` 恢復自動 Refresh。
        11. 比較 `BG_OP_STATUS` 與 VU 40DB 數值。
    -   預期結果：
        -   強制 Refresh 觸發後，`BG_OP_STATUS` 必須為 `3`。
        -   `EXC_EVENT_STATUS` Bit 2 必須為 1。
        -   所有測試指令的 `b9_device_information` 必須為 0，代表 Refresh 觸發的 BKOPS 狀態 3 不會 raise Event Alert。
        -   最終 `BG_OP_STATUS` 與 VU 40DB 數值必須一致。