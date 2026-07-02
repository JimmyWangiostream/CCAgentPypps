# Test Spec: UFS Firmware Test Framework Initialization & Execution Logic

## Verification Criterion (VC)
驗證 UFS 測試框架（UFSTC）在執行具體測試案例前的環境初始化、硬體鏈路建立及命令序列控制邏輯：確認測試腳本能正確掃描並鎖定單一 DUT 驅動器，透過 `host_init(TESTER_POWER_OFF)` 確保硬體處於已知狀態，執行 `first_init_to_max_hs_gear` 以 LS_RESET_MODE 進行鏈路啟動並設定 26MHz 參考時脈，設定 CMD_SEQ 的 QD 限制為 SDK 版本依賴的最小值（SDK v7+ 為 64，否則為 32，且受 device_limit 32 限制），並驗證 `process()` 方法能自動反射並依序執行所有命名為 `stepN` 的抽象步驟函數。若執行過程中發生 `ApiErrorBase` 或 `CommonLibErrorBase`，需觸發 `_fail_handling_flow` 讀取 DME 中斷狀態、Host Register Table 及 FW Assert Number，並最終 Dump Track Result 以記錄失敗上下文。

## Test Case (TC) Checkpoints
1. [Init_DUT_Selection_and_Host_Init_Check]：
   - 動作：呼叫 `api.scan_tester()` 掃描可用驅動器。若發現多個驅動器，需透過 `eval(input(...))` 手動選擇目標索引；若僅有一個，則自動選取。接著初始化 `api.CommonPath` 設定報告路徑與 MP Tool 路徑，並呼叫 `api.host_init(lib.HostInit.TESTER_POWER_OFF.value)` 將 Host 端硬體初始化為電源關閉狀態，最後呼叫 `api.track_activate_and_reset()` 激活 SDK Track 功能。
   - 預期結果：`self.tester_info` 必須正確指向選定的 DUT 目標驅動器；Host 端硬體狀態必須處於 `TESTER_POWER_OFF` 狀態，確保後續鏈路啟動從零狀態開始；SDK Track 功能必須成功激活，為後續效能追蹤與錯誤記錄做準備。

2. [Link_Startup_and_QD_Limit_Config_Check]：
   - 動作：呼叫 `api.first_init_to_max_hs_gear(link_startup_mode=api.LinkStartUpMode.LS_RESET_MODE, ref_clk=api.RefClk.MHZ_26_0)` 執行 UFS 鏈路初始化。同時，透過 `_set_cmd_seq_qd_limit(device_limit=32)` 設定命令序列佇列深度限制。此函數會讀取 `sdk_ver1`，若 SDK 版本 >= 7，則 SDK 上限為 64，否則為 32；最終 QD Limit 為 `min(sdk_qd_limit, 32)`。
   - 預期結果：UFS 鏈路必須成功以 `LS_RESET_MODE` 啟動，並鎖定在最高 HS Gear 模式，參考時脈必須設定為 26.0 MHz。CMD_SEQ 的 QD 限制必須被精確設定為 32（因為 `min(64, 32)` 或 `min(32, 32)` 均為 32），確保測試期間不會因過高的並行命令數導致硬體緩衝區溢出或行為不可控。

3. [Dynamic_Step_Execution_and_Failure_Handling_Check]：
   - 動作：框架透過 `get_step_func()` 反射類別中的所有方法，篩選出名稱符合 `step\d+` 格式且為可呼叫的函數，按數字順序排序後，依序在 `process()` 中執行。若執行期間拋出 `api.ApiErrorBase` 或 `lib.CommonLibErrorBase` 異常，進入 `except` 區塊，呼叫 `_fail_handling_flow`，該流程會依次執行 `api.dme_set_interrupt_device()`、`api.dme_get_host_register_table()` 及 `api.get_fw_assert_number()` 以收集硬體中斷與韌體斷點資訊。最後在 `finally` 區塊中，呼叫 `api.dumpfile('Track_Result.bin', sdk.sdk_track_result())` 將 SDK 追蹤結果寫入檔案。
   - 預期結果：所有 `stepN` 函數必須按順序執行完畢且無異常，則 `result` 為 `PASS`。若發生異常，`result` 為 `FAIL` 且 `err_code` 為對應的異常類別名稱；`_fail_handling_flow` 必須成功讀取並記錄 DME 中斷狀態、Host Register Table 內容及 FW Assert Number，且 `Track_Result.bin` 必須成功生成，包含測試執行期間的硬體追蹤數據，以便後續分析失敗根因。