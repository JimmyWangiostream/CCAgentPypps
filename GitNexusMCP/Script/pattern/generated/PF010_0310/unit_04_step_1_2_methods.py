=== WIKI REFS ===
entities/scsi-commands.md -- WRITE(10) opcode 0x2A
entities/write-booster.md -- WriteBooster behavior with random writes

=== CODE REFS ===
Script/api/ufs_api/rw_functions.py:random_write (gitnexus confirmed signature)
Script/pattern/sample_code/normal_rw_sample.py:Pattern.step1 -- confirmed api.random_write() idiom with write_record
Script/api/util/write_record/functions.py:get_empty_write_record -- write_record source

=== REVIEW FLAGS ===
(empty)

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop1_step_1_2(self, loop_idx: int) -> None:
        # sig: random_write(cmd_count, min_lun, max_lun, min_lba, max_lba, min_size, max_size, need_compare, compare_method, write_record) -> None
        #     via gitnexus context on Script/api/ufs_api/rw_functions.py:random_write
        # sig: api.get_empty_write_record() -> List[List[WriteRecordNode]]  via gitnexus
        # sig: api.BLOCK4K_SIZE_128K_BYTE, api.BLOCK4K_SIZE_1M_BYTE  via normal_rw_sample.py
        # sig: api.CompareMethod.HW_COMPARE  (int value, not an enum object -- anti-conflation)
        # Random write while WriteBooster is enabled -- write through WB buffer
        # src[code]: Script/api/ufs_api/rw_functions.py:random_write
        import random

        write_record = api.get_empty_write_record()
        lun = self.max_capacity_lun
        max_lba = shared.param.gLUCapacity[lun]

        cmd_count = random.randint(8, 32)  # random block count per iteration
        min_size = api.BLOCK4K_SIZE_128K_BYTE
        max_size = api.BLOCK4K_SIZE_1M_BYTE

        logger.info(f"[PF010_0310] Random write loop {loop_idx}: lun={lun}, cmd_count={cmd_count}")
        # src[code]: Script/api/ufs_api/rw_functions.py:random_write
        api.random_write(
            cmd_count=cmd_count,
            min_lun=lun,
            max_lun=lun,
            min_lba=0,
            max_lba=max_lba,
            min_size=min_size,
            max_size=max_size,
            need_compare=True,
            compare_method=api.CompareMethod.HW_COMPARE,
            write_record=write_record
        )
        self.write_record_p1 = write_record  # consumed by _loop1_step_1_3 (read-back verify)
