=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
NO MATCH

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step3(self) -> None:
        """Loop loop_1 (Burn-in Loop) — wrapper. The loop body is decomposed into
        one helper per IR sub-step (_loop1_*), each called once per
        iteration. Control flow lives here; sub-step logic lives in the helpers."""
        _LOOP_ITERATIONS = 10  # TODO human-confirm: loop count (loop_type='condition'; not given by TC)
        for loop_idx in range(_LOOP_ITERATIONS):
            self._loop1_step_1_1(loop_idx)
            self._loop1_step_1_2(loop_idx)
            self._loop1_step_1_3(loop_idx)
            self._loop1_step_1_4(loop_idx)
            self._loop1_step_2_1(loop_idx)
            self._loop1_step_2_2(loop_idx)
            self._loop1_step_2_3(loop_idx)
            self._loop1_step_2_4(loop_idx)
            self._loop1_step_3_1(loop_idx)
            self._loop1_step_3_2(loop_idx)
            self._loop1_step_3_3(loop_idx)
            self._loop1_step_3_4(loop_idx)
            self._loop1_step_3_5(loop_idx)
