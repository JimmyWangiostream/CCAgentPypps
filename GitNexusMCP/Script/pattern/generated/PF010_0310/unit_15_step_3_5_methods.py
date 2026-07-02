=== WIKI REFS ===
concepts/power-management.md -- POR timing and reset type guidance
entities/power-modes.md -- power mode transitions and reset behavior

=== CODE REFS ===
Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready -- confirmed HW_RESET signature
Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode -- confirmed vendor mode after POR

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===
(None required)

=== METHODS ===
    def _loop1_step_3_5(self, loop_idx: int) -> None:
        # sig: init_tester_to_unit_ready(resetmode: Dcmd5ResetType, powerdown: bool = False) -> None
        #     via gitnexus context on Script/api/ufs_api/initial_device.py
        # sig: access_vendor_mode() -> None  via same source
        # POR from Sleep state -- verify WB Buffer Flush under Sleep -> POR path
        # src[code]: Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready
        # src[code]: Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode
        import random

        logger.info(f"[PF010_0310] POR from Sleep (loop {loop_idx})")
        if random.randint(0, 1):
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=False)
        else:
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
        api.access_vendor_mode()
