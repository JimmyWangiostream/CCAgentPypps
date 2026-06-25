=== GROUNDING LOG ===
Step: step_0_1 (TEST UNIT READY)
Source: Script/pattern/sample_code/read_attr_flag_sample.py — ExecuteCMD.CmdSeqTestUnitReady()
Script/api/cmd_seq/cmds.py: CmdSeqTestUnitReady -> send(clear_on_success=True)

=== EXTRA IMPORTS ===

=== METHODS ===
    def step1(self) -> None:
        """Step 0.1: Confirm device ready — TEST UNIT READY (0x00)

        Expected: GOOD Status
        """
        logger.info('Step 0.1: Issue TEST UNIT READY (0x00)')
        cmd = ExecuteCMD.CmdSeqTestUnitReady()
        cmd.enqueue()
        ExecuteCMD.send(clear_on_success=True)
