# Test Spec: VC-18 (5.c) Erase Fail with Hidden Area Replacement Block Exhaustion - FW Stuck Verification

## Verification Criterion (VC)
驗證在 Hidden Area 情境下，當 L2 VB 對應的實體區塊發生 Erase Fail，且韌體嘗試從預先預測的 Replacement Block Pool (Pool Type 2) 中選取新區塊時，若連續兩次選取的新區塊（1st BBT EF 與 2nd BBT EF）均宣告 Erase Fail，韌體將無法完成 L2 VB 的遷移，導致 Host 端 Write10 指令超時，並觸發特定的韌體 Assert 錯誤碼 0x510。此測試旨在確認韌體在替換區塊資源耗盡或連續失敗時的錯誤處理機制與狀態鎖定行為。

## Test Case (TC) Checkpoints
1. [Case01_HiddenArea_Replacement_Exhaustion_Assert_0x510_Check]：
   - 動作：
     1. 透過 Vendor Command 40C1 讀取當前 L2 VB 號碼 ($L2_{vb}$)，並透過 40DC 讀取下一個可用的 Open VB 號碼 ($L2_{vb\_next}$)。
     2. 透過 Vendor Command 40D6 查詢 Hidden Area (Pool Type 2) 的預測替換區塊，取得前兩個替換區塊的物理地址資訊：
        - 第 1 個替換區塊：CE=$CE_1$, Plane=$Plane_1$, Block=$Block_1$
        - 第 2 個替換區塊：CE=$CE_2$, Plane=$Plane_2$, Block=$Block_2$
     3. 透過 Vendor Command C012 注入 Erase Fail 錯誤，針對以下三個區塊設定 fail_type=1：
        - 目標區塊：$L2_{vb\_next}$ (Die 0, Plane 0)
        - 第 1 個替換區塊：$Block_1$ (Die $CE_1$, Plane $Plane_1$)
        - 第 2 個替換區塊：$Block_2$ (Die $CE_2$, Plane $Plane_2$)
     4. 從 LBA 0 開始執行連續的 Write10 指令（每次寫入最大長度），並設置 `skip_response_check=True` 以捕捉超時。
     5. 監控 Host 端是否拋出 `G_TIMEOUT_ALL` 異常。
     6. 若發生超時，立即檢查韌體 Assert 號碼是否為 0x510。
     7. 在超時發生前，輪詢讀取 L2 VB 號碼，確認其始終等於初始的 $L2_{vb}$，未發生跳變。
   - 預期結果：
     - Host 端必須拋出 `G_TIMEOUT_ALL` 異常，表示 Write10 指令因韌體卡死而無回應。
     - 韌體 Assert 號碼必須精確等於 0x510。
     - 在超時發生期間，L2 VB 號碼必須保持不變（等於 $L2_{vb}$），證明韌體因無法處理連續的替換區塊 Erase Fail 而進入 Stuck 狀態，未執行任何邏輯上的 VB 遷移。
     - 若未拋出超時或 Assert 號碼不等於 0x510，則測試失敗並拋出 `SIGHTING_RESPONSE_UNEXPECTED`。