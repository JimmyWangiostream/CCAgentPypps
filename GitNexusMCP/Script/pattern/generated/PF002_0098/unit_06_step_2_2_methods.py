=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/cmd_seq/cmds.py:Read10 (gitnexus rank1)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===

=== METHODS ===
    def _loop0_step_2_2(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.Read10() -> Read10  via gitnexus context
        # sig: cmd.set_option(lun: int, start_lba: int, total_size: int, ...) -> Self
        # sig: ExecuteCMD.enqueue(cmd) -> int
        # sig: ExecuteCMD.send(clear_on_success: bool = False) -> None
        boot_lun = getattr(self, 'boot_lun_id', 0xB0)
        lba_start = getattr(self, 'written_lba_start', 0)
        transfer_len = getattr(self, 'written_transfer_length', 128)

        read10 = ExecuteCMD.Read10()
        read10.set_option(
            lun=boot_lun,
            start_lba=lba_start,
            total_size=transfer_len
        )
        cmd_idx = ExecuteCMD.enqueue(read10)
        ExecuteCMD.send(clear_on_success=False)

        from Script.api.cmd_seq.response import QueryResponse
        rsp = ExecuteCMD.read_response(cmd_idx)
        read_data = rsp.data if rsp else b''
        logger.info(f"[Loop {loop_idx}] Read {len(read_data)} bytes from Boot LUN 0x{boot_lun:02X}")

        # Compare data with written pattern (HW_FIX pattern: all 0x55 or 0xAA alternating)
        expected_pattern = bytes([0x55 if (i % 2 == 0) else 0xAA for i in range(len(read_data))])
        if read_data != expected_pattern:
            logger.error(f"Data mismatch! Expected {len(expected_pattern)} bytes of HW_FIX pattern")
            raise api.SIGHTING_FAIL_DATA_COMPARE_FAIL
        logger.info(f"[Loop {loop_idx}] Data integrity verified: {transfer_len} blocks match written pattern")
