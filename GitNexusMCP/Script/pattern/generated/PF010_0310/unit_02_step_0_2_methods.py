=== WIKI REFS ===
entities/scsi-commands.md — READ CAPACITY(10) (25h) is a UCS SCSI command returning the LU last-LBA/block-size
entities/lun.md — capacity is a per-LUN property; max LBA derives from the LU capacity

=== CODE REFS ===
Script/api/cmd_seq/cmds.py: ReadCapacity10 (gitnexus context — set_option(wait_queue_empty,timeout,delay_time))
Script/api/cmd_seq/protocols.py: IsEntry.enqueue (gitnexus context)
Script/api/__init__.py: shared (gitnexus grep — api.shared.param.gLUCapacity capacity cache)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def step2(self) -> None:
        """Step 0.2 — READ CAPACITY(10) (0x25). Produces: self.max_lba.

        Expected: GOOD Status; max_lba taken from the device LU capacity cache.
        """
        logger.info('Step 0.2: READ CAPACITY(10) to obtain LU capacity')
        # sig: ReadCapacity10.set_option(wait_queue_empty=None, timeout=None, delay_time=None) via gitnexus context
        rc = ExecuteCMD.ReadCapacity10()  # src[code]: Script/api/cmd_seq/cmds.py:ReadCapacity10
        rc.set_option(wait_queue_empty=True)
        rc.enqueue()  # sig: IsEntry.enqueue() -> int via gitnexus context
        ExecuteCMD.send(clear_on_success=True)
        # The LU capacity table is populated during device init; max LBA = capacity - 1.
        # src[code]: Script/api/__init__.py:shared (api.shared.param.gLUCapacity)
        self.max_lba = max(int(api.shared.param.gLUCapacity[self.default_lun]) - 1, 0)
        logger.info(f'Step 0.2: max_lba = {self.max_lba}')
