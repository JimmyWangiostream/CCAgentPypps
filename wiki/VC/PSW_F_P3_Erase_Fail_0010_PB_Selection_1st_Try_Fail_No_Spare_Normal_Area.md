# Test Spec: UFS FW Stuck Verification on Spare Block Exhaustion (VC-17)

## Verification Criterion (VC)
驗證當 Normal Area 備用區塊（Spare Block）耗盡且發生 Erase Fail 時，韌體是否正確進入死鎖（Stuck）狀態：
1. **正常流程驗證 (pre_process)**：確認在備用區塊充足時，透過 VU C012 注入 Erase Fail 並觸發 L2 VB 切換，系統能正常更新 BBT 並增加 Bad Block 計數，證明測試環境與注入機制有效。
2. **異常死鎖驗證 (step1)**：在備用區塊預測值為 0xFFFF（無可用備用區塊）的情境下，針對下一個 L2 VB 注入 Erase Fail 並持續寫入。預期韌體因無法進行區塊替換而觸發 Assert (0x202) 或進入無限等待狀態，導致 Write10 命令超時 (G_TIMEOUT_ALL)，且 L2 VB 號碼維持不變，確認韌體在資源枯竭時的錯誤處理機制符合預期（即 Stuck）。

## Test Case (TC) Checkpoints

1. [Case01_Normal_EraseFail_Replacement_Check]:
   - 動作：
     1. 透過 VU 40C1 讀取當前 L2 Open VB (`L2_vb`)。
     2. 透過 VU 40DC 讀取下一個預期的 L2 VB (`L2_vb_next`)。
     3. 透過 VU 405E 記錄初始 Bad Block 計數 (`BB_count`)。
     4. 透過 VU 40D6 確認下一個替換區塊 (`next_replacement_block`) 不為 0xFFFF（表示有備用區塊）。
     5. 使用 VU C012 針對 `L2_vb_next` (CE:0, Plane:0) 注入 `fail_type=1` (Erase Fail)。
     6. 從 LBA 0 開始連續執行 Write10 命令，每次寫入 `WRITE_10_MAX_BLOCK_LEN` 長度，並持續透過 VU 40C1 監控 L2 VB 狀態。
     7. 當 L2 VB 發生跳變（`L2_vb_new != L2_vb`）時停止寫入。
     8. 透過 VU 4013 讀取 BE Fail 狀態，並透過 VU 405E 重新讀取 Bad Block 資訊。
     9. 計算 BBT 並比對目標區塊是否被標記為 Bad，且 `BB_count_new` 必須等於 `BB_count + 1`。
   - 預期結果：
     - L2 VB 成功切換，證明韌體在備用區塊可用時能正常處理 Erase Fail 並進行替換。
     - Bad Block 計數增加 1。
     - BBT 中明確包含目標區塊 (`L2_vb_next`) 的資訊，證明替換機制運作正常。

2. [Case02_SpareExhaustion_FWStuck_Check]:
   - 動作：
     1. 透過 VU 40C1 讀取當前 L2 Open VB (`L2_vb`)。
     2. 透過 VU 40DC 讀取下一個預期的 L2 VB (`L2_vb_next`)。
     3. 使用 VU C012 針對 `L2_vb_next` (CE:0, Plane:0) 注入 `fail_type=1` (Erase Fail)。
     4. 從 LBA 0 開始連續執行 Write10 命令，每次寫入 `WRITE_10_MAX_BLOCK_LEN` 長度。
     5. 在發送命令時設定 `skip_response_check=True` 以捕捉超時異常。
     6. 持續監控 L2 VB 狀態，預期其保持不變。
   - 預期結果：
     - 寫入命令觸發 `G_TIMEOUT_ALL` 異常。
     - 韌體 Assert 編號必須為 `0x202`，代表韌體偵測到無法處理的錯誤並進入死鎖狀態。
     - L2 VB 號碼必須維持為初始值 (`L2_vb_new == L2_vb`)，證明因無備用區塊可替換，韌體無法推進邏輯區塊映射，導致系統掛起。