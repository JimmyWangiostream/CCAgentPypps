# Test Spec: RPMB Secure Erase & Password Authentication Logic Verification

## Verification Criterion (VC)
驗證 UFS 裝置中 RPMB (Replay Protected Memory Block) 區域的密碼管理、資料完整性保護以及安全擦除機制：
1. **密碼狀態機驗證**：確認在無密碼設定狀態下，執行 Clear 操作應返回錯誤碼 `1`；在已設定密碼狀態下，執行 Clear 操作應返回成功碼 `0`；設定密碼後查詢狀態應返回 `1`。
2. **資料寫入與讀取驗證**：確認在 RPMB Region 0 寫入特定資料後，讀取 payload 前 4KB (Byte 228-484) 不應全為 `0x00`，證明資料已正確寫入 Flash。
3. **安全擦除觸發與完成驗證**：確認使用正確密碼觸發 RPMB Erase (Command 0) 後，查詢 Erase Status (Command 1) 應從非完成狀態輪詢至 `1` (或 `2`)，代表韌體已執行物理層級的區塊清除。
4. **擦除後資料驗證**：確認 Erase 完成後，讀取相同 Region 的 payload 應全為 `0x00`，證明安全擦除機制生效。
5. **錯誤密碼防護驗證**：確認使用錯誤密碼 (Password - 1) 嘗試執行 Clear 操作時，裝置應拒絕並返回錯誤碼 `2` (Authentication Failure)，確保未授權存取被阻斷。

## Test Case (TC) Checkpoints

1. [Case01_Password_Initialization_Check]：
   - 動作：生成隨機 64-bit 密碼，透過 Vendor Command 4047 以 Query (cmd=2) 查詢 RPMB 密碼狀態。若返回 `0` (未設定)，則執行 Clear (cmd=1) 預期返回 `1` (錯誤/無效操作)，隨後再次 Query 確認狀態為 `0`。接著執行 Set (cmd=1) 設定該隨機密碼，預期返回 `0` (成功)。最後再次 Query 密碼狀態，預期返回 `1` (已設定)。
   - 預期結果：初始 Query 結果為 `0`；Clear 操作返回 `1`；Set 操作返回 `0`；最終 Query 結果為 `1`。驗證韌體能正確識別並切換 RPMB 密碼的 Set/Clear/Query 狀態。

2. [Case02_RPMB_Write_Integrity_Check]：
   - 動作：透過 Vendor Command 進入 RPMB Access Mode，清除 RPMB Key 並重新程式化 Key。使用 RPMB API 對 Region 0 寫入 4 個 LBA (LBA 0-3) 的測試資料。隨後呼叫 `read_rpmb_should_not_0`，讀取 Region 0 的資料，提取每個 LBA 中 Offset 228 到 484 的 Payload 區塊 (共 4KB)，並檢查這些位元組是否全為 `0x00`。
   - 預期結果：讀取的 Payload 資料中至少存在非 `0x00` 的位元組。驗證 RPMB 寫入機制能將 Host 端資料正確儲存於 Flash 中，且未被預設值覆蓋。

3. [Case03_Secure_Erase_Trigger_Check]：
   - 動作：使用 Case01 設定的正確密碼，透過 Vendor Command 4048 發送 Trigger RPMB Erase (cmd=0)。隨後進入輪詢循環，持續透過 Vendor Command 4048 發送 Query RPMB Erase Status (cmd=1)。檢查返回的 Payload 第一個位元組 (Status)，若不等於 `1` 或 `2` 則報錯；若等於 `1` 或 `2` 則跳出循環，代表擦除完成。
   - 預期結果：Trigger 操作返回 `0` (成功觸發)；輪詢最終返回的狀態值必須為 `1` (Erase Complete) 或 `2` (Erase In Progress/Complete)。驗證韌體能正確接收安全擦除指令並執行底層 Flash 區塊清除流程。

4. [Case04_Erase_Data_Verification_Check]：
   - 動作：在 Case03 確認 Erase 狀態為 `1` 後，再次呼叫 `read_rpmb_should_0` 讀取 Region 0 的資料。提取 Offset 228 到 484 的 Payload 區塊，檢查所有位元組是否均為 `0x00`。
   - 預期結果：讀取的 Payload 資料所有位元組均為 `0x00`。驗證 RPMB 安全擦除機制已徹底清除先前寫入的資料，符合安全標準。

5. [Case05_Wrong_Password_Auth_Failure_Check]：
   - 動作：計算錯誤密碼 `wrongpassword = password - 1`。使用此錯誤密碼透過 Vendor Command 4047 執行 Clear RPMB Password (cmd=1) 操作。檢查返回的 Payload 第一個位元組 (Status)。
   - 預期結果：返回的狀態值必須為 `2` (Authentication Failure)。驗證韌體在密碼驗證階段嚴格比對，拒絕使用錯誤憑證進行的敏感操作，確保 RPMB 區域的安全性。