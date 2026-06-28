# Project Defaults (default.md) — AUTO-GENERATED, do not hand-edit

> Merge of ModelDefault (base) + UserPrompt (overrides) + CustomerReq constraints.
> Priority: **UserPrompt > ModelDefault**. Apply these when the TC flow omits a detail.
> Sources: wiki/UserPrompt/, wiki/ModelDefault/, wiki/conflicts.md (audit).
> Regenerate: `python generate_pattern.py build-defaults`

## (1) UserPrompt overrides — HIGHEST priority (use when TC is silent)
# UserPrompt

## 使用說明
本文件用於制定使用者習慣的細節說明, 當TC沒有敘述到flow細節時, 參考這一份實作

## 未指定時參照:
- **LUN**：MaxCapacity的Enabled Lun

_← UserPrompt (overrides ModelDefault)_

## (2) CustomerReq constraints (Rule 1 — CustomerReq > Spec)
- **WriteBooster LUN Restriction**: Reject WriteBooster Attribute/Flag writes on LUN > 7, Boot LUNs, or Well-Known LUNs with `invalid INDEX` response  _← CustomerReq_

## (3) Resolved overrides (audit — from conflicts.md)
- **Default LUN Selection**: ModelDefault ``TestNormalLun = 0` must NOT be used as default` SUPERSEDED → use `default LUN = MaxCapacity Enabled LUN`. When TC flow does not specify a LUN, the test framework shall enumerate all enabled Normal LUNs, read `dNumAllocUnits` from each Unit Descriptor, and select the LUN with the highest value  _← UserPrompt wins_

## (4) ModelDefault base (used only when TC AND UserPrompt are silent)
_Items resolved in (3) above are superseded._

### data_operations  _← ModelDefault_
# Default Data Operation Parameters

Used when TC flow specifies read/write operations but omits parameter details.

## sequential_write()

**Default Parameters:**
```python
# When chunk_size not specified
chunk_size = api.BLOCK4K_SIZE_128M_BYTE  # 128 MB chunks (optimal for performance)

# When fua (Force Unit Access) not specified
fua = 0  # Disabled by default (allows write caching)

# When need_compare not specified  
need_compare = False  # Skip hardware verify unless data integrity is critical

# When compare_method not specified
compare_method = api.CompareMethod.HW_COMPARE  # Use hardware comparison when available

# When write_record not specified
write_record = api.get_empty_write_record()  # Create new record for tracking
```

**Rationale:**
- Large chunk sizes (128MB) reduce test execution time for non-critical patterns
- FUA disabled allows firmware write optimization (WriteBooster)
- Hardware compare is faster and more reliable than software verification
- Write record tracks all operations for debugging and analysis

**Related Spec:** Section 11.3.15 (WRITE command)

---

## sequential_read()

**Default Parameters:**
```python
# When chunk_size not specified
chunk_size = api.BLOCK4K_SIZE_128M_BYTE  # 128 MB chunks

# When compare_method not specified
compare_method = api.CompareMethod.HW_COMPARE  # Hardware verify
```

---

## lba_to_pba() — LBA to Physical Block Address Conversion

**Default Parameters:**
```python
# LUN defaults when operating on specific LU types:
TestNormalLun = 0      # General data storage
TestEM1Lun = 1         # Enhanced Memory 1 (slower, reliable)
TestWBLun = 2          # WriteBooster LUN
TestGC_Lun = 3         # Garbage Collection
TestTemperatureLun = 4 # Temperature monitoring
```

---

## Data Size Defaults

When data size/block count not specified:

```python
# Common test data sizes (in bytes)
MINIMAL_TEST_SIZE = api.BLOCK4K_SIZE_128M_BYTE        # ~128 MB (small test)
STANDARD_TEST_SIZE = 10 * api.BLOCK4K_SIZE_128M_BYTE  # ~1.3 GB (typical)
STRESS_TEST_SIZE = 100 * api.BLOCK4K_SIZE_128M_BYTE   # ~13 GB (extensive)

# VB (Virtual Block) sizing
SLC_VB_SIZE = fw_geometry.l84_vb_size_u0 * 512 // 4096  # SLC block size
TLC_VB_SIZE = fw_geometry.l88_vb_size_u1 * 512 // 4096  # TLC block size
EXCEED_SIZE = 50  # Extra blocks beyond main VB (safety margin)
```

---

## Transfer Parameters

**Default transfer behavior when TC omits specifics:**

