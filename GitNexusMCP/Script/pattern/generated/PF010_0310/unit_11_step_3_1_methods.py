=== WIKI REFS ===
entities/flags.md -- SET FLAG (0x02) opcode and flag IDN structure
entities/write-booster.md -- WriteBooster flush flags

=== CODE REFS ===
Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1 -- confirmed ExecuteCMD.SetFlag() idiom (same as Unit 3)

=== REVIEW FLAGS ===
(empty)

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop1_step_3_1(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN).enqueue()  via same idiom as Unit 3
        # sig: ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE).enqueue()  (same pattern)
        # sig: ExecuteCMD.send()  via same source
        # 50%/50% random: set WB flush flag (branch choice)
        # src[code]: Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1
        import random

        # src[wiki]: default.md -- when TC omits, use UserPrompt/CustomerReq rule
        if random.randint(0, 1) == 0:
            flag_idn = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN  # 0x0F
            logger.info(f"[PF010_0310] Set WB Buffer Flush En (loop {loop_idx})")
        else:
            flag_idn = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE  # 0x10
            logger.info(f"[PF010_0310] Set WB Buffer Flush During Hibernate (loop {loop_idx})")
        ExecuteCMD.SetFlag().assign(idn=flag_idn).enqueue()
        ExecuteCMD.send()
