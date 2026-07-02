# Test Spec: UFS FTL LWP State Persistence Verification under HW_RESET (No SSU)

## Verification Criterion (VC)
驗證 UFS 韌體在 **無 Secure Storage Unit (SSU)** 保護的硬體重啟 (HW_RESET) 情境下，FTL (Flash Translation Layer) 的 **LWP (Logical Write Pointer)** 狀態機與 **Open VB (Virtual Block)** 編號的持久化行為：
1.  **基礎持久化驗證**：確認在 Normal LUN (LUN 0) 進行 TLC 寫入後，執行 HW_RESET 且無 SSU 流程，韌體恢復後的 LWP 狀態與 Open VB 編號必須與重置前完全一致，證明 LWP 資訊已正確寫入非揮發性儲存空間 (如 PTE 或特定 FTL 表)。
2.  **多 CE/Plane 狀態同步驗證**：驗證在寫入觸發不同 WL (Write Leveling) 閾值 (如 WL2, WL540, WL541, WL556, WL557, WL558, WL559, WL1108, WL1109, WL1110, WL1111) 時，針對特定 CE (Chip Enable) 與 Plane 的 LWP 狀態，在 HW_RESET 後是否仍能精確恢復至重置前的邏輯頁位置。
3.  **跨 WL 邊界行為驗證**：特別驗證在跨越不同 WL Group (GroupA, GroupB, GroupC, GroupD) 邊界時，LWP 的遞增與 Open VB 的切換邏輯在掉電恢復後是否保持連續且無損壞。

## Test Case (TC) Checkpoints

1.  **[TC01_Basic_LWP_Persistence_Check]**：
    -   動作：配置 LUN 0 (Normal) 為測試目標，寫入 1 個 TLC CE Page 大小的資料 (大小為 `Plane_Per_Die * 4 * 3` pages)。透過 Vendor Command 0x40C1 (`issue_40C1_to_get_open_vb_information`) 取得當前 Open VB 編號 (`L2_Open_logical_VB_Host_TLC_number`)。接著呼叫 `collect_lwp_checks` 記錄所有 CE/Plane 的當前 LWP 狀態 (記為 LWP_A)。執行 `api.init_tester_to_unit_ready` 設定為 `HW_RESET` 且 `powerdown=False` (無 SSU)。重置完成後，再次透過 0x40C1 取得 Open VB 編號，並呼叫 `collect_lwp_checks` 取得重置後的 LWP 狀態 (記為 LWP_B)。
    -   預期結果：重置後的 Open VB 編號必須與重置前完全相同；LWP_A 與 LWP_B 必須完全一致 (`identical == True`)，代表韌體在無 SSU 保護下成功從非揮發性儲存載入並恢復了 LWP 狀態。

2.  **[TC02_WL2_First_CE_LWP_Persistence_Check]**：
    -   動作：從上一階段繼續，寫入資料直到觸發 WL2 的第一個 CE (Chip Enable)。寫入長度計算為 `per_tlcwl_cepage * 2 - already_write_cepage + 1 * tlc_ce_page`。寫入完成後，取得當前 Open VB 編號並記錄 LWP_A。執行無 SSU 的 HW_RESET。重置後取得 Open VB 編號並記錄 LWP_B。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。此步驟驗證在寫入量達到 WL2 閾值時，LWP 狀態的持久化機制依然有效。

3.  **[TC03_WL2_Subsequent_CE_LWP_Persistence_Check]**：
    -   動作：針對剩餘的 CE (i=1 至 `ce_num-1`)，每個 CE 寫入 1 個 TLC CE Page 大小的資料。在每個 CE 寫入後，檢查第一個 CE (CE 0) 的 LWP 值是否等於 **26** (`lwpA[0].LWP.value != 26`)。若不等於 26 則報錯。隨後執行無 SSU 的 HW_RESET，並比較重置前後的 LWP (LWP_A vs LWP_B) 及 Open VB 編號。
    -   預期結果：CE 0 的 LWP 必須精確等於 26；重置後的 LWP 狀態與 Open VB 編號必須與重置前完全一致。此步驟驗證在 WL2 階段多個 CE 並行寫入後的狀態恢復。

