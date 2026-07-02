# Test Spec: UFS 4.1 Device Descriptor & Feature Support Enumeration Verification

## Verification Criterion (VC)
驗證 UFS 裝置在 UFS Spec 4.1 規範下的硬體能力宣告與韌體支援狀態：透過讀取 Device Descriptor (DevDesc) 確認裝置基本屬性（如 LUN 數量、Boot 使能、ICC Level、Write Booster 支援等）；透過讀取 UFS Features Support 確認核心功能（FFU, PSA, Device Life Span, Refresh Op, Temp Warning）的硬體支援位元；透過讀取 Extended UFS Features Support 確認進階功能（Extended Write Booster, Performance Throttling, Advanced RPMB, HID, Barrier, Clear Error History, Fast Recovery Mode, Authenticated Vendor Cmd）的支援狀態；透過讀取 Extended Write Booster Support 確認 Write Booster Buffer 的具體操作模式（Resize, FIFO Partial Flush, Pinned Partial Flush）。此測試為基礎相容性與規格符合性檢查，確保韌體正確解析並回報 4.1 版本特有的功能位元。

## Test Case (TC) Checkpoints
1. [DevDesc_410_Structure_Check]：
   - 動作：呼叫 `api.get_device_descriptor()` 獲取 UFS 裝置描述符，並解析 `api.DeviceDescriptor410` 結構體。重點檢查以下欄位：`b6_number_lu` (Logical Unit 數量), `b7_number_wlu` (Write Logical Unit 數量), `b8_boot_enable` (Boot 功能使能), `b10_init_power_mode` (初始電源模式), `b11_high_priority_lun` (高優先級 LUN), `b14_background_ops_term_lat` (背景操作終止延遲), `b15_init_active_icc_level` (初始活躍 ICC 等級), `b28_device_rtt_cap` (RTT 能力), `b33_queue_depth` (佇列深度), `b36_num_secure_wp_area` (安全寫保護區域數量), `b83_write_booster_buffer_preserve_user_space_en` (WB 緩衝區使用者空間保留使能), `b84_write_booster_buffer_type` (WB 緩衝區類型), `l85_num_shared_write_booster_buffer_alloc_units` (共享 WB 緩衝區配置單元數)。
   - 預期結果：所有欄位必須為有效的 UFS 4.1 定義值。特別是 `b84_write_booster_buffer_type` 與 `l85` 必須反映硬體實際配置的 Write Booster 緩衝區大小與類型，`b33_queue_depth` 必須大於 0 以確認佇列功能正常，`b8` 與 `b9` 必須符合裝置的 Boot 與描述符存取安全設定。

2. [UFS_Features_Support_410_Check]：
   - 動作：呼叫 `api.get_ufs_features_support()` 獲取 UFS Features Support 位元組，並解析 `api.UFSFeaturesSupport410` 結構體。檢查以下位元：`u0_ffu` (Firmware Update), `u1_psa` (Power State Awareness), `u2_device_life_span` (Device Life Span Estimation), `u3_refresh_op` (Refresh Operation), `u4_too_high_temp` (Too High Temperature Warning), `u5_too_low_temp` (Too Low Temperature Warning), `u6_extended_temp` (Extended Temperature Range)。
   - 預期結果：`u0_ffu` 與 `u1_psa` 通常應為 1 (支援)。`u2` 至 `u6` 的位元狀態必須與裝置硬體溫度感測器與電源管理單元的能力一致。若裝置支援溫度警告，`u4` 或 `u5` 應設為 1。

3. [Extended_UFS_Features_Support_410_Check]：
   - 動作：呼叫 `api.get_extended_ufs_features_support()` 獲取 Extended UFS Features Support 位元組，並解析 `api.ExtendedUFSFeaturesSupport410` 結構體。重點檢查 UFS 4.1 新增或擴充的功能位元：`u8_write_booster` (Write Booster 支援), `u9_performance_throttling` (效能節流), `u10_adv_rpmb` (Advanced RPMB), `u12_device_level_exception_warning` (裝置層級異常警告), `u13_hid` (Host Initiated Data Integrity), `u14_barrier` (Barrier Command), `u15_clear_error_history_functionality` (清除錯誤歷史), `u18_fast_recovery_mode` (快速恢復模式), `u19_rpmb_authenticated_vendor_cmd` (RPMB 認證 Vendor Command)。
   - 預期結果：`u8_write_booster` 必須與 DevDesc 中的 WB 配置對應。`u19_rpmb_authenticated_vendor_cmd` 若為 1，代表韌體支援透過 RPMB 通道進行認證的 Vendor Command，這是 4.1 安全增強功能。`u15` 若為 1，代表韌體支援透過特定命令清除錯誤歷史記錄。

4. [Extended_Write_Booster_Support_410_Check]：
   - 動作：呼叫 `api.get_extended_write_booster_support()` 獲取 Extended Write Booster Support 位元組，並解析 `api.ExtendedWriteBoosterSupport410` 結構體。檢查以下位元：`u0_write_booster_buffer_resize` (WB 緩衝區調整大小), `u1_fifo_partial_flush_mode` (FIFO 部分刷新模式), `u2_pinned_partial_flush_mode` (Pinned 部分刷新模式)。
   - 預期結果：這些位元定義了 Write Booster 緩衝區的管理機制。若 `u0` 為 1，代表韌體支援動態調整 WB 緩衝區大小；若 `u1` 或 `u2` 為 1，代表支援相應的 Partial Flush 模式以優化寫入效能與資料完整性。這些狀態必須與硬體控制器對 WB 緩衝區的實際控制邏輯一致。