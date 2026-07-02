# Test Spec: UFS GC Robustness & BB Retirement Verification under CECC/UECC Injection

## Verification Criterion (VC)
驗證 UFS 韌體在垃圾回收（GC）流程中，針對不同來源區塊（Source Block）與目標區塊（Destination Block）進行錯誤注入（CECC/UECC）後的系統穩定性與壞塊管理機制：
1. **CECC 源區塊驗證**：在 L1/EM1/WB/PSA 四種 GC 情境下，確認對 GC Source Block 注入 CECC（透過 Vendor Command D014 設定 Read Recovery Module）後，韌體能正確處理讀取錯誤並繼續執行 GC 流程，且最終資料完整性通過 HW_COMPARE。
2. **UECC 目標區塊驗證**：在 GC 觸發後，對當前處於 `GC_DEST` 狀態的 VB 注入 UECC（透過 Vendor Command C012 模擬 Program/Erase Fail），模擬韌體在寫入目標區塊時發生不可修復錯誤的情境。
3. **SPOR 恢復與 BKOPS 狀態驗證**：執行 SPOR（Soft Power Off Reset）後，確認韌體能正確恢復並啟用 BKOPS，且 BKOPS 最終進入 Idle 狀態，證明韌體在異常錯誤注入後未陷入死鎖或狀態不一致。
4. **BB Retirement 原因驗證**：驗證被注入 UECC 的 VB 最終被標記為壞塊（Bad Block），且其 Retirement Reason 必須為 `READBACK`，證明韌體是透過讀取回傳錯誤（Readback Error）而非其他機制（如 Program Fail）來判定該區塊失效。

## Test Case (TC) Checkpoints

1. [Case01_L1_GC_CECC_Source_Check]：
   - 動作：配置 LUN 為 SLC (LUN0) + TLC (LUN1)，在 LUN1 寫入 `pageline_block * 3` 大小的資料以建立 Source Block。透過 `issue_D014` 對該 Source Block 的特定 Die/Plane/Block 注入 CECC（設定 `isSpeciBlock=1`, `nandMode=1`）。接著寫入額外資料觸發 L1 GC。在 GC 過程中，針對 `CURRENT_L2_TLC` 列表中的 VB 執行 `issue_C012` 注入 Program/Erase Fail (`fail_type=3`)。執行 SPOR 後，確認 BKOPS Idle，並檢查被注入 VB 的 Retirement Reason。
   - 預期結果：資料讀取比較（Read Compare）通過；被注入的 VB 狀態在 VBINFO 中顯示異常；最終 `check_BB_retirement` 驗證該 VB 的 Retirement Reason 等於 `project_api.BBRetirementReaspnType.READBACK`。

2. [Case02_EM1_GC_Threshold_Trigger_Check]：
   - 動作：配置 LUN 為 SLC (LUN0, 20個VB) + TLC (LUN1)。在 LUN0 持續寫入資料，直到 `USED_BLK_POOL_EM1` 的 VB 數量達到 SLC GC 閾值 (`slc_threshold`)，強制觸發 EM1 GC。在 GC 觸發前，對 Source Block 注入 CECC。GC 完成後，對 `GC_DEST` 狀態的 VB 注入 UECC (`issue_C012`, `fail_type=3`)。執行 SPOR 並等待 BKOPS Idle。
   - 預期結果：EM1 GC 流程正常完成；被注入 UECC 的 VB 被正確識別為壞塊；`check_BB_retirement` 驗證該 VB 的 Retirement Reason 等於 `project_api.BBRetirementReaspnType.READBACK`。

3. [Case03_WB_GC_Fill_Buffer_Check]：
   - 動作：配置 LUN 為 SLC + TLC，啟用 Write Booster (`WRITEBOOSTER_EN`) 並禁用 Buffer Flush。在 LUN1 持續寫入資料，直到 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 屬性值不再為 `0xA`（表示 Buffer 已滿或狀態改變）。在 GC 觸發前，對 Source Block 注入 CECC。GC 完成後，對 `GC_DEST` 狀態的 VB 注入 UECC。執行 SPOR 並等待 BKOPS Idle。
   - 預期結果：Write Booster Buffer 填滿機制正常；被注入 UECC 的 VB 被正確識別為壞塊；`check_BB_retirement` 驗證該 VB 的 Retirement Reason 等於 `project_api.BBRetirementReaspnType.READBACK`。

4. [Case04_PSA_GC_POR_Recovery_Check]：
   - 動作：配置 LUN 為 SLC + TLC。設定 PSA State 為 `PRE_SOLDERING`，寫入 `PSA_MAX_DATA_SIZE` 大小的資料，並將 PSA State 設為 `LOADING_COMPLETE`。執行 HW_RESET (`powerdown=True`) 模擬 POR。POR 後，寫入少量資料觸發 PSA 相關的 GC 流程。在 GC 觸發前，對 Source Block 注入 CECC。GC 完成後，對 `GC_DEST` 狀態的 VB 注入 UECC。執行 SPOR 並等待 BKOPS Idle。
   - 預期結果：PSA 資料在 POR 後保持完整；被注入 UECC 的 VB 被正確識別為壞塊；`check_BB_retirement` 驗證該 VB 的 Retirement Reason 等於 `project_api.BBRetirementReaspnType.READBACK`。

5. [Case05_VB_State_Transition_Log_Check]：
   - 動作：在所有 Case 執行過程中，記錄四個時間點的 VB 列表狀態：A (寫入前), B (CECC注入後/GC前), C (UECC注入後/GC後), D (SPOR後/BKOPS Idle後)。比對每個 VB 在這四個時間點的狀態變化（如 `GC_SOURCE`, `GC_DEST`, `GC_FG_QUEUE`, `GC_BG_QUEUE` 等標記）。
   - 預期結果：對於被注入 UECC 的 VB，其狀態在 C 和 D 階段應顯示為異常或已移除出正常可用列表；對於正常 VB，其狀態轉換應符合 UFS 規範（例如從 `GC_SOURCE` 變更為 `FREE` 或 `GC_DEST` 變更為 `NORMAL`）；所有狀態轉換日誌應無衝突或死鎖跡象。