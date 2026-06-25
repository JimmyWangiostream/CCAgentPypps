=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py: clear_flag
Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_2_2(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.2 — Disable WriteBooster (CLEAR FLAG fWriteBoosterEn)."""
        # TODO-REVIEW-NO-WIKI
        api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:clear_flag
