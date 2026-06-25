=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py: read_flag (direct read of source — read_flag(idn,index=0,selector=0)->int)
Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_1_2(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.2 — Verify fWriteBoosterEn == 1."""
        # TODO-REVIEW-NO-WIKI
        if api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN) != 1:  # src[code]: attr_flag_functions.py:read_flag
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION('Step 1.2: expected fWriteBoosterEn == 1')
