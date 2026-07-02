# Test Spec: UFS Media Scan Status Verification for Various Error Injection Scenarios

## Verification Criterion (VC)
驗證 UFS 韌體在禁用自動媒體掃描（Media Scan）的情境下，透過 Vendor Command `0x4028` 觸發手動媒體掃描時，針對不同硬體錯誤注入類型（Page Attribute 錯誤、空白頁錯誤、Valley Check 錯誤、MLC Page UECC、VRLC 左右讀取 UECC、DiffEC、溫度相關 EC 閾值、EPC 空白頁 UECC、Good BEC、溫度解摺疊、Valley Offset/Center EC 解摺疊）的識別與回報機制。測試涵蓋 SLC (LUN 1) 與 TLC (LUN 0) 兩種記憶體類型，並驗證 `media_scan_status` 欄位是否正確回傳對應的 `BE_STATUS` 代碼（0x01, 0x02, 0x03, 0x04, 0x06, 0x07, 0x08, 0x0B, 0x0D, 0x0E, 0x0F, 0x10）。

## Test Case (TC) Checkpoints

1.  **[Case01_Wrong_Page_Attr_Check]**：
    -   動作：針對 SLC 區塊（Page Attr 0）注入非 SLC 屬性（1, 2, 3, 4, 5）；針對 TLC 區塊（Page Attr 3）注入非 TLC 屬性（0, 1, 2, 4, 5）。透過 `issue_4028` 觸發媒體掃描，設定 `b43_is_blank_page=0`（非空白頁），讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x01` (`BE_STATUS_MEDIA_SCAN_WRONG_PAGE_ATTR`)，代表韌體正確識別出 Page Attribute 與預期模式不符。

2.  **[Case02_Wrong_Empty_Page_Check]**：
    -   動作：針對 SLC 區塊（Page Attr 0）與 TLC 區塊（Page Attr 3），在 Page 0 處標記為空白頁（`b43_is_blank_page=1`），透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x02` (`BE_STATUS_MEDIA_SCAN_BLOCK_WRONG_EMPTY_PAGE`)，代表韌體識別出標記為空白的頁面實際含有資料或屬性錯誤。

3.  **[Case03_Wrong_Page_For_Valley_Check_Check]**：
    -   動作：針對 SLC 區塊（Page Attr 0）與 TLC 區塊（Page Attr 3），在 Page 12 處標記為非空白頁（`b43_is_blank_page=0`），透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x03` (`BE_STATUS_MEDIA_SCAN_WRONG_PAGE_FOR_VALLEY_CHECK`)，代表韌體在 Valley Check 機制中識別出該頁面不應存在於此位置或屬性異常。

4.  **[Case04_MLC_LP_BEC_Fold_Check]**：
    -   動作：在 LUN 0 (TLC) 寫入超過一個 WL 大小的資料。針對 TLC 區塊中的 MLC_LP Page（Page 1620, 1622...1650），使用 `inject_UECC` 注入 UECC 錯誤。透過 `issue_4028` 觸發媒體掃描，設定 `b42_page_attr=1` (MLC_LP)，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x04` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_MLCLP_BEC`)，代表韌體識別出 MLC_LP 頁面存在 BEC (Block Error Count) 異常且需摺疊。

5.  **[Case06_VRLC_Left_Right_UECC_Check]**：
    -   動作：針對 SLC 區塊與 TLC 區塊的 Page 0，分別注入 380 個 Error Bits（SLC 使用 `flipbit_on_SLC`，TLC 使用 `flipbit_on_TLC`）。透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x06` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_VRLC_LEFT_RIGHT_READ_UECC`)，代表韌體識別出左右讀取（VRLC）時的 UECC 錯誤超過閾值。

6.  **[Case07_DiffEC_Check]**：
    -   動作：針對 SLC 區塊與 TLC 區塊的 Page 0，分別在每個 4KB 區塊內注入 150 個 Error Bits（SLC）或 235 個 Error Bits（TLC），共 4 個 4KB 區塊。透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x07` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_DIFFEC`)，代表韌體識別出不同 4KB 區塊間的 Error Bit Count 差異（DiffEC）超過閾值。

7.  **[Case08_Temp_Fold_Check]**：
    -   動作：執行 HW_RESET 後，設定 NAND 溫度為 20°C（Die 0）與 85°C（Controller）。透過 `issue_D08E` 設定 `XTEMP_DELTA_TH=1` 與 `VALLEY_CENTER_EC_TH=1`。在 SLC 區塊 Page 0 注入 150 個 Error Bits（每個 4KB）。透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x08` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_FOR_TEMP`)，代表韌體在特定溫度與 EC 閾值設定下，識別出需因溫度因素摺疊區塊。

8.  **[Case11_EPC_Empty_UECC_Check]**：
    -   動作：針對 SLC 區塊 Page 4 與 TLC 區塊 Page 12，標記為空白頁（`b43_is_blank_page=1`），並使用 `inject_UECC` 注入 UECC 錯誤。透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x0B` (`BE_STATUS_MEDIA_SCAN_BLOCK_FOLD_EMPTY_FOR_EPC`)，代表韌體識別出空白頁存在 UECC 錯誤（EPC 異常）。

9.  **[Case13_Good_BEC_Unfold_Check]**：
    -   動作：針對 SLC 區塊與 TLC 區塊的 Page 0，不注入任何錯誤，標記為非空白頁（`b43_is_blank_page=0`）。透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x0D` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_FOR_GOOD_BEC`)，代表韌體識別出區塊 BEC 良好，無需摺疊。

10. **[Case14_Temp_Unfold_Check]**：
    -   動作：執行 HW_RESET 後，設定 NAND 溫度為 20°C（Die 0）與 85°C（Controller）。透過 `issue_D08E` 設定 `XTEMP_DELTA_TH=1` 與 `VALLEY_CENTER_EC_TH=0xFFFF`（高閾值）。在 SLC 區塊 Page 0 注入 150 個 Error Bits。透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status` 及 `diff_ec`, `arc_offset`, `center_ec` 數值。
    -   預期結果：`media_scan_status` 必須等於 `0x0E` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_FOR_TEMP`)，代表韌體在特定溫度與高 EC 閾值設定下，識別出區塊可解摺疊。

11. **[Case15_Valley_Offset_Center_EC_Unfold_Check]**：
    -   動作：透過 `issue_D08E` 設定 `VALLEY_DIFFEC_TH=0xFFFF`, `VALLEY_OFST_TH=0xFF`, `VALLEY_CENTER_EC_TH=0xFFFF`（所有閾值設為最大）。在 SLC 區塊 Page 0 注入 150 個 Error Bits。透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status` 及 `diff_ec`, `arc_offset`, `center_ec` 數值。
    -   預期結果：`media_scan_status` 必須等於 `0x0F` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_FOR_VALLEY_OFFSET_CENTER_EC`)，代表韌體在寬鬆的 Valley 閾值設定下，識別出區塊可解摺疊。

12. **[Case16_Empty_Unfold_Check]**：
    -   動作：針對 SLC 區塊 Page 4 與 TLC 區塊 Page 12，標記為空白頁（`b43_is_blank_page=1`），不注入任何錯誤。透過 `issue_4028` 觸發媒體掃描，讀取回應 Payload 中的 `media_scan_status`。
    -   預期結果：`media_scan_status` 必須等於 `0x10` (`BE_STATUS_MEDIA_SCAN_BLOCK_UNFOLD_EMPTY`)，代表韌體識別出區塊為正常空白，可解摺疊。