# Test Spec: UFS SLC PSA State Transition & LWP Consistency Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 SLC 模式下的 PSA (Power State Awareness) 狀態機轉換邏輯與 LWP (Last Written Page) 的一致性：
1.  **PSA 狀態機驗證**：確認透過 `WriteAttribute` 將 `PSA_STATE` 從 `OFF` 設定為 `PRE_SOLDERING` 後，裝置能正確進入預焊接狀態，且該狀態下允許特定的寫入操作。
2.  **LWP 一致性與 SPOR 行為驗證**：在 `PRE_SOLDERING` 狀態下，針對 Normal LUN (LUN 0) 執行跨 CE/Plane 的 SLC 順序寫入。記錄寫入前的 LWP 狀態 (LWP_A)，執行無 SSU 的 HW_RESET (模擬 SPOR)，記錄重啟後的 LWP 狀態 (LWP_B)。驗證 LWP_A 與 LWP_B **必須不同**，證明韌體在異常掉電後正確更新了 LWP 指標以反映最後寫入的頁面，且未發生 LWP 指標凍結或錯誤回滾。
3.  **資料完整性驗證**：重啟後讀取寫入區域，確認資料與寫入記錄 (Write Record) 完全一致，排除因 PSA 狀態切換或重置導致的資料損壞。

## Test Case (TC) Checkpoints

1.  **[TC01_PSA_PreSoldering_LWP_Diff_Check]**：
    -   **動作**：
        1.  初始化測試環境，配置 LUN 0 (Normal), LUN 1 (Boot A), LUN 2 (Boot B), LUN 3 (EM1)，並設定 LUN 0 為 Thin Provisioning。
        2.  透過 `WriteAttribute` 將 `PSA_STATE` 設定為 `OFF`，確保裝置處於正常操作狀態。
        3.  執行 `Unmap` 命令清除所有 LUN 的邏輯區塊映射，確保寫入起始於乾淨狀態。
        4.  透過 `WriteAttribute` 將 `PSA_STATE` 設定為 `PRE_SOLDERING`，並等待狀態切換完成。
        5.  針對 LUN 0 執行順序寫入，寫入長度為 `slc_ce_page * ce_num * 2` (即 2 個 SLC 頁面寬度的資料)，並啟用 `HW_COMPARE` 進行寫入時硬體比對。
        6.  寫入完成後，呼叫 `issue_409D_to_do_power_loss_analysing` (透過 `collect_lwp_checks` 封裝) 獲取當前各 Plane 的 LWP 狀態，儲存為 `LWP_A`。
        7.  呼叫 `api.init_tester_to_unit_ready` 執行 **HW_RESET**，且 `powerdown=False` (模擬無 SSU 的硬體重啟)。
        8.  裝置重啟並進入 Unit Ready 後，再次呼叫 `collect_lwp_checks` 獲取當前各 Plane 的 LWP 狀態，儲存為 `LWP_B`。
        9.  比較 `LWP_A` 與 `LWP_B`，並執行 `read_compare` 驗證寫入資料的完整性。
    -   **預期結果**：
        1.  `LWP_A` 與 `LWP_B` **必須不同** (`identical == False`)。這代表在無 SSU 保護的 HW_RESET 後，韌體成功從非揮發性儲存或暫存器中恢復並更新了 LWP 指標，指向最後寫入的 SLC 頁面，而非重置為舊值或保持不變。
        2.  `read_compare` 必須通過，確認寫入的 SLC 資料在重置後仍可被正確讀取且無誤碼，證明 PSA 狀態切換與重置過程未破壞用戶資料。
        3.  若 `LWP_A` 等於 `LWP_B`，則測試失敗 (`SIGHTING_FAIL_DATA_COMPARE_FAIL`)，因為這暗示韌體未能正確追蹤或恢復最後寫入位置，存在資料一致性風險。