```python
# Data alignment
start_lba = 0           # Start from beginning unless specified
total_size = <from above>  # Use appropriate test size tier

# Ordering
allow_out_of_order = False  # Maintain FIFO order by default
max_pending_transfers = 1   # Single outstanding transfer (safe default)

# Timing
timeout_ms = 30000          # 30 second timeout for standard operations
busy_wait_threshold = 100   # Check busy status every 100ms
```

**Spec Reference:** Section 10.7.13 (Data Out Transfer Rules), 25 (SCSI Transport)

### descriptor_operations  _← ModelDefault_
# Default Descriptor, Attribute & Flag Operations

Used when TC specifies attribute/flag changes but omits specific values.

## Attribute Operations

### Common Attributes When Not Specified

```python
# When reading attributes without specifying which ones
api.read_attribute(idn=api.AttributeIDN.PSA_STATE)  # Most commonly checked

# PSA State defaults
PSA_STATE = api.PSAState.PRE_SOLDERING  # After manufacturing
PSA_DATA_SIZE = device_descriptor.l37_psa_max_data_size

# Data Sector Size
DATA_SECTOR_SIZE = 4096  # bytes (standard UFS)

# Boot LU attributes
BOOT_LU_A_ENABLED = True
BOOT_LU_B_ENABLED = True
```

---

## Flag Operations

### Default Flag Settings

```python
# When setting/clearing flags without specific target

# WriteBooster
set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)    # Default: enabled

# Background Operations  
set_flag(idn=api.FlagIDN.BKOPS_RECOMMENDED)  # Default: enabled
set_flag(idn=api.FlagIDN.BKOPS_URGENT)       # Default: NOT urgent unless critical

# Device Init
set_flag(idn=api.FlagIDN.DEVICE_INIT)        # Only set if needed (rare)

# Purge (Secure Erase)
clear_flag(idn=api.FlagIDN.PURGE_ENABLE)     # Default: disabled (risky operation)
```

---

## Query Operation Defaults

When using Query Request/Response without specifics:

```python
# Default query operations
QueryType = Vendor_CMD_Query_Func.VENDOR_CMD_QUERY_ATTRIBUTE  # Most common

# Typical query workflow when TC doesn't specify
def standard_query_flow():
    # 1. Read descriptor first (safe, doesn't modify)
    device_desc = query_descriptor(DescriptorType.DEVICE)
    
    # 2. Then read attributes
    psa_state = query_attribute(AttributeIDN.PSA_STATE)
    
    # 3. Finally modify if needed (rare, requires explicit TC instruction)
```

---

## Descriptor Read Defaults

### Device Descriptor
```python
# Always safe to read, provides baseline info
device_descriptor = api.get_device_descriptor()

# Key fields typically accessed
bNumberLU = device_descriptor.bNumberLU                    # LU count
bBootLunEn = device_descriptor.bBootLunEn                  # Boot support  
l37_psa_max_data_size = device_descriptor.l37_psa_max_data_size
bSecureRemovalType = device_descriptor.bSecureRemovalType  # Erase type
```

### Geometry Descriptor
```python
# Always needed for capacity calculations
geometry_desc = api.get_geometry_descriptor()

# Key fields
bAllocationUnitSize = geometry_desc.bAllocationUnitSize
wManufacturerID = geometry_desc.wManufacturerID
```

### LU Descriptor
```python
# Read for each LU that will be used in test
for lun in [0, 1, 2, 3, 4]:
    lu_desc = api.get_lu_descriptor(lun)
    # Verify LU type and capacity match expectations
```

---

## Mode Page Defaults

### Mode Sense Defaults

When reading mode pages without specifying which:

```python
# Default to reading all supported pages
all_mode_pages = api.read_mode_sense(lun=<target_lun>, pc=0)  # Current values

# Most commonly checked pages
CONTROL_MODE_PAGE = 0x0A       # Device behavior control
ERROR_RECOVERY_PAGE = 0x01     # Retry/error handling
CACHE_MODE_PAGE = 0x08         # Caching policy
```

### Mode Select Defaults

When modifying mode pages:

