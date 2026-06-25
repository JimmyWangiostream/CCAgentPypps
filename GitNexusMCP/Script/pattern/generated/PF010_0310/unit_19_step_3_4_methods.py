=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/cmd_seq/cmds.py: StartStopUnit (SSU) / CmdSeqPowerCycle (POR)
Script/api/ufs_api/attr_flag_functions.py: read_flag (fDeviceInit)
Script/api/ufs_api/defines/enum_define.py: PowerCycleMode.ALL_POWER_DOWN, FlagIDN.DEVICE_INIT, WellKnownLUN.UFS_DEVICE

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop4_step_3_4(self, loop_idx: int) -> None:
        """Loop loop_4 Step 3.4 — Phase-3 random reset (POR_delay / SSU+Hibernate+POR).
        Expected: fDeviceInit == 1 after the reset."""
        # TODO-REVIEW-NO-WIKI
        reset_type = random.choice(['POR_DELAY', 'SSU_HIB_POR'])
        logger.info(f'Step 3.4 phase-3 reset (iter {loop_idx}): {reset_type}')
        if reset_type == 'SSU_HIB_POR':
            for power_condition in (0x02, 0x01):  # SLEEP then ACTIVE
                ssu = ExecuteCMD.StartStopUnit()  # src[code]: Script/api/cmd_seq/cmds.py:StartStopUnit
                ssu.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0,
                           power_condition=power_condition, no_flush=0, start=0)
                ssu.set_option(wait_queue_empty=True)
                ssu.enqueue()
            ExecuteCMD.send(clear_on_success=True)
            # TODO human-confirm: exact SSU -> Hibernate -> POR sequencing for Phase 3
            por = ExecuteCMD.CmdSeqPowerCycle()  # src[code]: Script/api/cmd_seq/cmds.py:CmdSeqPowerCycle
            por.set_option(mode=api.PowerCycleMode.ALL_POWER_DOWN, wait_queue_empty=True, delay_time=100)
            por.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        else:  # POR_DELAY — Power-On Reset with a longer settle delay
            por = ExecuteCMD.CmdSeqPowerCycle()
            por.set_option(mode=api.PowerCycleMode.ALL_POWER_DOWN, wait_queue_empty=True, delay_time=1000)
            por.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        if api.read_flag(idn=api.FlagIDN.DEVICE_INIT) != 1:  # src[code]: attr_flag_functions.py:read_flag
            logger.warning(f'Step 3.4 reset {reset_type}: fDeviceInit != 1 after reset')
