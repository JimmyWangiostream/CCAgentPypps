=== WIKI REFS ===
entities/power-modes.md -- POR behavior and power mode transitions
concepts/power-management.md -- Reset types and timing

=== CODE REFS ===
Script/pattern/Inhibition_time/PSW_F_P3_InhibitionTime_0001_Disable_Enable_Test.py:Pattern.power_cycle -- confirmed POR idiom
Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready -- confirmed signature
Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode -- confirmed no-arg vendor mode

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop1_step_1_4(self, loop_idx: int) -> None:
        # sig: init_tester_to_unit_ready(resetmode: Dcmd5ResetType, powerdown: bool = False) -> None
        #     via gitnexus context on Script/api/ufs_api/initial_device.py
        # sig: access_vendor_mode() -> None  via same source
        # Power On Reset: random HW_RESET with or without power-down
        # src[code]: Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready
        # src[code]: Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode
        import random

        logger.info(f"[PF010_0310] POR loop {loop_idx}")
        if random.randint(0, 1):
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=False)
        else:
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
        api.access_vendor_mode()
