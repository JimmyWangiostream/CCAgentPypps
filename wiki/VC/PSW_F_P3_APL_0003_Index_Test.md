# Test Spec: UFS Index Page UECC Corruption & SPOR Recovery Validation

## Verification Criterion (VC)
驗證 UFS 韌體在無 SSU (Secure Storage Unit) 保護下的 HW_RESET 過程中，針對 Index Page (包含 Mirror 與 Major 頁面) 進行不同層級 UECC 錯誤注入後的系統行為與狀態恢復機制：
1. **Mirror Page Single UECC**：驗證僅在 Index Mirror Page LWP 注入單一 UECC 錯誤後，韌體能透過備援機制自動修復並刷新 Index 資訊，系統初始化成功且 Index 邏輯位置發生跳變（Refresh）。
2. **Major Page Single UECC**：驗證在 Index Mirror Page 正常情況下，僅在 Index Major Page LWP-1 注入單一 UECC 錯誤後，韌體能成功修復並刷新 Index 資訊，系統初始化成功且 Index 邏輯位置發生跳變。
3. **Cumulative UECC on Mirror & Major**：驗證在連續循環中，同時對 Index Mirror Page 與 Index Major Page (LWP-1, LWP-N) 注入 UECC 錯誤，驗證韌體是否能持續透過備援頁面修復並刷新 Index，確保系統初始化成功且 Index 邏輯位置持續跳變。
4. **Total Index Page Corruption (Fail Case)**：驗證當 Index 所有頁面 (Page 0, Page 1, etc.) 均被注入 UECC 錯誤導致完全不可讀時，韌體應觸發 Assert 並導致 `init_tester_to_unit_ready` 失敗，確認系統無法在無備援資料下恢復。

## Test Case (TC) Checkpoints

1. **[Case01_Mirror_UECC_Single_Check]**：
   - 動作：透過 Vendor Command 0x40C1 讀取當前 Open VB 資訊，計算出 Index Mirror Page 的 PCA (Physical Channel Address: Block, Plane, CE, Page)。執行 HW_RESET (無 SSU)。再次讀取 Open VB 資訊並計算 PCA，確認與重置前一致。接著，針對計算出的 Index Mirror Page LWP 注入 UECC 錯誤（避開 ICS Bad Block 區域）。再次執行 HW_RESET (無 SSU)。最後讀取 Open VB 資訊並計算新的 PCA。
   - 預期結果：重置前的 PCA 與重置後（注入前）的 PCA 必須完全相同（Block, Plane, CE, Page 均一致）。注入 UECC 並重置後，新的 PCA 必須與注入前的 PCA **不同**（代表 Index 邏輯位置已刷新/Refresh），且系統初始化成功無 Assert。

2. **[Case02_Major_UECC_Single_Check]**：
   - 動作：在 Case01 的基礎上，獲取當前 Index 資訊。計算 Index Major Page LWP-1 的 PCA（即 First Free Physical Page - 1 對應的物理位置）。針對該 PCA 注入 UECC 錯誤。執行 HW_RESET (無 SSU)。
   - 預期結果：系統初始化必須成功（無 Assert）。韌體應能識別 Major Page 錯誤並從 Mirror Page 或其他備援機制恢復，最終 Index 邏輯位置應發生刷新（與注入前的 PCA 不同）。

3. **[Case03_Cumulative_Mirror_Major_UECC_Check]**：
   - 動作：進入循環測試（i=0,1,2）。在每次循環中：
     a. 對當前 Index 的 Mirror Page 注入 UECC。
     b. 執行 HW_RESET (無 SSU)，確認 Index 刷新。
     c. 對當前 Index 的 Major Page LWP-1 注入 UECC。
     d. 若循環 i>=1，進一步對更早的 Major Page (LWP-N, N>1) 注入 UECC，具體位置取決於 ICS Bad Block 狀態與物理頁面的遞減計算（確保避開 Bad Block）。
     e. 執行 HW_RESET (無 SSU)。
     f. 讀取 Open VB 資訊並計算 PCA。
   - 預期結果：每次 HW_RESET 後，系統初始化必須成功。讀取到的新 PCA 必須與注入 UECC 前的 PCA **不同**，證明韌體在多重備援頁面（Mirror 與多個 Major 頁面）均受損的情況下，仍能成功修復並推進 Index 邏輯位置。

4. **[Case04_Total_Index_Corruption_Fail_Check]**：
   - 動作：獲取當前 Index 資訊。計算 Index 所有相關頁面（Page 0, Page 1, ... 直到 Page 0, CE 0, Plane 0）的 PCA。針對**所有**這些頁面注入 UECC 錯誤，確保沒有任何備援頁面是有效的。執行 HW_RESET (無 SSU)。
   - 預期結果：`api.init_tester_to_unit_ready` 必須拋出異常（Exception），且 `api.get_fw_assert_number()` 應返回非零值（代表觸發韌體 Assert）。這確認當所有 Index 備援資料均失效時，系統無法恢復並進入錯誤狀態。