=== WIKI REFS ===
concepts/power-management.md -- SSU Sleep power condition field encoding
entities/power-modes.md -- Sleep mode transitions and power conditions

=== CODE REFS ===
Script/pattern/read_scan/mutual_fun.py:push_ssu -- confirmed StartStopUnit(CDB) idiom with lun=WellKnownLUN.UFS_DEVICE, power_condition=0x02(Sleep), assign/set_option/enqueue pattern

=== REVIEW FLAGS ===
(empty -- both sources matched)

=== EXTRA IMPORTS ===
(None required; push_ssu lives in Script/pattern/read_scan/ which is not a bound namespace; however the idiom is directly usable via ExecuteCMD as shown)

=== METHODS ===
    def _loop1_step_3_4(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.StartStopUnit().assign(lun=WellKnownLUN, immed=int, power_condition=int, no_flush=int, start=int) -> Self
        # sig: ExecuteCMD.StartStopUnit().set_option(wait_queue_empty: bool) -> None
        # sig: ExecuteCMD.enqueue(cmd: IsEntry) -> None
        # via gitnexus context on Script/pattern/read_scan/mutual_fun.py:push_ssu
        # Enter Sleep via START STOP UNIT (Opcode 0x1B, START=0, PowerCondition=0x02)
        # src[code]: Script/pattern/read_scan/mutual_fun.py:push_ssu

        logger.info(f"[PF010_0310] START STOP UNIT -> Sleep (loop {loop_idx})")
        ssu = ExecuteCMD.StartStopUnit()
        ssu.assign(
            lun=api.WellKnownLUN.UFS_DEVICE,
            immed=0,
            power_condition=0x02,   # 0x02 = Sleep
            no_flush=0,
            start=0                # 0 = Stop/Standby
        )
        ssu.set_option(wait_queue_empty=True)
        ExecuteCMD.enqueue(ssu)