```python
# Default behavior when updating mode pages
PF_BIT = 1  # Permanent (save to non-volatile)
SP_BIT = 1  # Save parameters (non-volatile storage)

# Default parameter values for common pages
error_recovery = {
    "awre": 1,        # Auto-write reallocate enabled
    "arre": 1,        # Auto-read reallocate enabled
    "tb": 0,          # Transfer block on error disabled
    "rc": 0,          # Read continuous disabled
    "eec": 0,         # Enable error recovery control
    "tur": 0,         # Test unit ready on recovery
}

cache_policy = {
    "cce": 1,         # Cache control enabled
    "dra": 1,         # Disable read-ahead (let firmware optimize)
    "wce": 1,         # Write cache enabled (safe: host responsible for flush)
    "rcd": 0,         # No read cache disable
    "mf": 0,          # Modular
    "rsc": 0,         # Restart/save control
    "fua": 0,         # FUA disabled (allow caching)
    "fuanv": 0,       # FUA non-volatile disable
}
```

**Spec Reference:** Section 11.4 (Mode Pages)

---

## VPD (Vital Product Data) Pages

Default VPD pages when device info needed:

```python
# Always available and safe to read
vpd_supported_pages = api.read_vpd_pages(lun=0)
vpd_device_id = api.read_vpd_pages(page=0x83)  # Device identification
vpd_serial_number = api.read_vpd_pages(page=0x80)

# Query via INQUIRY command (better compatibility)
inquiry_response = api.inquiry(lun=0)
```

**Spec Reference:** Section 11.5 (VPD Pages)

### error_handling  _← ModelDefault_
# Default Error Handling & Recovery Behavior

Used when TC specifies error scenarios but omits handling/recovery details.

## Exception Defaults

### Default Exception Types

When raising exceptions without specific type:

```python
# Most common test failure exceptions (from Script patterns)
SIGHTING_FAIL_DATA_COMPARE_FAIL  # Data mismatch in read-back
SIGHTING_FAIL_TIMEOUT            # Operation exceeded timeout
SIGHTING_FAIL_UNEXPECTED_STATUS  # Command returned unexpected status
SIGHTING_FAIL_HARDWARE_ERROR     # Hardware error detected
```

### Default Error Logging

```python
# Default error reporting pattern
logger.error_fp(message)        # Failure point: used when test fails
logger.error_lb(message)        # Log block: used for data mismatches
logger.flow(step_number, message)  # Flow tracking
logger.info(message)            # General information
```

---

## Data Verification Defaults

### Default Comparison Behavior

When comparing data without specifics:

```python
# Default comparison method
compare_method = api.CompareMethod.HW_COMPARE  # Use hardware

# Hardware comparison advantages:
# - Faster (parallel comparison)
# - More reliable
# - Integrates with device error detection

# Software comparison used only when:
# - HW compare unavailable
# - Comparing against pattern data
# - Debugging specific fields
```

### Default Tolerance

When checking numerical values:

```python
# Default tolerance for comparisons
exact_match_required = True       # No tolerance by default

# Exceptions (use only when explicitly stated):
tolerance_percent = 0.1           # 0.1% tolerance for analog values
tolerance_absolute = 1            # ±1 for counts/indices
```

---

## Command Timeout Defaults

When operation hangs without clear timeout:

```python
# Standard timeout values
TIMEOUT_STANDARD_CMD = 30000   # 30 seconds (read/write/query)
TIMEOUT_LONG_CMD = 60000       # 60 seconds (format/rebuild)
TIMEOUT_VENDOR_CMD = 10000     # 10 seconds (vendor specific)
TIMEOUT_INITIALIZATION = 45000 # 45 seconds (device init)

# Timeout response
on_timeout = raise SIGHTING_FAIL_TIMEOUT  # Fail test on timeout
retry_on_timeout = False  # Don't auto-retry by default
log_timeout_details = True  # Always log timeout info
```

---

## Sense Data Handling

### Default Sense Data Interpretation

When device returns error status:

```python
# Query sense data structure
sense_key = response.sense_data[2]  # Main error category
asc = response.sense_data[12]       # Additional Sense Code
ascq = response.sense_data[13]      # ASCQ (more specific)

# Common sense keys when not specified:
RECOVERED_ERROR = 0x1  # Warning, operation succeeded
NOT_READY = 0x2        # Device not ready
MEDIUM_ERROR = 0x3     # Data error (bad block)
HARDWARE_ERROR = 0x4   # Device hardware fault
ILLEGAL_REQUEST = 0x5  # Invalid command
UNIT_ATTENTION = 0x6   # State change (reset, etc.)
DATA_PROTECT = 0x7     # Write protected
BLANK_CHECK = 0x8      # Unexpected blank area
```

