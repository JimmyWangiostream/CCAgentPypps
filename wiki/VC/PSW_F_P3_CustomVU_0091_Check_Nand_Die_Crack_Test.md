# Test Spec: NAND Trim Register Crack Injection & HW_RESET Recovery Verification

## Verification Criterion (VC)
驗證 NAND Trim 暫存器（特定地址 0x050, 0x150, 0x250, 0x350）在透過 Vendor Command 強制修改為異常值（Crack 狀態）後，硬體行為是否符合預期：
1. **Crack 檢測機制**：確認在注入異常 Trim 值後，透過 VU 40E6 指令讀取的 Die Status 必須回報為 1（代表偵測到 Crack/異常）。
2. **HW_RESET 清除機制**：確認執行 HW_RESET 後，即使未立即恢復 Trim 值，硬體狀態機是否自動重置或清除 Crack 標記（預期結果為 0，即無 Crack）。
3. **韌體恢復機制**：確認透過 C084 Vendor Command 將 Trim 值寫回預設正常值（Default Value）後，再執行 HW_RESET，Die Status 必須維持為 0（正常），驗證韌體在電源循環後能正確載入預設 Trim 參數並消除異常狀態。

## Test Case (TC) Checkpoints
1. [Case01_Baseline_No_Crack_Check]：
   - 動作：透過 `issue_4084_to_get_NAND_trim` 讀取當前 NAND Trim 暫存器（地址 0x050, 0x150, 0x250, 0x350）的預設值。接著執行 `issue_40E6_to_check_nand_die_crack` 指令，並對所有 CE (Chip Enable) 的 Die 進行狀態檢查。
   - 預期結果：所有 Die 的檢查結果必須等於 `0`（代表 No Crack/Normal），確認系統初始狀態無異常，且 Trim 暫存器處於預設正常範圍。

2. [Case02_HW_RESET_Clean_State_Check]：
   - 動作：執行 `api.init_tester_to_unit_ready` 進行 HW_RESET（無 Power Down）。重置後，再次執行 `issue_40E6_to_check_nand_die_crack` 檢查所有 Die 狀態。
   - 預期結果：所有 Die 的檢查結果必須等於 `0`，確認單純的 HW_RESET 不會導致 NAND 進入異常狀態，且硬體狀態機在重置後處於乾淨（Clean）狀態。

3. [Case03_Crack_Injection_Verification]：
   - 動作：針對每個目標地址（0x050, 0x150, 0x250, 0x350），分別設定 `force_crack_dict` 中的異常值（0x050/0x250 設為 0xFF, 0x150/0x350 設為 0x0）。註：程式碼中註解掉了實際寫入指令，但邏輯假設已透過 `issue_C084_to_set_NAND_trim` 寫入。寫入後，執行 `issue_40E6_to_check_nand_die_crack` 檢查所有 Die 狀態。
   - 預期結果：所有 Die 的檢查結果必須等於 `1`（代表 Crack Detected），驗證當 Trim 參數被強制修改為異常值時，NAND 控制器能正確偵測並標記 Die 為異常狀態。

4. [Case04_HW_RESET_After_Crack_Check]：
   - 動作：在已注入 Crack 狀態（Trim 值異常）的情況下，執行 `api.init_tester_to_unit_ready` 進行 HW_RESET（無 Power Down）。重置後，立即執行 `issue_40E6_to_check_nand_die_crack` 檢查所有 Die 狀態。
   - 預期結果：所有 Die 的檢查結果必須等於 `0`。這驗證了硬體層面的 HW_RESET 機制會強制清除暫存的 Crack 標記或重置 NAND 狀態機，即使 Trim 暫存器內的值仍為異常值，硬體狀態在重置瞬間被視為正常（或標記被清除）。

5. [Case05_Trim_Recovery_And_Stability_Check]：
   - 動作：在 Case04 重置後的狀態下，透過 `issue_C084_to_set_NAND_trim` 將所有目標地址的 Trim 值寫回 `default_dict` 中的預設正常值（0x050/0x250 -> 0x4, 0x150/0x350 -> 0x3）。寫入完成後，執行 `api.init_tester_to_unit_ready` 進行 HW_RESET。最後，執行 `issue_40E6_to_check_nand_die_crack` 檢查所有 Die 狀態。
   - 預期結果：所有 Die 的檢查結果必須等於 `0`。驗證在將 Trim 參數恢復為預設正常值並執行 HW_RESET 後，系統能穩定維持在正常狀態，確認韌體能正確載入預設 Trim 參數並消除之前的異常標記。