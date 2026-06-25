=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/rw_functions.py: read_compare (write_record, compare_method)
Script/api/ufs_api/defines/enum_define.py: CompareMethod.HW_COMPARE

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_1_4(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.4 — READ(10) + HW compare against the Step 1.3 write record
        (self.write_data, set earlier in this iteration)."""
        # TODO-REVIEW-NO-WIKI
        api.read_compare(self.write_data, api.CompareMethod.HW_COMPARE)  # src[code]: rw_functions.py:read_compare
