=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/rw_functions.py: sequential_write (lun,start_lba,total_size,chunk_size,fua,need_compare,compare_method,write_record)
Script/api/ufs_api/rw_functions.py: get_empty_write_record
Script/api/ufs_api/defines/enum_define.py: CompareMethod.HW_COMPARE

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop4_step_1_3(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.3 — WRITE(10) random LBA/size; keep the write record for the
        Step 1.4 compare. Sets self.write_lba/write_len (IR contract) and self.write_data
        (the write record handed to Step 1.4 within THIS iteration)."""
        # TODO-REVIEW-NO-WIKI
        lun = self.default_lun
        max_lba = self.max_lba if self.max_lba > 0 else 1024
        self.write_lba = random.randint(0, max_lba)
        self.write_len = random.choice([4096, 8192, 16384])
        self.write_data = api.get_empty_write_record()  # src[code]: rw_functions.py:get_empty_write_record
        # sig: sequential_write(lun,start_lba,total_size,chunk_size,fua,need_compare,compare_method,write_record)
        api.sequential_write(lun=lun, start_lba=self.write_lba, total_size=self.write_len,
                             chunk_size=api.BLOCK4K_SIZE_512K_BYTE, fua=0,
                             need_compare=False, compare_method=api.CompareMethod.HW_COMPARE,
                             write_record=self.write_data)  # src[code]: rw_functions.py:sequential_write
