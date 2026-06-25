=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py: set_flag (gitnexus context — set_flag(idn,index=0,selector=0))
Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_1_1(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.1 — Enable WriteBooster (SET FLAG fWriteBoosterEn)."""
        # TODO-REVIEW-NO-WIKI
        api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: Script/api/ufs_api/attr_flag_functions.py:set_flag
