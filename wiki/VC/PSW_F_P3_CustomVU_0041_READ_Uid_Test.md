# Test Spec: UFS Multi-CE UID Consistency & Hardware Topology Verification

## Verification Criterion (VC)
驗證 UFS 裝置在多個 Chip Enable (CE) 通道下的硬體拓撲一致性與 UID 唯一性：Case 01 確認當 CE 數量大於等於 1 時，Health Report 中的 CE0 Flash ID 必須與物理 Die 0 的 UID 完全匹配，且該 Die 的 CE/CH/CPU 索引值分別為 0/0/0；Case 02 確認當 CE 數量大於等於 2 時，CE1 的 Flash ID 與物理 Die 1 UID 匹配，且索引值為 1/0/0；Case 03 確認當 CE 數量大於等於 4 時，CE2 與 CE3 的 Flash ID 分別與物理 Die 2 和 Die 3 的 UID 匹配，且索引值分別為 2/0/0 和 3/0/0。此測試旨在確保韌體讀取的 Health Report 數據與 Vendor Command 0x4061 返回的硬體物理 UID 在邏輯映射與物理實體上完全一致，無拓撲錯位。

## Test Case (TC) Checkpoints
1. [Case01_CE0_UID_Match_Check]：
   - 動作：呼叫 `project_api.get_health_report()` 獲取 Health Report payload，並透過 `get_flash_setting()` 讀取 `Max_Fdevice` 確認 CE 數量。若 `ce_num >= 1`，則呼叫 `project_api.issue_4061_to_get_uid()` 獲取 UID 回應，並比對 `health_report.flash_id_ce0.payload` 是否等於 `uid.uid_of_physical_die0.payload`。同時檢查 `uid.ce_die0.value`、`uid.ch_die0.value`、`uid.cpu_die0.value` 的數值。
   - 預期結果：若 CE 數量 >= 1，`health_report.flash_id_ce0.payload` 必須嚴格等於 `uid.uid_of_physical_die0.payload`；且 `uid.ce_die0.value` 必須等於 0，`uid.ch_die0.value` 必須等於 0，`uid.cpu_die0.value` 必須等於 0。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

2. [Case02_CE1_UID_Match_Check]：
   - 動作：在確認 `ce_num >= 2` 的前提下，比對 `health_report.flash_id_ce1.payload` 與 `uid.uid_of_physical_die1.payload`。同時檢查 `uid.ce_die1.value`、`uid.ch_die1.value`、`uid.cpu_die1.value` 的數值。
   - 預期結果：`health_report.flash_id_ce1.payload` 必須嚴格等於 `uid.uid_of_physical_die1.payload`；且 `uid.ce_die1.value` 必須等於 1，`uid.ch_die1.value` 必須等於 0，`uid.cpu_die1.value` 必須等於 0。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。

3. [Case03_CE2_CE3_UID_Match_Check]：
   - 動作：在確認 `ce_num >= 4` 的前提下，分別比對 `health_report.flash_id_ce2.payload` 與 `uid.uid_of_physical_die2.payload`，以及 `health_report.flash_id_ce3.payload` 與 `uid.uid_of_physical_die3.payload`。同時檢查對應 Die 的 CE/CH/CPU 索引值。
   - 預期結果：
     - 對於 CE2/Die2：`health_report.flash_id_ce2.payload` 必須等於 `uid.uid_of_physical_die2.payload`；且 `uid.ce_die2.value` 必須等於 2，`uid.ch_die2.value` 必須等於 0，`uid.cpu_die2.value` 必須等於 0。
     - 對於 CE3/Die3：`health_report.flash_id_ce3.payload` 必須等於 `uid.uid_of_physical_die3.payload`；且 `uid.ce_die3.value` 必須等於 3，`uid.ch_die3.value` 必須等於 0，`uid.cpu_die3.value` 必須等於 0。
     - 任一條件不符，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL`。