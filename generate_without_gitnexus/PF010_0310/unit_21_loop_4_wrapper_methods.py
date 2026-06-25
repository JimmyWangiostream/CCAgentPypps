=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
NO MATCH

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step7(self) -> None:
        """Loop loop_4 (Burn-in) — wrapper. The loop body is decomposed into
        one helper per IR sub-step (_loop4_*), each called once per
        iteration. Control flow lives here; sub-step logic lives in the helpers."""
        _LOOP_ITERATIONS = 10  # TODO human-confirm: loop count (loop_type='condition'; not given by TC)
        for loop_idx in range(_LOOP_ITERATIONS):
            self._loop4_step_1_1(loop_idx)
            self._loop4_step_1_2(loop_idx)
            self._loop4_step_1_3(loop_idx)
            self._loop4_step_1_4(loop_idx)
            self._loop4_step_1_5(loop_idx)
            self._loop4_step_1_6(loop_idx)
            self._loop4_step_2_1(loop_idx)
            self._loop4_step_2_2(loop_idx)
            self._loop4_step_2_3(loop_idx)
            self._loop4_step_2_4(loop_idx)
            self._loop4_step_2_5(loop_idx)
            self._loop4_step_3_3(loop_idx)
            self._loop4_step_3_4(loop_idx)
            self._loop4_step_3_5(loop_idx)