**Spec Reference:** Section 13 (RESPONSE UPIU - Sense Data Format)

---

## Retry Strategy

### Default Retry Behavior

When operation fails without explicit retry instruction:

```python
# Default retry policy
max_retries = 0          # Don't retry by default (fail-fast)
retry_on_timeout = False
retry_on_busy = True     # Retry if device reports BUSY

# Retry timing
retry_delay_ms = 100     # Wait 100ms between retries
exponential_backoff = False  # Use fixed delays

# Only retry when:
# - Explicitly specified in TC
# - Transient error detected
# - Device in BUSY state
```

### Retry Exhaustion

```python
# When max retries exceeded
on_exhaustion = raise SIGHTING_FAIL_<ERROR_TYPE>
log_retry_attempts = True
collect_diagnostic_info = True
```

---

## Hardware Reset Recovery

When hardware reset occurs unexpectedly:

```python
# Default recovery after unexpected reset
auto_reinit = True  # Automatically reinitialize
verify_state_after_reset = True
rebuild_corrupted_structures = True

# Re-initialization sequence
1. Detect reset occurred
2. Query device status
3. Clear any pending commands
4. Restore critical settings
5. Resume test flow
```

---

## Power Loss Recovery

When simulating/testing power loss:

```python
# Default power loss behavior
notify_firmware_before_powerdown = True  # Send notification
allow_pending_writes = False  # Flush before cutting power

# Recovery expectation
verify_data_integrity = True     # Check for corruption
check_journal_consistency = True  # Validate FTL structures
rebuild_indexes = True           # Rebuild if needed

# Acceptable data loss
unwritten_data_loss_ok = True    # Data in cache may be lost
persistent_data_must_be_intact = True  # Committed data safe
```

---

## Thermal/Environmental Faults

When device reports thermal issues:

```python
# Default thermal fault handling
immediate_shutdown = True         # Don't allow overheating
wait_for_cooldown = True         # Pause test
cooldown_target_temp = 70        # Celsius
max_cooldown_time = 300000       # 5 minutes max wait

# If device won't cool:
on_thermal_failure = SIGHTING_FAIL_HARDWARE_ERROR
log_thermal_data = True
```

---

## State Machine Violations

When device enters invalid state:

```python
# Default invalid state handling
fail_on_invalid_state = True     # Strict checking
log_state_transition = True      # Record path to invalid state
attempt_recovery = False         # Don't try to recover
report_state_machine_error = True

# State transition verification
validate_state_transitions = True  # Check against spec
allowed_invalid_paths = []         # None by default
```

**Spec Reference:** Section 7 (Reset, Power-Up and Power-Down State Machines)

### hardware_settings  _← ModelDefault_
# Default Hardware Settings & Configuration

Used when TC specifies hardware configuration but omits specific setting values.

## HwSetting Field Defaults

When modifying hardware settings without explicit values:

```python
# Most commonly configured settings (from Script patterns)

# Inhibition Time (idle timeout)
HwSettingField.INHIBITION_TIME = 180  # seconds

# PSA (Production State Awareness) Configuration
PSA_STATE = api.PSAState.PRE_SOLDERING  # Default after manufacturing
PSA_DATA_SIZE = device_descriptor.l37_psa_max_data_size  # Use device max

# Write Booster
WRITEBOOSTER_ENABLED = True
WRITEBOOSTER_BUFFER_SIZE = auto  # Use device default

# Background Operations
BKOPS_ENABLED = True
BKOPS_FLUSH_ENABLE = True

# Temperature Monitoring
TEMPERATURE_THRESHOLD_HIGH = 85  # Celsius
TEMPERATURE_THRESHOLD_LOW = 0    # Celsius

# Cache Settings
CACHE_MODE = WRITE_BACK  # Default cache policy
CACHE_FLUSH_TIMEOUT = 30  # seconds
```

---

## Device Descriptor Access

When TC needs device info but doesn't specify what to read:

```python
# Default descriptor retrieval (safe to always do)
device_desc = api.get_device_descriptor()
geometry_desc = api.get_geometry_descriptor()
fw_geometry = api.get_fw_geometry()

# Common device info accessed:
device_desc.l37_psa_max_data_size      # PSA capacity
device_desc.bNumberLU                   # Number of logical units
device_desc.bSecureRemovalType          # Secure erase support
```

**Spec Reference:** Section 14 (Descriptors, Flags and Attributes)

