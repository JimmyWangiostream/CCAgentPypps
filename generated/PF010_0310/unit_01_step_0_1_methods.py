=== WIKI REFS ===
entities/scsi-commands.md — TEST UNIT READY (00h) is a mandatory no-data SCSI command; GOOD Status means ready
entities/lun.md — iterate enabled Normal LUs to confirm readiness

=== CODE REFS ===
Script/pattern/sample_code/response_sample.py: Pattern.test_test_unit_ready (gitnexus rank1) — TestUnitReady().assign/enqueue/send idiom
Script/api/cmd_seq/cmds.py: TestUnitReady (gitnexus rank2)
Script/api/shared.py: param.gMaxNumberLU / gUnit[].b3_lu_enable (rank3)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===
import Script.api.shared as shared

=== METHODS ===
    def step1(self) -> None:
        """step_0_1 — TEST UNIT READY (0x00): confirm every enabled LUN is ready (GOOD Status)."""
        param = shared.param  # src[code]: Script/api/shared.py
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable:
                tur = ExecuteCMD.TestUnitReady()  # src[code]: Script/api/cmd_seq/cmds.py:TestUnitReady
                tur.assign(lun)
                ExecuteCMD.enqueue(tur)
        ExecuteCMD.send(clear_on_success=True)
        logger.info("step1: TEST UNIT READY — GOOD Status confirmed for all enabled LUNs")
