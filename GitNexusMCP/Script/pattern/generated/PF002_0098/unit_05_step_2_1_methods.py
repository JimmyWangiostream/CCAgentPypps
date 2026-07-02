=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py:read_flag (gitnexus rank1)
Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready (gitnexus rank1)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop0_step_2_1(self, loop_idx: int) -> None:
        # sig: api.init_tester_to_unit_ready(resetmode: Dcmd5ResetType, stop_after_device_init: bool = False, ...) -> None
        # sig: api.FlagIDN.DEVICE_INIT = 0x01 (fDeviceInit flag)
        # Complete device init after reset: call with default (no reset) to wait for ready
        api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.SKIP_RESET, stop_after_device_init=False)
        logger.info(f"[Loop {loop_idx}] Device initialized and ready after reset")
