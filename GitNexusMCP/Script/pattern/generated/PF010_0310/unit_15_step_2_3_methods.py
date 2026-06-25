=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/rw_functions.py: read_compare (write_record, compare_method)
Script/api/ufs_api/defines/enum_define.py: CompareMethod.HW_COMPARE

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_2_3(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.3 — READ(10) + HW compare against the Step 2.1 record
        (data must still match after WB was disabled)."""
        # TODO-REVIEW-NO-WIKI
        api.read_compare(self.write_data, api.CompareMethod.HW_COMPARE)  # src[code]: rw_functions.py:read_compare
