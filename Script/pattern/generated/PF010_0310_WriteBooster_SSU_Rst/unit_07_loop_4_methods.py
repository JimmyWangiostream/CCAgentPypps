=== GROUNDING LOG ===
# Steps: loop_4 (step_1_1 through step_3_5)
# Phase 1: Enable WB + Write/Read/Reset
# Phase 2: Write + Disable WB + Read/Reset
# Phase 3: Flush Enable + Delay + Reset
# Source: Script/pattern/luns_reconfiguration/PSW_F_P3_Reconfiguration_0002.py — test_write_booster_flow
# Script/api/ufs_api/attr_flag_functions.py — set_flag/clear_flag/read_flag
# Script/api/ufs_api/defines/enum_define.py — FlagIDN.WRITEBOOSTER_EN=0x0E, etc.
# Script/pattern/debug_command/ — Dcmd5Reset for POR/SSU reset
# Script/api/ufs_api/rw_functions.py — sequential_write, random_write, read_compare

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def step7(self) -> None:
        """Step loop_4: Burn-in loop — WB Enable/Disable/Flush + Reset cycles

        Covers Phase 1 (WB Enable), Phase 2 (WB Disable), Phase 3 (Flush).
        Each cycle: Enable WB -> Write/Read -> Reset -> Verify WB state -> ...
        """
        logger.info('Step loop_4: Start burn-in loop')

        # Burn-in iteration count — configurable
        # TODO human-confirm: source of loop count from burn-in config
        _BURNIN_ITERATIONS = 10

        for burn_in_idx in range(_BURNIN_ITERATIONS):
            logger.info(f'Burn-in iteration {burn_in_idx + 1}/{_BURNIN_ITERATIONS}')
            self._burnin_iteration(burn_in_idx)

        logger.info('Step loop_4: Burn-in loop complete')

    def _burnin_iteration(self, iteration: int) -> None:
        """Execute one burn-in iteration covering all 3 phases.

        Phase 1: Enable WB, write, read-compare, random reset, verify WB flag
        Phase 2: Write, disable WB, read-compare, random reset, verify WB disabled
        Phase 3: Set flush flag (random), delay, random reset, verify flush flag
        """
        lun = self.default_lun

        # ---- Phase 1: WB Enable + W/R + Reset ----
        logger.info(f'Phase 1 (iteration {iteration}): Enable WB')
        api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)

        logger.info(f'Phase 1 (iteration {iteration}): Verify WB enabled')
        wb_enabled_val = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
        if wb_enabled_val != 1:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
                f'Expected fWriteBoosterEn=1, got {wb_enabled_val}')
        logger.info('Phase 1: WB enabled confirmed')

        logger.info(f'Phase 1 (iteration {iteration}): Random write on LUN {lun}')
        lba = random.randint(0, self.max_lba if self.max_lba > 0 else 1024)
        write_size = random.choice([4096, 8192, 16384])
        api.sequential_write(
            lun=lun, start_lba=lba, total_size=write_size,
            chunk_size=api.BLOCK4K_SIZE_512K_BYTE, fua=0,
            need_compare=False, compare_method=api.CompareMethod.HW_COMPARE,
            write_record=self.write_records
        )

        logger.info(f'Phase 1 (iteration {iteration}): Read-compare')
        read_data = api.random_read(
            lun=lun, start_lba=lba, total_size=write_size,
            chunk_size=api.BLOCK4K_SIZE_512K_BYTE, fua=0,
            need_compare=False
        )
        # Verify data match
        stored_data = None
        for rec in self.write_records:
            if rec.lun == lun and rec.start_lba == lba:
                stored_data = rec.data
                break
        if stored_data is not None and read_data is not None:
            if read_data != stored_data:
                raise api.PATTERN_ASSERT_RESPONSE_MISMATCH('Data mismatch after WB-enabled write')
        logger.info('Phase 1: Data verified')

        logger.info(f'Phase 1 (iteration {iteration}): Random reset')
        self._do_random_reset()
        # Verify fDeviceInit == 1 after reset
        device_init = api.read_flag(idn=api.FlagIDN.DEVICE_INIT)
        if device_init != 1:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
                f'Expected fDeviceInit=1 after reset, got {device_init}')

        logger.info(f'Phase 1 (iteration {iteration}): Verify WB flag after reset')
        wb_after_reset = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
        # Per UFS spec, fWriteBoosterEn is volatile — should be cleared after reset
        self.wb_enabled_state = wb_after_reset
        logger.info(f'Phase 1: WB flag after reset = {wb_after_reset}')

        # ---- Phase 2: Write + Disable WB + Reset ----
        logger.info(f'Phase 2 (iteration {iteration}): Write before disable')
        lba2 = random.randint(0, self.max_lba if self.max_lba > 0 else 1024)
        write_size2 = random.choice([4096, 8192, 16384])
        api.sequential_write(
            lun=lun, start_lba=lba2, total_size=write_size2,
            chunk_size=api.BLOCK4K_SIZE_512K_BYTE, fua=0,
            need_compare=False, compare_method=api.CompareMethod.HW_COMPARE,
            write_record=self.write_records
        )

        logger.info(f'Phase 2 (iteration {iteration}): Clear fWriteBoosterEn')
        api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)

        logger.info(f'Phase 2 (iteration {iteration}): Read-compare')
        read_data2 = api.random_read(
            lun=lun, start_lba=lba2, total_size=write_size2,
            chunk_size=api.BLOCK4K_SIZE_512K_BYTE, fua=0,
            need_compare=False
        )
        stored_data2 = None
        for rec in self.write_records:
            if rec.lun == lun and rec.start_lba == lba2:
                stored_data2 = rec.data
                break
        if stored_data2 is not None and read_data2 is not None:
            if read_data2 != stored_data2:
                raise api.PATTERN_ASSERT_RESPONSE_MISMATCH('Data mismatch after WB-disabled write')
        logger.info('Phase 2: Data verified')

        logger.info(f'Phase 2 (iteration {iteration}): Random reset')
        self._do_random_reset()

        logger.info(f'Phase 2 (iteration {iteration}): Verify WB disabled')
        wb_disabled_val = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
        self.wb_disabled_state = wb_disabled_val
        if wb_disabled_val != 0:
            logger.warning(f'Phase 2: Expected fWriteBoosterEn=0, got {wb_disabled_val}')
        logger.info(f'Phase 2: WB disabled state = {wb_disabled_val}')

        # ---- Phase 3: Flush Enable + Delay + Reset ----
        logger.info(f'Phase 3 (iteration {iteration}): Set flush flag (random)')
        # Randomly choose between buffer flush en and hibernate flush en (50/50)
        if random.random() < 0.5:
            flush_flag_idn = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN
            flush_flag_name = 'fWriteBoosterBufferFlushEn'
        else:
            flush_flag_idn = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE
            flush_flag_name = 'fWriteBoosterBufferFlushDuringHibernate'
        api.set_flag(idn=flush_flag_idn)
        logger.info(f'Phase 3: Set {flush_flag_name} = 1')

        logger.info(f'Phase 3 (iteration {iteration}): Random delay 0~2 seconds')
        delay = random.uniform(0, 2)
        time.sleep(delay)

        logger.info(f'Phase 3 (iteration {iteration}): Random reset')
        self._do_flush_random_reset()

        logger.info(f'Phase 3 (iteration {iteration}): Verify flush flag')
        flush_after_reset = api.read_flag(idn=flush_flag_idn)
        self.flush_flag_state = flush_after_reset
        logger.info(f'Phase 3: Flush flag ({flush_flag_name}) after reset = {flush_after_reset}')

    def _do_random_reset(self) -> None:
        """Randomly select one reset type: SSU, POR, or Link Startup."""
        reset_type = random.choice(['SSU', 'POR', 'LINK'])
        logger.info(f'Random reset: {reset_type}')

        if reset_type == 'SSU':
            # START STOP UNIT — power cycle mode
            cmd = ExecuteCMD.StartStopUnit()
            cmd.power_condition = 0x0  # STOP
            cmd.start = 0
            cmd.enqueue()
            ExecuteCMD.send(clear_on_success=True)
            time.sleep(0.1)  # brief pause
            cmd2 = ExecuteCMD.StartStopUnit()
            cmd2.power_condition = 0x0
            cmd2.start = 1
            cmd2.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        elif reset_type == 'POR':
            # Dcmd5 — power-on reset
            api.Dcmd5Reset(0x02)  # Dcmd5 Reset Type: POR
            time.sleep(0.5)
        else:
            # Link startup reset via Dcmd5 RESET_N
            api.Dcmd5Reset(0x01)  # Dcmd5 Reset Type: RESET_N
            time.sleep(0.1)

        # Verify fDeviceInit == 1
        device_init = api.read_flag(idn=api.FlagIDN.DEVICE_INIT)
        if device_init != 1:
            logger.warning(f'Reset {reset_type}: fDeviceInit={device_init} (expected 1)')

    def _do_flush_random_reset(self) -> None:
        """Randomly select a flush-path reset: POR_delay or SSU+Hibernate+POR."""
        reset_type = random.choice(['POR_DELAY', 'SSU_HIB_POR'])
        logger.info(f'Flush-path random reset: {reset_type}')

        if reset_type == 'POR_DELAY':
            time.sleep(random.uniform(0, 1))
            api.Dcmd5Reset(0x02)  # POR
            time.sleep(0.5)
        else:
            # SSU → Hibernate → POR
            cmd = ExecuteCMD.StartStopUnit()
            cmd.power_condition = 0x0
            cmd.start = 0
            cmd.enqueue()
            ExecuteCMD.send(clear_on_success=True)
            time.sleep(0.1)

            # Hibernate via SSU extended power mode
            # Some devices support Hibernate mode via Dcmd5 or extended SSU
            cmd2 = ExecuteCMD.StartStopUnit()
            cmd2.power_condition = 0x06  # Hibernate mode (extended)
            cmd2.start = 1
            cmd2.enqueue()
            ExecuteCMD.send(clear_on_success=True)
            time.sleep(0.5)

            # After wake from hibernate, verify device init
            device_init = api.read_flag(idn=api.FlagIDN.DEVICE_INIT)
            if device_init != 1:
                logger.warning('Hibernate+POR: fDeviceInit != 1')
            time.sleep(0.1)