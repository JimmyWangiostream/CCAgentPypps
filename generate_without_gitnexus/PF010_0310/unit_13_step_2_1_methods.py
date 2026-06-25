=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/rw_functions.py: sequential_write / get_empty_write_record
Script/api/ufs_api/defines/enum_define.py: CompareMethod.HW_COMPARE

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop4_step_2_1(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.1 — WRITE(10) (record only; compared in Step 2.3 AFTER WB is
        disabled). Sets self.write_lba/write_len and self.write_data (the write record)."""
        # TODO-REVIEW-NO-WIKI
        lun = self.default_lun
        max_lba = self.max_lba if self.max_lba > 0 else 1024
        self.write_lba = random.randint(0, max_lba)
        self.write_len = random.choice([4096, 8192, 16384])
        self.write_data = api.get_empty_write_record()  # src[code]: rw_functions.py:get_empty_write_record
        api.sequential_write(lun=lun, start_lba=self.write_lba, total_size=self.write_len,
                             chunk_size=api.BLOCK4K_SIZE_512K_BYTE, fua=0,
                             need_compare=False, compare_method=api.CompareMethod.HW_COMPARE,
                             write_record=self.write_data)  # src[code]: rw_functions.py:sequential_write