---

## Virtual Block (VB) Sizing

When determining VB sizes for test operations:

```python
# Calculate from firmware geometry
flash_setting = get_flash_setting()
slc_vb_size = fw_geometry.l84_vb_size_u0 * 512 // 4096
tlc_vb_size = fw_geometry.l88_vb_size_u1 * 512 // 4096

# Safety margins
exceed_size = 50  # Extra blocks beyond main VB capacity

# Total test allocation
total_test_size = slc_vb_size + exceed_size
```

---

## LUN Configuration Defaults

When configuring logical units for a test:

```python
# Standard LUN allocation (from VPCT test patterns)
TestNormalLun = 0      # Primary data partition
TestEM1Lun = 1         # Enhanced Memory 1 (extra reliable)
TestWBLun = 2          # WriteBooster dedicated LUN
TestGCLun = 3          # Garbage Collection area
TestTemperatureLun = 4 # Temperature monitoring

# LUN type defaults
normal_lu_type = "General Purpose"
em1_lu_type = "Enhanced Reliability"
wb_lu_type = "WriteBooster Cache"

# Common LU counts
min_lun_required = 2   # At least data + EM1
typical_lun_count = 5  # Data + EM1 + WB + GC + Temp
max_lun_count = device_descriptor.bNumberLU  # Device maximum
```

---

## RPMB Configuration

When accessing RPMB (Replay Protected Memory Block) without details:

```python
# Default RPMB region and mode
rpmb_region = RPMBRegion.REGION_0  # Always use region 0 by default

# Key management
rpmb_key = auto_generate_key()  # Generate random key for test
rpmb_key_size = 32  # bytes (256-bit key)

# Write counter reset
clear_rpmb_key = True  # Clear and reset on init (safe default)

# Operation mode
rpmb_mode = "NORMAL"  # Use normal RPMB mode by default
```

**Spec Reference:** Section 12.4 (RPMB — Replay Protected Memory Block)

---

## Erase/Defect Management

When configuring NAND management without specifics:

```python
# Flash defect handling
bad_block_info = api.get_bad_block_information()  # Retrieve existing defects
defragmentation_enabled = True  # Enable auto-defrag
defrag_source_vp = auto  # Let firmware select VPs to defrag

# Format operation defaults
format_type = "QUICK_FORMAT"  # Fast format (no full erase)
keep_user_data = False         # Erase all data unless specified

# Rebuild operation
auto_rebuild_on_error = True   # Auto-repair on detection
```

### initialization  _← ModelDefault_
# Default Initialization Parameters

Used when TC specifies device initialization but omits parameter details.

## init_tester_to_unit_ready()

**Default Parameters:**
```python
# When resetmode not specified
resetmode = Dcmd5ResetType.HW_RESET  # Hardware reset (full reset cycle)

# When powerdown not specified
powerdown = False  # Keep power on (faster initialization)
```

**Alternatives based on context:**
- If testing power-loss recovery → `powerdown = True`
- If testing reset recovery → `resetmode = HW_RESET`
- If testing warm reset → `resetmode = SOFT_RESET` (if available)

**Rationale:**
- HW_RESET is most reliable and recommended by UFS spec
- Keeping power on reduces test time unless power behavior is being tested

**Spec Reference:** Section 7 (Reset, Power-Up and Power-Down)

---

## access_vendor_mode()

**Default Parameters:**
```python
# Vendor mode access defaults
timeout = 5000  # 5 second timeout for vendor commands
retries = 3     # Retry up to 3 times on temporary failure
```

---

## LU Configuration

When TC specifies logical unit setup but omits details:

```python
# Standard LU configuration (from Script patterns)
config_lun(
    normal_list = [0, 2, 3, 4],    # Standard LUs: Data, WB, GC, Temp
    em1_list = [1],                 # Enhanced Memory 1 LU
    slc_lu = None,                  # No dedicated SLC LU unless specified
    tlc_lu = None,                  # No dedicated TLC LU unless specified
    rpmb_lu = None                  # No direct RPMB LU access unless needed
)
```

**Rationale:**
- 4 normal LUs cover most test scenarios
- EM1 provides reliable storage for critical data
- Additional LUs only configured when explicitly needed

**Related Script:** `Script/pattern/custom_vu/` initialization examples

---

## Hardware Setting Defaults

When getting/setting hardware settings without specifics:

