=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py: read_flag

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop4_step_3_5(self, loop_idx: int) -> None:
        """Loop loop_4 Step 3.5 — Read the flush flag chosen in Step 3.3 after reset
        (self._wb_flush_idn / self._wb_flush_name, set earlier in this iteration)."""
        # TODO-REVIEW-NO-WIKI
        self.flush_flag_state = api.read_flag(idn=self._wb_flush_idn)  # src[code]: attr_flag_functions.py:read_flag
        logger.info(f'Step 3.5: {self._wb_flush_name} after reset = {self.flush_flag_state}')
