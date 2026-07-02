=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/debug_cmd/dcmd5.py:Dcmd5.reset (gitnexus rank1)
Script/api/ufs_api/debug_cmd/dcmd_enum.py:Dcmd5ResetType (gitnexus rank1)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop0_step_1_1(self, loop_idx: int) -> None:
        # sig: api.init_tester_to_unit_ready(resetmode: Dcmd5ResetType, stop_after_device_init: bool = False, ...) -> None
        # Randomly select one of 4 reset types: HW_RESET, RST_N, ENDPOINT_RESET, UNIPRO_RESET
        reset_types = [
            api.Dcmd5ResetType.HW_RESET,
            api.Dcmd5ResetType.RESET_N,
            api.Dcmd5ResetType.ENDPOINT_RESET,
            api.Dcmd5ResetType.UNIPRO_RESET,
        ]
        selected_reset = random.choice(reset_types)
        logger.info(f"[Loop {loop_idx}] Selected reset type: {selected_reset.name} (0x{selected_reset.value:02X})")
        # Issue reset only; stop before device-init so Step 2_1 can confirm readiness
        api.init_tester_to_unit_ready(resetmode=selected_reset, stop_after_device_init=True)
        logger.info(f"[Loop {loop_idx}] Reset {selected_reset.name} issued")