```python
# Default settings retrieval
hw_setting = api.HwSetting.get_instance()
hw_setting.update_from_device()  # Always sync with device before reading

# Common defaults when modifying
inhibition_time = 180  # Seconds (typical idle timeout)
psa_state = api.PSAState.PRE_SOLDERING  # Default PSA mode
write_booster = ENABLED  # EnableWriteBooster by default
background_ops = ENABLED  # Background operations on by default
```

**Spec Reference:** Section 13 (UFS Functional Descriptions)

### power_management  _← ModelDefault_
# Default Power Management Parameters

Used when TC specifies power operations but omits timing/mode details.

## power_cycle()

**Default Behavior (from Script analysis):**
```python
# Random selection between powerdown and HW_RESET
if random.randint(0, 1):
    # 50% chance: Hard reset without power cycle
    init_tester_to_unit_ready(resetmode=Dcmd5ResetType.HW_RESET, powerdown=False)
else:
    # 50% chance: Power cycle (more stress)
    init_tester_to_unit_ready(resetmode=Dcmd5ResetType.HW_RESET, powerdown=True)

# Always restore vendor mode after power cycle
access_vendor_mode()
```

**When randomization not appropriate (TC-specific):**
```python
# For deterministic tests, default to:
resetmode = Dcmd5ResetType.HW_RESET
powerdown = False  # Less disruptive than full power loss
```

---

## Reset Type Defaults

When reset type not specified:

| Scenario | Default Reset | Rationale |
|----------|-------|-----------|
| **General testing** | HW_RESET | Safest, most complete |
| **Warm reset testing** | SOFT_RESET | If testing reset recovery |
| **Power loss testing** | HW_RESET + powerdown=True | Full power cycle |
| **Link recovery** | HW_RESET | Reestablishes all links |

**Spec Reference:** Section 7 (Reset types and procedures)

---

## Timing Defaults

### Idle/Inhibition Time

```python
# When inhibition_time not specified in TC
default_inhibition_time = 180  # seconds (3 minutes)

# Test values (derived from Inhibition_time patterns)
test_inhibition_values = [30, 60, 90, 150, 180, 210, 240, 255]  # seconds

# Zero timeout test (special case)
zero_sec_inhibition_time = 0  # Immediate inhibition on idle
```

### Sleep Duration

```python
# When adding delay between operations
short_delay = 0.01      # 10 milliseconds (minimal)
standard_delay = 0.1    # 100 milliseconds (between checks)
long_delay = 1.0        # 1 second (between major operations)
inhibition_delay = 180  # Must match inhibition_time setting
```

---

## Voltage/Thermal Defaults

When power supply or thermal parameters not specified:

```python
# From UFS Spec electrical requirements
VCC_NOMINAL = 3.3      # volts (primary power)
VCCQ_NOMINAL = 1.8     # volts (I/O power)
VCCQ2_NOMINAL = 1.8    # volts (second I/O rail)

# Thermal protection defaults
THERMAL_HOT_THRESHOLD = 85    # Celsius (trigger throttling)
THERMAL_COLD_THRESHOLD = 0    # Celsius (lower bound)
THERMAL_SAFE_OPERATING = 25   # Celsius (room temperature)
```

**Spec Reference:** 
- Section 6 (Electrical: Clock, Reset, Signals and Supplies)
- Section 8 (MIPI M-PHY: electrical characteristics)

---

## Shipping Mode Defaults

If entering shipping mode but parameters not specified:

```python
# Shipping mode entry
enable_shipping_mode = True
thermal_protection_mode = api.ThermalProtectionMode.HOT_COLD  # Default is both hot/cold

# Recovery from shipping mode
powerdown = True  # Full power cycle required to exit
timeout_for_exit = 5000  # milliseconds
```

**Spec Reference:** Section 7.7 (Shipping Mode)

### vendor_commands  _← ModelDefault_
# Default Vendor Command Parameters

Used when TC specifies vendor commands but omits parameter details. These are UFS implementation-specific commands.

## Common Vendor Commands

### Firmware Value Read/Write

When accessing firmware internal state without specifics:

```python
# Default read pattern for debugging
read_fw_value(address='gInhibitMgr.lock')  # Inhibition manager state

# Standard reads
fw_state = read_fw_value('gFwState.value')
inhibition_status = read_fw_value('gInhibitMgr.lock')
background_ops_status = read_fw_value('gBkopsStatus')
temperature = read_fw_value('gThermalMgr.current_temp')
```

