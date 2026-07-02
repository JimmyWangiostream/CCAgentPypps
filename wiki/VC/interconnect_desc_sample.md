# Test Spec: UFS Interconnect Descriptor Retrieval & Validation (410)

## Verification Criterion (VC)
驗證 UFS 主機控制器與裝置間的 UniPro 層級互連描述符（Interconnect Descriptor）讀取機制與版本資訊正確性：確認透過 `api.get_interconnect_descriptor()` API 成功獲取硬體描述符結構體，並驗證其關鍵欄位（B0 Length, B1 Descriptor IDN, W2 UniPro Version, W4 MPHY Version）符合 UFS 規範定義的硬體實體層與傳輸層版本特徵，確保主機端韌體能正確識別當前 UFS 鏈路的物理與邏輯配置參數。

## Test Case (TC) Checkpoints
1. [Interconnect_Desc_Read_Verify]：
   - 動作：呼叫 `api.get_interconnect_descriptor()` 從 UFS 裝置讀取 Interconnect Descriptor 結構體，並將返回的 `api.InterconnectDescriptor` 物件強制轉換為 `api.InterconnectDescriptor410` 型別，隨後記錄並輸出以下四個特定欄位的數值：
     1. `b0_length`：描述符的總長度（Byte）。
     2. `b1_descriptor_idn`：描述符識別碼編號（Descriptor ID Number）。
     3. `w2_bcd_unipro_version`：UniPro 協議版本號（BCD 編碼）。
     4. `w4_bcd_mphy_version`：MPHY 物理層版本號（BCD 編碼）。
   - 預期結果：
     - `b0_length` 必須等於 0x0010 (16 Bytes)，符合 UFS 規範中 Interconnect Descriptor 的固定長度定義。
     - `b1_descriptor_idn` 必須等於 0x01，代表此為 Interconnect Descriptor。
     - `w2_bcd_unipro_version` 必須為有效的 UniPro 版本（例如 0x1000 代表 UniPro 1.0 或更高，具體取決於硬體支援），且非 0xFFFF 或錯誤碼。
     - `w4_bcd_mphy_version` 必須為有效的 MPHY 版本（例如 0x1000 代表 MPHY 1.0 或更高），且非 0xFFFF 或錯誤碼。
     - 整個讀取過程無異常拋出，證明主機控制器能正確解析 UFS 裝置的硬體描述符資訊。