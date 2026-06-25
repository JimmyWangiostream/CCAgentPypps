=== WIKI REFS ===
entities/scsi-commands.md — TEST UNIT READY is a UCS SCSI command (CONTROL byte 00h); GOOD status means ready
entities/lun.md — target the UFS device well-known LUN for the readiness probe

=== CODE REFS ===
Script/api/cmd_seq/cmds.py: CmdSeqTestUnitReady (gitnexus context)
Script/api/cmd_seq/protocols.py: IsEntry.enqueue (gitnexus context)
Script/api/util/write_record/functions.py: get_empty_write_record (gitnexus query rank)
Script/api/ufs_api/defines/enum_define.py: WellKnownLUN.UFS_DEVICE (gitnexus grep-confirmed)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step1(self) -> None:
        """Step 0.1 — TEST UNIT READY (0x00). Expected: GOOD Status.

        step1 runs first, so initialise the test-wide state the later steps read.
        """
        # Test-wide state shared across steps via self.* (process() runs step1..stepN).
        self.default_lun: int = 0
        self.write_record = api.get_empty_write_record()  # src[code]: Script/api/util/write_record/functions.py:get_empty_write_record
        self.max_lba: int = 0

        logger.info('Step 0.1: TEST UNIT READY (0x00) on UFS device LUN')
        # sig: CmdSeqTestUnitReady.set_option(lun, timeout=100000, wait_queue_empty=False, delay_time=0) via gitnexus context
        tur = ExecuteCMD.CmdSeqTestUnitReady()  # src[code]: Script/api/cmd_seq/cmds.py:CmdSeqTestUnitReady
        tur.set_option(api.WellKnownLUN.UFS_DEVICE, wait_queue_empty=True)  # src[code]: Script/api/ufs_api/defines/enum_define.py:WellKnownLUN.UFS_DEVICE
        # sig: IsEntry.enqueue() -> int via gitnexus context
        tur.enqueue()
        ExecuteCMD.send(clear_on_success=True)
        logger.info('Step 0.1: device reported ready (GOOD Status expected)')