### Memory Access

When reading device memory without specifics:

```python
# Default SRAM read
sram_address = get_debug_info().VB_list_cycle_address.value
memory_data = read_Xmemory(sram_address=sram_address)

# Default DRAM read (if available)
dram_offset = 0x0000
dram_size = 256  # bytes (typical debug buffer)
```

---

## Debug Information Defaults

When retrieving debug info:

```python
# Always get full debug info structure first
resp, debug_info = api.ufs_api.vendor_cmd.get_debug_info()

# Key addresses provided by debug_info
VB_list_cycle_address = debug_info.VB_list_cycle_address.value
error_history_address = debug_info.error_history_address.value
bad_block_address = debug_info.bad_block_address.value
temperature_sensor_address = debug_info.temperature_sensor_address.value
```

---

## Flash Configuration

### Flash Setting Defaults

```python
# Get device flash characteristics
flash_setting = get_flash_setting()

# Use device's native configuration
page_size = flash_setting.page_size         # NAND page size (4KB typical)
erase_block_size = flash_setting.block_size # Block size (varies by device)
planes_per_lun = flash_setting.planes       # Parallelism factor
nand_type = flash_setting.nand_type         # SLC/TLC/QLC detection
```

### SLC Block Mode

When configuring SLC mode without details:

```python
# Default SLC mode behavior
enable_slc_mode = True
slc_block_ratio = auto  # Let device select optimal ratio

# SLC benefits
# - Better write performance
# - Lower error rates
# - Trade: reduced capacity
```

---

## VB (Virtual Block) Information

### Getting VB Metadata

```python
# Default VB information retrieval
vb_list_data = get_VB_group(show=False)  # Get all VB metadata

# Common VB queries
vpct_data = get_all_VPCT_VBINFO_values()  # Virtual Page Count Table
vbinfo = get_VPCT_VBINFO_value(vb_index)   # For specific VB
```

### VB State Defaults

```python
# When checking VB status
expected_vpct = api.VPCT_values(bytearray(4))
expected_vpct.VPC.value = expected_block_count

expected_vbinfo = api.VBINFO_values(bytearray(2))
expected_vbinfo.VBINFO_BIT_PSA.value = 0      # Not PSA block
expected_vbinfo.VBINFO_BIT_PMNTRAINEN.value = 0  # Not training block
```

---

## Background Operation Control

### Enabling/Disabling Background Ops

```python
# Default vendor command for background ops
enable_background_operation = True
bkops_timeout = 3600  # seconds (1 hour max)

# Query background ops status
bkops_status = read_fw_value('gBkopsStatus')
# Values: IDLE, TRIGGERED, URGENT, or RUNNING
```

---

## Temperature Management

### Temperature Reading

```python
# Default temperature monitoring
current_temp = read_fw_value('gThermalMgr.current_temp')

# Temperature sensor defaults
temp_threshold_warning = 80  # Celsius
temp_threshold_critical = 85  # Celsius

# Thermal throttling
throttle_on_warning = True
throttle_on_critical = True
```

### Thermal Protection

```python
# Default thermal protection mode (from ThermalProtection patterns)
thermal_mode = api.ThermalProtectionMode.HOT_COLD  # Both hot & cold

# Test temperature scenarios
test_cold = -5   # Celsius (cold test)
test_normal = 25  # Celsius (room temperature)
test_hot = 50    # Celsius (operating limit)
```

---

## RPMB Management

### RPMB Key Programming

```python
# Default RPMB key initialization
rpmb_region = RPMBRegion.REGION_0
key_size = 32  # bytes (256-bit)
clear_on_init = True

# Key programming sequence
vuc_clear_rpmb_key(RPMBRegion.REGION_0)  # Clear existing
rpmb_key_programming()  # Program new key
```

### RPMB Operations

```python
# Default RPMB operation defaults
write_counter_reset = True  # Reset on init
authenticated_write_enabled = True
replay_protection_enabled = True

# Operation result handling
operation_timeout = 5000  # milliseconds
max_retries = 3
```

---

## Device Identification

### Getting Device Info

```python
# Default identification queries
asic_id = get_asic_id()                    # ASIC version
fw_version = get_fw_version()              # Firmware version
fw_config = get_fw_configuration()         # Feature set
device_uid = read_uid()                    # Unique device ID

# Efuse data (one-time programmable)
efuse_data = get_efuse()  # Read OTP values
```
