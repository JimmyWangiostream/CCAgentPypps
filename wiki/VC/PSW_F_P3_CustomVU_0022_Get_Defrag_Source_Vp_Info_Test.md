# Test Spec: UFS Write Booster (WB) GC Data Integrity Verification via Vendor Command

## Verification Criterion (VC)
驗證 UFS 裝置在 Write Booster (WB) 緩衝區滿載並觸發 Flush 至 Flash 的過程中，韌體執行的垃圾回收 (GC) 或資料遷移行為是否正確。具體而言，測試邏輯透過 Vendor Command `0xD0FD` 暫停背景操作以確保狀態穩定，隨後使用 Vendor Command `0x40DD` 查詢特定 VB (Virtual Block) 的 Defrag/GC 來源 VP (Virtual Page) 資訊。最後，透過 Direct Read 指令分別讀取 GC 目標節點 (Target Node) 與來源節點 (Source VP) 的第一頁 (First Page) 資料，並比對前 4KB 內容。預期結果為兩者資料完全一致，證明 WB Flush 後的資料完整性與 GC 遷移邏輯正確無誤。

## Test Case (TC) Checkpoints
1. [WB_Flush_Trigger_and_BKOPS_Suspend_Check]：
   - 動作：
     1. 配置 LUN 0 為 Normal Memory Type，LUN 1 為 Enhanced 1 (EM1) Memory Type，各分配總容量的一半，並設定 WB Buffer 為 Shared 模式。
     2. 啟用 Write Booster (`WRITEBOOSTER_EN`)，並透過隨機寫入 (Random Write, 64MB~128MB) 填充 WB 緩衝區，直到 `AVAILABLE_WRITEBOOSTER_BUFFER_SIZE` 屬性讀回為 `0x0`。
     3. 啟用 WB Buffer Flush (`WRITEBOOSTER_BUFFER_FLUSH_EN`)，輪詢 `WRITEBOOSTER_BUFFER_FLUSH_STATUS` 屬性，直到狀態碼為 `0x01` (表示 Flush 進行中或已完成)。
     4. 發送 Vendor Command `0xD0FD` 且參數為 `0x00`，強制禁用所有背景操作 (Background Operations)，以凍結韌體狀態。
     5. 呼叫 `show_vb_info` 取得一個屬於 Normal Group 的 VB 號碼 (`vb`)。
   - 預期結果：
     - WB 緩衝區必須成功填滿並觸發 Flush 機制。
     - `WRITEBOOSTER_BUFFER_FLUSH_STATUS` 必須正確反映 Flush 狀態。
     - Vendor Command `0xD0FD` 必須成功執行，確保後續查詢時無背景 GC 干擾。
     - 成功取得有效的 Normal Group VB 號碼。

2. [GC_Source_VP_Info_Query_Check]：
   - 動作：
     1. 針對步驟 1 取得的 VB 號碼，發送 Vendor Command `0x40DD`。
     2. 解析回傳的 `sourcevpInfo` 結構，獲取來源 Virtual Page 的詳細資訊，包括：VB 號碼 (`vbnum`)、Die ID (`die`)、Plane ID (`plane`)、Page Index (`page`) 以及 VP Index (`vpindex`)。
   - 預期結果：
     - Vendor Command `0x40DD` 必須成功回傳有效的 `sourcevpInfo`。
     - 回傳的 Die、Plane、Page 及 VP Index 必須為有效的硬體位址參數，代表該 VB 在 GC 或 Defrag 過程中的資料來源位置。

3. [Direct_Read_GC_Target_vs_Source_Data_Integrity_Check]：
   - 動作：
     1. **讀取 GC 目標節點 (Target Node)**：
        - 建構 PCA (Physical Command Argument)：操作碼 `0x20000` (Direct Read)，模式設為 SLC (`b4_mode = 2`)，CE 設為步驟 1 取得的 VB 對應 Die，Plane 設為對應 Plane，Block 設為步驟 1 取得的 VB 號碼，fPage 設為 `0` (第一頁)。
        - 執行 `api.direct_read` 讀取 1 Block (4KB)，包含 FW Spare 資料，存入 `dire_read_payload`。
     2. **讀取來源節點 (Source VP)**：
        - 建構 PCA：操作碼 `0x20000`，模式設為 SLC (`b4_mode = 1`，註：程式碼中寫死為 1，通常 SLC 為 1 或 2 視 Vendor 定義，此處依程式碼邏輯)，CE 設為 `sourcevpInfo.die`，Plane 設為 `sourcevpInfo.plane`，Block 設為 `sourcevpInfo.vbnum`，fPage 計算為 `(sourcevpInfo.page << 5) | (sourcevpInfo.vpindex * 8)`。
        - 執行 `api.direct_read` 讀取 1 Block (4KB)，包含 FW Spare 資料，存入 `dire_read_payload1`。
     3. **資料比對**：
        - 呼叫 `compare_first_4k_bytes` 函數，比對 `dire_read_payload` 與 `dire_read_payload1` 的前 4KB 資料。
   - 預期結果：
     - 兩次 Direct Read 必須成功讀取到有效的 Flash 資料。
     - `compare_first_4k_bytes` 必須回傳 `True`。
     - 這代表 GC 目標節點的第一頁資料與來源 VP 的資料完全一致，驗證了 WB Flush 後資料寫入 Flash 的正確性以及後續可能的 Defrag/GC 遷移邏輯中資料未損壞。