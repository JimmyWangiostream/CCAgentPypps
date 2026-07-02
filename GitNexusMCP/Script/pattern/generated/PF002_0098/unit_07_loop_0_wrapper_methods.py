=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
NO MATCH

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step1(self) -> None:
        """Loop loop_0 (Burn-in Loop) — wrapper. The loop body is decomposed into
        one helper per IR sub-step (_loop0_*), each called once per
        iteration. Control flow lives here; sub-step logic lives in the helpers."""
        _LOOP_ITERATIONS = 10  # TODO human-confirm: loop count (loop_type='condition'; not given by TC)
        for loop_idx in range(_LOOP_ITERATIONS):
            self._loop0_step_0_1(loop_idx)
            self._loop0_step_0_2(loop_idx)
            self._loop0_step_0_3(loop_idx)
            self._loop0_step_1_1(loop_idx)
            self._loop0_step_2_1(loop_idx)
            self._loop0_step_2_2(loop_idx)
