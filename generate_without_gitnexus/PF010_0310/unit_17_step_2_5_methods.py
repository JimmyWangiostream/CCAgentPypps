=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py: read_flag
Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_2_5(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.5 — Verify fWriteBoosterEn == 0 after reset."""
        # TODO-REVIEW-NO-WIKI
        self.wb_disabled_state = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:read_flag
        if self.wb_disabled_state != 0:
            logger.warning(f'Step 2.5: expected fWriteBoosterEn == 0, got {self.wb_disabled_state}')
