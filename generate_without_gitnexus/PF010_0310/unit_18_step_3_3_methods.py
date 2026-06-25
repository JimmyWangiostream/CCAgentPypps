=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py: set_flag
Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN / WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE

=== REVIEW FLAGS ===
TODO-REVIEW-NO-WIKI

=== EXTRA IMPORTS ===
import random
import time

=== METHODS ===
    def _loop4_step_3_3(self, loop_idx: int) -> None:
        """Loop loop_4 Step 3.3 — Random delay (0~2 s) to let the flush trigger.

        NOTE: the TC's Step 3.1/3.2 (50/50 choice of flush flag + SET FLAG) has no
        dedicated IR sub-step — the parser folded it into Step 2.5's content — so the
        flush-flag selection + SET is performed HERE, immediately before the delay.
        Sets self._wb_flush_idn / self._wb_flush_name for the Step 3.5 verify."""
        # TODO-REVIEW-NO-WIKI
        # TODO human-confirm: TC Step 3.1/3.2 (flush-flag select+set) has no dedicated IR
        #   step; performed here. Confirm this is the intended placement.
        if random.random() < 0.5:
            self._wb_flush_idn = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN
            self._wb_flush_name = 'fWriteBoosterBufferFlushEn'
        else:
            self._wb_flush_idn = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE
            self._wb_flush_name = 'fWriteBoosterBufferFlushDuringHibernate'
        api.set_flag(idn=self._wb_flush_idn)  # src[code]: attr_flag_functions.py:set_flag
        logger.info(f'Step 3.1/3.2: set {self._wb_flush_name} = 1')
        time.sleep(random.uniform(0, 2))  # Step 3.3: random delay 0~2 s
