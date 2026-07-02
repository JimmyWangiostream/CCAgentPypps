=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/cmd_seq/cmds.py:Write10 (gitnexus rank1)
Script/api/ufs_api/attr_flag_functions.py:write_attribute (gitnexus rank1)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop0_step_0_3(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.Write10() -> Write10  via gitnexus context
        # sig: cmd.set_option(lun: int, start_lba: int, total_size: int, ...) -> Self  (confirmed via cmd_seq/cmds.py:Write10.set_option)
        # sig: ExecuteCMD.enqueue(cmd) -> int
        # sig: ExecuteCMD.send(clear_on_success: bool = False) -> None
        import random
        import Script.api.shared as shared

        # Boot W-LUN address: 0xB0 = BOOT_WELL_KNOWN_LU_A (JESD220H Section 10.6.5)
        boot_lun = 0xB0
        lun_desc = shared.param.gUnit[boot_lun]
        total_blocks = getattr(lun_desc, 'q11_logical_block_count', 0)
        test_blocks = min(total_blocks, 128)  # write 128 blocks max for test pattern

        write10 = ExecuteCMD.Write10()
        write10.set_option(
            lun=boot_lun,
            start_lba=0,
            total_size=test_blocks,
            wait_queue_empty=True,
            pattern_mode=api.CmdParamPatternMode.HW_FIX
        )
        cmd_idx = ExecuteCMD.enqueue(write10)
        ExecuteCMD.send(clear_on_success=False)

        self.boot_lun_id = boot_lun
        self.write_pattern = 'HW_FIX'
        self.written_lba_start = 0
        self.written_transfer_length = test_blocks
        logger.info(f"Written test pattern to Boot LUN 0x{boot_lun:02X}: {test_blocks} blocks")
