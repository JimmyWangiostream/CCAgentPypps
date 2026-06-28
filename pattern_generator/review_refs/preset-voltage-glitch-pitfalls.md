# PERESET / Voltage Glitch Test Pitfalls

Per-session knowledge from reviewing PSW_F_P3_PERESET_0001_PERESET_Detection_Normal_Test.py (291 lines).

## 1. Cross-Iteration Baseline Trap (RED — CRITICAL)

**Symptom**: PERESET_count_bk = PERESET_count is commented out. Each loop iteration
uses the stale baseline from the first iteration (case=0, v=0).

**Impact**: After case=0 executes, PERESET_count may have incremented. But case=1 still
compares against the OLD baseline, producing FALSE NEGATIVES (expected +1 but compared
to old value = 0 change).

**Fix**: Uncomment the baseline update at end of each iteration, OR re-read baseline
at loop start for case>0 or v>0.

## 2. READ Command Won't Timeout Under VCC Drop (RED — CRITICAL)

**Symptom**: Case 1 uses READ10 with fua=1 as the glitch target. READ commands complete
fast — data is read back to host immediately. Unlike WRITE (needs NVM time) or D060
(needs flash operations), READ rarely catches mid-exec during a voltage drop.

**Impact**: Case 1 will always raise SIGHTING_RESPONSE_UNEXPECTED, blocking all
subsequent test execution.

**Fix**: Remove Case 1, or switch to WRITE10 which needs NVM write time and is more
likely to timeout under brownout.

## 3. VU Command (D060) Timeout Under Brownout Unverified

**Symptom**: D060 is a Vendor U command. VU command timeout behavior under brownout
is firmware-dependent. If the flash controller silently drops VU requests without
triggering a timeout, the test gets false negatives.

**Fix**: Hardware-verify that D060 actually times out (rather than silently failing)
when VCC is at 1.7V.

## 4. Inconsistent Recovery Paths

**Pattern observed**:
- v==0: switch_voltage_value(2.5V) -> sleep(5) -> HW_RESET
  (Voltage adjusted BEFORE reset — simulates glitch auto-recovery)
- v==1/v==2: POWER_OFF -> switch_voltage_value(2.5V) -> HW_RESET
  (Power cut first, THEN voltage adjusted — simulates full power loss)

**Fix**: Either unify all recovery paths or document design rationale for v==0's
different approach.

## 5. Voltage Stabilization Delay Missing

**Symptom**: switch_voltage_value() and ExecuteCMD() happen back-to-back with no
delay. VCC may not have stabilized at target voltage when command is issued.

**Fix**: Add time.sleep(0.1) or similar after voltage drop, before issuing command.

## 6. Case 2 (Erase) Write Size Too Small

**Observation**: Case 2 writes only 1 VB (~tens to hundreds of 4K blocks), while
Case 0/1 write 512MB (131,072 blocks). This is orders of magnitude smaller, so
FTL wear-leveling, GC, and bad-block management are NOT triggered.

**Fix**: Use same write size as Case 0/1, or at least 16MB+.

## 7. Voltage Matrix Intent Unclear

**Observed matrix**:
- v==0: 2.0V, glitch recovery (adjust voltage + HW_RESET)
- v==1: 2.0V, power-loss recovery (power off + adjust + HW_RESET)
- v==2: 1.7V, power-loss recovery (power off + adjust + HW_RESET)

v==0 and v==1 both use 2.0V but different recovery. This tests glitch tolerance vs
power-loss tolerance, but is undocumented.

**Fix**: Add comments explaining the design intent.
