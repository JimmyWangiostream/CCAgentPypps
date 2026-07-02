# Test Spec: UFS Vendor Command RPMB Key Clear & Factory Reset Sequence

## Verification Criterion (VC)
驗證 UFS 韌體在 Vendor Command 模式下的安全存儲區（RPMB）狀態重置與系統級恢復機制：Case 01 確認透過 Vendor Command 清除 RPMB Region 0 的加密金鑰後，系統能正確進入 Vendor Mode 並執行金鑰擦除操作；Case 02 確認在清除金鑰後，透過 Vendor Command 備份描述符屬性標誌（Descriptor Attribute Flag）以保留當前硬體配置狀態，並執行 Buffer Factory Reset 將內部緩衝區與邏輯狀態恢復至出廠預設值，確保後續測試環境的乾淨性與一致性。

## Test Case (TC) Checkpoints
1. [Case01_VendorMode_RPMB_Key_Clear_Check]：
   - 動作：呼叫 `access_vendor_mode()` 進入 Vendor Command 模式，隨後呼叫 `vuc_clear_rpmb_key(RPMBRegion.REGION_0)` 針對 RPMB 的 Region 0 執行金鑰清除指令。
   - 預期結果：UFS 裝置必須成功進入 Vendor Mode 並接受 Vendor Command；RPMB Region 0 的加密金鑰必須被硬體或韌體層級擦除，導致該區域的 MAC 驗證失效或金鑰寄存器歸零，為後續的 Factory Reset 或金鑰重新初始化做準備。

2. [Case02_DescAttr_Backup_Factory_Reset_Check]：
   - 動作：在 Vendor Mode 下，呼叫 `vuc_backup_desc_attr_flag()` 讀取並備份當前 UFS 裝置的描述符屬性標誌（Descriptor Attribute Flag），接著呼叫 `buffer_factory_reset()` 執行緩衝區工廠重置。
   - 預期結果：描述符屬性標誌（如 LUN 配置、電源管理狀態、錯誤標記等）必須被成功讀取並保存至韌體內部暫存區或 NVMe/Vendor 特定存儲區；`buffer_factory_reset` 必須將 UFS 韌體內部的動態緩衝區、邏輯映射表（L2P）暫態狀態及錯誤計數器重置為出廠預設值，確保裝置處於一個已知且乾淨的初始狀態，同時不影響已備份的描述符配置。