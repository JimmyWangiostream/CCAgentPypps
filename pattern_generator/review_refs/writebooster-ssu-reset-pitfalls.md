# WriteBooster + SSU Reset Pitfalls

Session reference: PF010_0310_WriteBooster_SSU_Rst code review (2026-06-24)

## CRITICAL — Runtime Crashes

### 1. Custom Helper Methods Not Defined
```python
# BAD: calls undefined method
desc_data = self._read_config_desc()  # AttributeError at runtime
```
Always verify custom helpers exist. Prefer standard APIs: `api.get_device_descriptor()`, `api.get_config_descriptors()`, `ExecuteCMD.ReadDescriptor()`.

### 2. Wrong Offset in Config Descriptor Read
```python
# BAD: reading offset 0x01 instead of proper field location
b_wb_type = desc_data[0]  # wrong byte — b84 in DevDesc, not header[0]
struct.unpack_from("<I", desc_data, 0x01)  # wrong offset — l18 is at unit offset 72
```

## MAJOR — False Positive Risks

### 3. Post-Reset Flag Without Assert (False Positive)
```python
# BAD: only logs, never raises on wrong value
val = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
logger.info(f"fWriteBoosterEn after reset = {val}")
```
UFS Spec 6.3.4: all WB flags are VOLATILE. After ANY reset, MUST be 0. Reading without assert = test passes on buggy firmware.

### 4. Random LBA Reuse in Burn-In
```python
# BAD: random LBA may collide, corrupting write_record
lba = random.randint(0, self.max_lba - 256)
api.random_write(..., write_record=self.write_record, need_compare=True)
```
Same LBA written twice → write_record lookup returns wrong data → compare fails or passes incorrectly.

### 5. Wrong SSU Power Condition Semantics
```python
# BAD: PC=0x01 + start=0x01 is NOT power cycle
ssu.assign(lun=0, immed=0, power_condition=0x01, no_flush=0, start=0x01)  # "Power cycle" ← WRONG comment
```
PC=0x01+start=0x01 = START only. Power cycle = STOP (0,0) + power-down + START.

## MEDIUM — Code Quality

### 6. Manual Config Descriptor Write
```python
# BAD: manual bytearray + vendor cmd
desc_data = bytearray(0x40)
desc_data[0x00] = 0x01
resp = vf.modify_desc_attr_flag(QuerryType=ed.Vendor_CMD_Query_Func.VENDOR_CMD_QUERY_DESCRIPTOR, ...)
```
Use `api.ConfigDescriptor410()` + `ExecuteCMD.WriteDescriptor()` + `cmd.set_desc()` instead.

### 7. write_record Not Initialized in pre_process
```python
# BAD: relies on hasattr guard
write_record=self.write_record if hasattr(self, 'write_record') else []
```
Initialize in pre_process: `self.write_record = []`

### 8. fDeviceInit Not Checked After Reset
After every reset path (SSU/POR/LINKSTARTUP), must verify:
```python
val = api.read_flag(idn=api.FlagIDN.DEVICE_INIT)
if val != 1:
    raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(...)
```
