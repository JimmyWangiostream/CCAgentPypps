=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
(reuses _loop4_step_1_5 — Script/api/cmd_seq/cmds.py: StartStopUnit / CmdSeqPowerCycle)

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_2_4(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.4 — Random reset, identical to Step 1.5; reuse that helper
        rather than duplicating the SSU/POR/LINKSTARTUP logic."""
        # TODO-REVIEW-NO-WIKI
        self._loop4_step_1_5(loop_idx)
