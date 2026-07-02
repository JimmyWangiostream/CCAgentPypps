# Test Spec: EM1 LUN UECC Injection & Unmap Overlap Read Failure Test

## Verification Criterion (VC)
驗證在 Enhanced Memory Type 1 (EM1) LUN 上，當特定 LBA 範圍被注入不可修復的 UECC 錯誤，且該範圍部分 LBA 隨後被 Unmap 指令標記為無效時，Host 發起包含這些「錯誤且已 Unmap」LBA 的連續讀取請求，UFS 裝置必須正確返回 `TARGET_FAILURE` 狀態碼、`CHECK_CONDITION` SCSI 狀態以及 `MEDIUM_ERROR` Sense Key，以確認韌體在處理混合了物理損壞與邏輯無效區域的讀取請求時，能正確識別並報告硬體級別的數據完整性錯誤，而非錯誤地將其視為邏輯無效或正常數據。

## Test Case (TC) Checkpoints
1. [EM1_Configuration_and_Data_Flush]：
   - 動作：透過 `config_lun` 函數配置 LUN，隨機選取一個 EM1 LUN (`self.TestEM1Lun`) 並分配 Allocation Units；關閉背景操作 (BG_OP_EN) 以確保寫入行為可控；針對該 EM1 LUN 從 LBA 0 開始順序寫入 23050 個 LBA 的資料（chunk size 為 WRITE_6_MAX_LBA，FUA=1）；執行兩次 StartStopUnit (SSU) 命令，分別設定 power_condition 為 0x02 (Active/Idle) 和 0x01 (Low Power)，並等待隊列清空，確保所有資料已強制刷新至 NAND Flash。
   - 預期結果：EM1 LUN 配置成功；23050 LBA 的資料完整寫入並持久化至 NAND；SSU 命令執行無誤，裝置進入穩定的電源狀態，為後續錯誤注入提供乾淨的物理基礎。

2. [UECC_Injection_on_EM1_LWP]：
   - 動作：定義注入 LBA 列表 `injectUECC_list`，包含 LBA 13098 至 13121（共 24 個 LBA）；針對列表中的每個 LBA，透過 `get_PCA_and_print` 獲取其對應的物理地址 (PCA/L2P_PCA)；呼叫 `inject_UECC` 函數，該函數透過 `direct_write` 向該物理頁面寫入全 0xAA 的 payload（共 4 blocks, 16KB），從而覆蓋原始數據並導致 ECC 校驗失敗，產生不可修復的 UECC 錯誤。
   - 預期結果：指定的 24 個 LBA 對應的 NAND 物理頁面數據被替換為 0xAA；由於 0xAA 模式與原始隨機數據不符，硬體 ECC 引擎在讀取時將檢測到 UECC 錯誤；這些 LBA 在物理層面現在包含無效數據。

3. [Unmap_Overlap_Region]：
   - 動作：針對 LBA 13107 執行 Unmap 命令，長度為 12 個 LBA（即覆蓋 LBA 13107 至 13118）；將此 Unmap 命令加入命令隊列並發送；記錄寫入資訊。此操作在邏輯層面將這 12 個 LBA 標記為「無效/未定義」，儘管它們在物理上仍存有之前注入的 UECC 錯誤數據。
   - 預期結果：LBA 13107-13118 在邏輯映射表中被標記為 Unmap 狀態；物理層面的 UECC 錯誤數據仍然存在但未在邏輯上被立即清除，形成「邏輯無效但物理損壞」的重疊狀態。

4. [Read_Failure_Verification_on_Overlap_LBAs]：
   - 動作：發起一個 Read10 命令，從 LBA 13094 開始，長度為 72 個 LBA（覆蓋 LBA 13094 至 13165）；此讀取範圍涵蓋了：
     - LBA 13094-13097：正常數據（未注入錯誤，未 Unmap）。
     - LBA 13098-13106：注入 UECC 但未 Unmap 的區域。
     - LBA 13107-13118：注入 UECC 且被 Unmap 的重疊區域。
     - LBA 13119-13165：正常數據（未注入錯誤，未 Unmap）。
   - 執行讀取並捕獲響應，檢查 `response.upiu.b6_response`、`response.upiu.b7_status` 以及 `response.b32_sense_data.b2_sense_key`。
   - 預期結果：讀取命令必須失敗；`b6_response` 必須等於 `TARGET_FAILURE`；`b7_status` 必須等於 `CHECK_CONDITION`；`b2_sense_key` 必須等於 `MEDIUM_ERROR`。這證明即使部分 LBA 被 Unmap，只要讀取範圍內包含物理層面的 UECC 錯誤，裝置仍優先報告硬體數據完整性錯誤，而非忽略它或僅報告邏輯錯誤。

5. [Control_Read_Verification]：
   - 動作：發起兩組 Read10 命令以驗證非問題區域的正常行為：
     - 第一組：讀取 LBA 0 至 13095（共 13096 個 LBA，長度均為 1），這些 LBA 未受 UECC 注入或 Unmap 影響。
     - 第二組：讀取 LBA 13124 至 13124+9925（共 9926 個 LBA，長度均為 1），這些 LBA 位於注入範圍之後，未受影響。
   - 執行這些讀取命令。
   - 預期結果：這兩組讀取命令應成功完成，返回 `GOOD_STATUS` 或無錯誤響應，證明測試腳本的其他部分未破壞裝置的正常讀取功能，且確認了錯誤僅限於注入的特定 LBA 範圍。