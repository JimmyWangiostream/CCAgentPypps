# Test Spec: UFS Link Layer DME Attribute Consistency Verification (VU 0x4049 vs DME GET)

## Verification Criterion (VC)
驗證 UFS 主機端韌體透過 Vendor Command (VU 0x4049) 獲取的 UIC 配置資訊，與透過 DME (Device Management Entity) GET 命令從 PHY 層讀取的 MIB (Management Information Base) 屬性值在硬體實現上的一致性。重點驗證包括：
1. **基礎配置一致性**：VU 0x4049 回傳的 payload 前 21 bytes 必須與 DME GET 讀取的 MIB 屬性序列完全匹配。
2. **MPHY 進階能力解析正確性**：特別針對 `MPHY_RX_Advanced_Granularity_Cap` (0x98) 屬性，驗證韌體是否能正確解碼其 Bit 0 (支援位) 與 Bit 1-2 (步進值)，並確認該解碼後的結構化數據與 VU 回傳的原始數據邏輯一致。
3. **硬體狀態同步性**：確認韌體內部維護的 UIC 配置模型與 PHY 硬體實際報告的 MIB 狀態無衝突，確保 Link Training 與 Power Management 參數的準確性。

## Test Case (TC) Checkpoints
1. [VU_0x4049_Configuration_Extraction]：
   - 動作：執行 `project_api.issue_4049_get_UIC_configuration()` 發送 Vendor Command 0x4049，獲取 UIC 配置結構體 `UIC_configuration`，並將其 payload 轉存至檔案 `VU0x4049`。
   - 預期結果：成功獲取非空的 UIC 配置 payload，且該 payload 包含完整的 PHY 屬性列表，為後續比對提供基準數據 (Golden Data)。

2. [DME_MIB_Attribute_Scanning]：
   - 動作：遍歷 `testAttributeslist` 中定義的所有 MIB 屬性 ID (如 `PA_HIBERN8TIME`, `RX_Min_ActivateTime_Capability` 等)。針對每個屬性，設定 `attr_get_type` 為 `PEER | NORMAL`，`sel` 為 0，呼叫底層 C API `DME_Get` 讀取硬體暫存器值。
   - 動作細節：若當前屬性為 `MPHY_RX_Advanced_Granularity_Cap` (0x98)，則執行位元解碼：Bit 0 提取為 `rx_adv_gran_supported`，Bit 1-2 提取為 `rx_adv_gran_step`，並將這兩個解碼後的整數值依序加入 `byte_list`。對於其他所有屬性，直接將讀取的原始 `value` 加入 `byte_list`。
   - 預期結果：所有 DME GET 呼叫返回成功 (errcode 為 0)，且 `byte_list` 中累積的數據序列反映了 PHY 硬體當前報告的 MIB 狀態。特別是 `MPHY_RX_Advanced_Granularity_Cap` 的處理邏輯必須正確分離支援位與步進值，確保數據結構與 VU 回傳格式對應。

3. [UIC_Configuration_Mismatch_Check]：
   - 動作：將 `byte_list` 轉換為 `bytearray` 並封裝為 `UIC_from_DME_get` 對象。比較 `UIC_from_DME_get.payload[0:21]` 與 `UIC_configuration.payload[0:21]`。
   - 預期結果：兩者必須完全相等。若不相等，觸發 `SIGHTING_FAIL_DATA_COMPARE_FAIL` 異常。這確認了韌體透過 VU 命令獲取的邏輯配置與 PHY 硬體透過 DME 協議報告的物理屬性在關鍵的前 21 bytes (通常包含核心 PHY 參數與能力集) 上是嚴格同步的，無硬體 Bug 或韌體解析錯誤。