=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/cmd_seq/cmds.py: StartStopUnit (SSU) / CmdSeqPowerCycle (POR / LINKSTARTUP)
Script/api/ufs_api/attr_flag_functions.py: read_flag (fDeviceInit)
Script/api/ufs_api/defines/enum_define.py: PowerCycleMode.ALL_POWER_DOWN / LINK_START_UP, FlagIDN.DEVICE_INIT, WellKnownLUN.UFS_DEVICE

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop4_step_1_5(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.5 — Random device reset (SSU / POR / LINKSTARTUP).
        This is the STANDARD reset; Step 2.4 reuses it. Expected: fDeviceInit == 1 after."""
        # TODO-REVIEW-NO-WIKI
        reset_type = random.choice(['SSU', 'POR', 'LINKSTARTUP'])
        logger.info(f'Step 1.5 random reset (iter {loop_idx}): {reset_type}')
        if reset_type == 'SSU':
            for power_condition in (0x02, 0x01):  # SLEEP then ACTIVE
                ssu = ExecuteCMD.StartStopUnit()  # src[code]: Script/api/cmd_seq/cmds.py:StartStopUnit
                ssu.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0,
                           power_condition=power_condition, no_flush=0, start=0)
                ssu.set_option(wait_queue_empty=True)
                ssu.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        elif reset_type == 'POR':
            por = ExecuteCMD.CmdSeqPowerCycle()  # src[code]: Script/api/cmd_seq/cmds.py:CmdSeqPowerCycle
            por.set_option(mode=api.PowerCycleMode.ALL_POWER_DOWN, wait_queue_empty=True, delay_time=100)
            por.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        else:  # LINKSTARTUP — link re-startup
            link = ExecuteCMD.CmdSeqPowerCycle()
            link.set_option(mode=api.PowerCycleMode.LINK_START_UP, wait_queue_empty=True, delay_time=100)
            link.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        if api.read_flag(idn=api.FlagIDN.DEVICE_INIT) != 1:  # src[code]: attr_flag_functions.py:read_flag
            logger.warning(f'Step 1.5 reset {reset_type}: fDeviceInit != 1 after reset')
