# Test Spec: UFS Host Controller Suspend Timer Configuration Verification

## Verification Criterion (VC)
驗證 UFS 主機控制器（Host Controller）的電源管理暫存器配置機制，特別是 `SUSPEND_SCALE`（掛起時間比例因子）的寫入與讀回一致性：確認透過 `HwSetting` API 單欄位模式（Single Field Style）將 `SUSPEND_SCALE` 設定為數值 5 後，硬體暫存器能正確鎖存該值，且後續讀取操作能返回預期的 5，同時驗證 `SUSPEND_TIMER` 暫存器在僅修改 `SUSPEND_SCALE` 的情境下保持其原有狀態不變，確保硬體設定的隔離性與寫入有效性。

## Test Case (TC) Checkpoints
1. [Suspend_Scale_Write_Read_Back_Check]：
   - 動作：初始化 `HwSetting` 實例，首先透過 `get_local_val` 讀取當前 `SUSPEND_SCALE` 與 `SUSPEND_TIMER` 的本地緩存值（作為基準狀態）。接著，呼叫 `set_to_device` 並指定 `api.HwSettingField.SUSPEND_SCALE` 為 5，將此設定寫入硬體暫存器。寫入完成後，再次呼叫 `get_local_val` 分別讀取 `SUSPEND_SCALE` 與 `SUSPEND_TIMER` 的當前值。
   - 預期結果：`SUSPEND_SCALE` 的讀回值必須嚴格等於 5，證明硬體暫存器已正確接收並儲存該比例因子設定；`SUSPEND_TIMER` 的讀回值必須與寫入操作前的基準值完全一致，證明單欄位寫入操作未對其他並行電源管理參數產生副作用或意外覆寫。