=== WIKI REFS ===
entities/scsi-commands.md — READ CAPACITY(10) (25h) returns Last LBA + block length

=== CODE REFS ===
Script/api/cmd_seq/cmds.py: ReadCapacity10 (gitnexus rank1)
Script/api/ufs_api/initial_device.py: gLUCapacity[index] = gUnit[index].q11_logical_block_count (rank2) — capacity cache populated at init
Script/api/shared.py: param.gLUCapacity / gMaxNumberLU (rank3)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===
import Script.api.shared as shared

=== METHODS ===
    def step2(self) -> None:
        """step_0_2 — READ CAPACITY(10) (0x25): obtain MAX_LBA and pick the test LUN.

        gLUCapacity[] is populated during device init from gUnit[].q11_logical_block_count;
        READ CAPACITY(10) is issued to confirm GOOD Status on each enabled LUN.
        """
        param = shared.param
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable:
                rc = ExecuteCMD.ReadCapacity10()  # src[code]: Script/api/cmd_seq/cmds.py:ReadCapacity10
                rc.assign(lun)
                ExecuteCMD.enqueue(rc)
        ExecuteCMD.send(clear_on_success=True)
        # produces: max_lba — first enabled LUN with non-zero capacity is the W/R target
        self._test_lun: int = 0
        self.max_lba: int = 0
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable and param.gLUCapacity[lun] > 0:  # src[code]: Script/api/shared.py:gLUCapacity
                self._test_lun = lun
                self.max_lba = param.gLUCapacity[lun]
                break
        logger.info(f"step2: test_lun={self._test_lun}, max_lba={self.max_lba}")
