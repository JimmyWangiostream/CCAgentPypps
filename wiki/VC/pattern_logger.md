# Test Spec: PyppsLogger Custom Logging Infrastructure Validation

## Verification Criterion (VC)
驗證 `PyppsLogger` 自定義日誌框架在特定日誌級別（FLOW, ERROR_LAST_BEHAVIOR, ERROR_FAIL_PHENOMENON, PRINT_BUFFER）下的觸發機制與輸出格式規範：
1. **級別過濾與擴展日誌寫入**：確認當啟用 `extra_dump=True` 時，日誌系統會動態初始化 `FileHandler` 並寫入帶有時間戳記的額外日誌文件，且該文件僅接收標記為 `extra_log=True` 的記錄。
2. **Buffer 十六進制格式化**：確認 `print_buffer` 方法能將 `bytearray` 數據精確轉換為標準的十六進制轉儲格式（每行 16 字節，包含偏移量、Hex 值及 ASCII 可打印字符），並嚴格遵循 `PRINT_BUFFER` 級別過濾。
3. **自定義日誌級別註冊**：確認 `set_logger` 函數能正確將自定義整數級別（35, 41, 42, 31）映射為對應的字符串標籤（'FLOW', 'ERROR_LAST_BEHAVIOR' 等）並應用於全局日誌實例。

## Test Case (TC) Checkpoints

1. [Case01_ExtraLog_FileInitialization_Check]：
   - 動作：調用 `set_to_debug_mode_logger` 初始化日誌環境，指定 `log_path` 與 `ptn_name`。隨後調用 `logger.flow` 或 `logger.info` 並設置 `extra_dump=True`。檢查 `_extra_handler` 全局變量是否被實例化，並驗證生成的額外日誌文件路徑是否符合 `{log_path}/{ptn_name}_{timestamp}_additional.log` 的命名規則。
   - 預期結果：`_extra_handler` 不為 None；額外日誌文件成功創建；該文件中的日誌記錄必須包含 `extra_log` 過濾器允許的標記，且格式由 `_extra_cfg` 中定義的 formatter 控制。

2. [Case02_BufferHexDumpFormat_Check]：
   - 動作：構建一個長度為 32 字節的 `bytearray`，其中包含可打印 ASCII 字符（如 'A' 到 'Z'）與不可打印字符（如 0x00, 0xFF）。調用 `logger.print_buffer(buffer, block=512, extra_dump=False)`，並確保 `PRINT_BUFFER` (31) 級別已啟用。捕獲日誌輸出內容。
   - 預期結果：輸出必須包含標題行 `      |  00  01 ...  0F         ASCII` 與分隔線。數據行必須嚴格遵循 `%03X0  |` 偏移格式（例如 `00000  |`），每行顯示 16 個字節的 Hex 值（格式 `%02X`），並在行尾附加 ASCII 表示（可打印字符保留原樣，不可打印字符替換為 '.'）。最終行必須正確關閉並記錄。

3. [Case03_CustomLevelMapping_Check]：
   - 動作：調用 `set_logger` 將源日誌級別應用到全局 `logger`。檢查 `logging` 模塊的內部級別映射表，確認整數 35 映射為 'FLOW'，41 映射為 'ERROR_LAST_BEHAVIOR'，42 映射為 'ERROR_FAIL_PHENOMENON'，31 映射為 'BUFFER'。
   - 預期結果：`logging.getLevelName(35)` 返回 'FLOW'；`logging.getLevelName(41)` 返回 'ERROR_LAST_BEHAVIOR'；`logging.getLevelName(42)` 返回 'ERROR_FAIL_PHENOMENON'；`logging.getLevelName(31)` 返回 'BUFFER'。全局 `logger` 的 handlers 必須與源日誌一致，且級別設置正確。

4. [Case04_ExtraLogFilterIsolation_Check]：
   - 動作：在 `extra_dump=True` 的情境下，分別調用 `logger.flow`（級別 FLOW=35）與 `logger.info`（級別 INFO=20）。確保兩者都觸發了 `_ensure_extra_handler`。檢查額外日誌文件中是否**僅**包含被標記為 `extra_log=True` 的記錄，並排除任何未設置該標記的普通日誌。
   - 預期結果：額外日誌文件內容與主日誌文件內容分離；額外日誌文件僅包含顯式請求 dump 的 FLOW 或 INFO 級別記錄，證明 `ExtraLogFilter` 正確過濾了非 dump 請求的日誌。