4.  **[TC04_WL540_FEP_Persistence_Check]**：
    -   動作：寫入資料直到所有 CE 的 Plane 0 的 FEP (Final Erase Page) 達到 `WL_Group.GroupA_TLC_end` (即 WL540)。寫入完成後，記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。驗證在 GroupA 結束時的狀態持久化。

5.  **[TC05_WL541_MLC_Start_Persistence_Check]**：
    -   動作：寫入資料直到 CE 0 的 Plane 0 FEP 達到 `WL_Group.GroupB_MLC_start` (即 WL541)，而其他 CE 保持在前一狀態。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。驗證在 GroupB 開始時的非同步 LWP 狀態恢復。

6.  **[TC06_WL542_MLC_Start_Plus1_Persistence_Check]**：
    -   動作：寫入資料直到所有 CE 的 Plane 0 FEP 達到 `WL_Group.GroupB_MLC_start` (WL541) 後的下一個狀態 (註：程式碼中寫入直到 `GroupB_MLC_start` 但針對 `ce=ce_num-1, plane=0`，隨後檢查點描述為 WL541，實際動作是寫入至該特定 CE/Plane 的指定 LWP)。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。

7.  **[TC07_WL542_CE0_Persistence_Check]**：
    -   動作：寫入資料直到 CE 0 的 Plane 0 FEP 達到 `WL_Group.GroupB_MLC_start + 1` (即 WL542)，而其他 CE 保持在 WL541。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。驗證 CE 0 領先其他 CE 一個 LWP 時的狀態恢復。

8.  **[TC08_WL556_MLC_End_Persistence_Check]**：
    -   動作：寫入資料直到所有 CE 的 Plane 0 FEP 達到 `WL_Group.GroupB_MLC_end` (即 WL556)。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。驗證 GroupB 結束時的狀態持久化。

9.  **[TC09_WL557_TLC_Start_Plus2_Persistence_Check]**：
    -   動作：寫入資料直到 CE 0 的 Plane 0 FEP 達到 `WL_Group.GroupC_TLC_start + 2` (即 WL557)，而其他 CE 保持在 WL556。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。驗證 GroupC 開始階段的非同步狀態恢復。

10. **[TC10_WL558_TLC_Start_Plus5_Persistence_Check]**：
    -   動作：寫入資料直到所有 CE 的 Plane 0 FEP 達到 `WL_Group.GroupC_TLC_start + 2 + 3` (即 WL558)。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。

11. **[TC11_WL559_TLC_Start_Plus8_Persistence_Check]**：
    -   動作：寫入資料直到 CE 0 的 Plane 0 FEP 達到 `WL_Group.GroupC_TLC_start + 2 + 3 + 3` (即 WL559)，而其他 CE 保持在 WL558。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。

12. **[TC12_WL1108_TLC_End_Persistence_Check]**：
    -   動作：寫入資料直到所有 CE 的 Plane 0 FEP 達到 `WL_Group.GroupC_TLC_end` (即 WL1108)。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。驗證 GroupC 結束時的狀態持久化。

13. **[TC13_WL1109_SLC_Start_Persistence_Check]**：
    -   動作：寫入資料直到 CE 0 的 Plane 0 FEP 達到 `WL_Group.GroupD_SLC_start` (即 WL1109)，而其他 CE 保持在 WL1108。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。驗證進入 GroupD (SLC 模式) 時的狀態恢復。

14. **[TC14_WL1110_SLC_Start_Plus1_Persistence_Check]**：
    -   動作：寫入資料直到所有 CE 的 Plane 0 FEP 達到 `WL_Group.GroupD_SLC_start + 1` (即 WL1110)。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。

15. **[TC15_WL1111_SLC_End_Minus1_Persistence_Check]**：
    -   動作：寫入資料直到 CE 0 的 Plane 0 FEP 達到 `WL_Group.GroupD_SLC_end - 1` (即 WL1111)，而其他 CE 保持在 WL1110。記錄 LWP_A 與 Open VB。執行無 SSU 的 HW_RESET。重置後記錄 LWP_B 與 Open VB。
    -   預期結果：Open VB 編號必須不變；LWP_A 與 LWP_B 必須完全一致。驗證 SLC 階段結束前的狀態持久化。