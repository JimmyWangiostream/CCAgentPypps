=== WIKI REFS ===
entities/scsi-commands.md -- READ(10) opcode 0x28
entities/lun.md -- LUN semantics

=== CODE REFS ===
Script/api/ufs_api/rw_functions.py:random_read -- confirmed signature via gitnexus context

=== REVIEW FLAGS ===
(empty)

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop1_step_2_3(self, loop_idx: int) -> None:
        # sig: random_read(cmd_count, min_lun, max_lun, min_lba, max_lba, min_size, max_size, need_compare, write_record) -> None
        #     via gitnexus context on Script/api/ufs_api/rw_functions.py:random_read
        # Read back data written in step_2_2 (WB disabled) and compare
        # src[code]: Script/api/ufs_api/rw_functions.py:random_read
        import random

        lun = self.max_capacity_lun
        max_lba = shared.param.gLUCapacity[lun]
        write_record = self.write_record_p2  # from _loop1_step_2_2

        cmd_count = random.randint(8, 32)
        min_size = api.BLOCK4K_SIZE_128K_BYTE
        max_size = api.BLOCK4K_SIZE_1M_BYTE

        logger.info(f"[PF010_0310] Read-compare (no-WB) loop {loop_idx}: lun={lun}, cmd_count={cmd_count}")
        api.random_read(
            cmd_count=cmd_count,
            min_lun=lun,
            max_lun=lun,
            min_lba=0,
            max_lba=max_lba,
            min_size=min_size,
            max_size=max_size,
            need_compare=True,
            write_record=write_record
        )
