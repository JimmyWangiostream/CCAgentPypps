# Test Spec: PyppsLogger Logging Infrastructure & Buffer Dump Verification

## Verification Criterion (VC)
驗證 `PyppsLogger` 自定義日誌系統在 UFS 韌體測試環境中的行為一致性與數據可視化能力：Case 01 確認自定義日誌級別（FLOW, ERROR_LAST_BEHAVIOR, ERROR_FAIL_PHENOMENON, PRINT_BUFFER）的啟用狀態能正確過濾日誌輸出，確保非目標級別訊息不被記錄；Case 02 確認 `print_buffer` 函數能將二進制 `bytearray` 數據精確轉換為標準的十六進位與 ASCII 對照格式，並嚴格遵循每 16 位元組換行、每 512 位元組區塊標頭（Header）與分隔線（Separator）的輸出結構，確保測試人員能透過日誌準確還原硬體暫存器或記憶體內容。

## Test Case (TC) Checkpoints
1. [Case01_Custom_Log_Level_Filtering_Check]：
   - 動作：初始化 `PyppsLogger` 實例並透過 `set_logger` 綁定源日誌記錄器，設定日誌級別為 `logging.INFO`。分別調用 `logger.flow(FLOW, ...)`、`logger.error_lb(ERROR_LAST_BEHAVIOR, ...)`、`logger.error_fp(ERROR_FAIL_PHENOMENON, ...)` 以及 `logger.print_buffer(PRINT_BUFFER, ...)`。確認在預設 `INFO` 級別下，上述自定義級別（FLOW=35, ERROR_LAST_BEHAVIOR=41, ERROR_FAIL_PHENOMENON=42, PRINT_BUFFER=31）的日誌是否被過濾。
   - 預期結果：由於自定義級別數值（31, 35, 41, 42）均高於標準 `INFO` (20) 或需明確啟用，若未手動 `setLevel` 這些特定級別，則這些自定義日誌訊息不應出現在控制台或檔案輸出中。此步驟驗證 `isEnabledFor` 邏輯與 `addLevelName` 註冊的正確性，確保測試框架不會因日誌噪音干擾關鍵錯誤輸出。

2. [Case02_Buffer_Dump_Formatting_Check]：
   - 動作：創建一個長度為 512 位元組的 `bytearray`，其中包含連續的 ASCII 可打印字符（如 'A' 到 'Z' 重複）及非打印字符（如 0x00, 0xFF）。調用 `logger.print_buffer(buffer, block=512)`。檢查日誌輸出內容。
   - 預期結果：日誌輸出必須嚴格遵循以下格式：
     1. 首先輸出標題行：`      |  00  01 ...  0F         ASCII`。
     2. 接著輸出分隔線：`-------------------------------------------------------------------------------------------`。
     3. 數據行必須以 `%03X0` 格式開頭（例如 `00000  |`），每行顯示 16 個位元組的十六進位值（格式 `%02X`）。
     4. 每行末尾必須附加 ASCII 對照，可打印字符（32-126）顯示為原字符，不可打印字符顯示為 `.`。
     5. 由於 `block=512`，若數據長度小於 512，則僅輸出一個區塊；若大於 512，則每 512 位元組重複輸出標題與分隔線。此驗證確保測試腳本能準確記錄並展示 UFS 控制器內部緩衝區或 LBA 資料的原始狀態。