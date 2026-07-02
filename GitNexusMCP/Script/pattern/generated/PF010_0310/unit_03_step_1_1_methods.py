=== WIKI REFS ===
entities/flags.md -- SET FLAG (0x02) opcode and flag IDN structure
entities/write-booster.md -- WriteBooster fWriteBoosterEn flag meaning

=== CODE REFS ===
Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1 -- confirmed ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()

=== REVIEW FLAGS ===
(empty)

=== EXTRA IMPORTS ===
(None needed -- ExecuteCMD and api already in scaffold)

=== METHODS ===
    def _loop1_step_1_1(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()  via read_attr_flag_sample.py step1
        # sig: ExecuteCMD.send()  via same source
        # Enable WriteBooster by setting fWriteBoosterEn flag
        # TC specifies max_capacity_lun for LUN field (TC: LUN=0x00, max_capacity_lun is within allowed range per CustomerReq)
        # src[code]: Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1
        logger.info(f"[PF010_0310] Enabling WriteBooster (loop {loop_idx})")
        ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()
        ExecuteCMD.send()
