=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py: read_flag
Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_1_6(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.6 — Read fWriteBoosterEn after reset (volatile; log per SPEC)."""
        # TODO-REVIEW-NO-WIKI
        self.wb_flag_after_reset = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:read_flag
        logger.info(f'Step 1.6: fWriteBoosterEn after reset = {self.wb_flag_after_reset}')
