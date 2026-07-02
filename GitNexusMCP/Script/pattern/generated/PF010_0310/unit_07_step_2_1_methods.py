=== WIKI REFS ===
entities/flags.md -- CLEAR FLAG (0x05) opcode and flag IDN structure
entities/write-booster.md -- WriteBooster flag semantics

=== CODE REFS ===
Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1 -- confirmed ExecuteCMD.ClearFlag() idiom

=== REVIEW FLAGS ===
(empty)

=== EXTRA IMPORTS ===
(None needed -- ExecuteCMD and api already in scaffold)

=== METHODS ===
    def _loop1_step_2_1(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.ClearFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()  via read_attr_flag_sample.py step1
        # sig: ExecuteCMD.send()  via same source
        # Disable WriteBooster by clearing fWriteBoosterEn flag
        # src[code]: Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1
        logger.info(f"[PF010_0310] Disabling WriteBooster (loop {loop_idx})")
        ExecuteCMD.ClearFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()
        ExecuteCMD.send()
