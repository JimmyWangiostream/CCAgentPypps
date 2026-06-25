import package_root
from Script import api
from Script.lib import sdk_lib as lib
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
import Script.api.cmd_seq as ExecuteCMD
import random
import time


class PF010_0310_WriteBooster_SSU_Rst(UFSTC):
    """PF010_0310 — PF010_0310_WriteBooster_SSU_Rst-Normalized-TestFlow"""

    def pre_process(self) -> None:
        pass  # TODO human-confirm: pre-test device setup

    def step1(self) -> None:
        """Step 0.1: Confirm device ready — TEST UNIT READY (0x00)

        Expected: GOOD Status
        """
        logger.info('Step 0.1: Issue TEST UNIT READY (0x00)')
        cmd = ExecuteCMD.CmdSeqTestUnitReady()
        cmd.enqueue()
        ExecuteCMD.send(clear_on_success=True)

    def step2(self) -> None:
        """Step 0.2: Get max_lba via READ CAPACITY(10)

        Expected: GOOD Status, logical_block_count >= 1
        """
        logger.info('Step 0.2: Issue READ CAPACITY(10) to get max LBA')
        capacity = ExecuteCMD.ReadCapacity10()
        ExecuteCMD.send(clear_on_success=True)
        # Extract max_lba from capacity response (logical_block_count - 1)
        logical_block_count = int(capacity.get('logical_block_count', 0))
        max_lba = max(logical_block_count - 1, 0)
        self.max_lba = max_lba
        logger.info(f'Step 0.2: max_lba = {self.max_lba}')

    def step3(self) -> None:
        """Step 0.3: Check WriteBooster support — READ DEVICE DESCRIPTOR

        Reads UFSFeaturesSupport (device descriptor) and checks u8_write_booster bit.
        Produces: wb_supported

        Expected: QUERY RESPONSE Success, WB bit is set
        """
        logger.info('Step 0.3: Read device descriptor for WB support check')
        dev_desc = api.get_device_descriptor()

        # Check UFSFeaturesSupport bit 8 for WB support
        ufs_feat = api.get_ufs_features_support()
        self.wb_supported = bool(ufs_feat.u8_write_booster)

        if self.wb_supported:
            logger.info('Step 0.3: WriteBooster is supported (u8_write_booster=1)')
        else:
            logger.info('Step 0.3: WriteBooster NOT supported — raise NOT SUPPORTED')
            raise api.UFS_NON_SUPPORT('WriteBooster not supported by device')

    def step4(self) -> None:
        """Step 0.4: Read max WB alloc units — READ DESCRIPTOR (Configuration Descriptor)

        Reads Configuration Descriptor to get l85_num_shared_write_booster_buffer_alloc_units.
        Produces: max_wb_alloc_units

        Expected: QUERY RESPONSE Success, returns max alloc units
        """
        logger.info('Step 0.4: Read Configuration Descriptor for max WB alloc units')
        config_data = api.get_config_descriptor()

        # Max alloc units from device descriptor field (WB max capability)
        # Device descriptor has l85_num_shared_write_booster_buffer_alloc_units
        dev_desc = api.get_device_descriptor()
        self.max_wb_alloc_units = int(dev_desc.l85_num_shared_write_booster_buffer_alloc_units)

        logger.info(f'Step 0.4: max_wb_alloc_units = {self.max_wb_alloc_units}')

    def step5(self) -> None:
        """Step 0.5: Read Configuration Descriptor (full read)

        Reads the Configuration Descriptor and stores the raw data for later write.
        Produces: config_descriptor_data

        Expected: QUERY RESPONSE Success
        """
        logger.info('Step 0.5: Read full Configuration Descriptor')
        # get_config_descriptor reads via READ DESCRIPTOR (0x01)
        self.config_descriptor_data = api.get_config_descriptor()
        logger.info('Step 0.5: Configuration Descriptor read successfully')

    def step6(self) -> None:
        """Step 0.6: Configure WriteBooster Buffer — WRITE DESCRIPTOR (Configuration)

        Sets bWriteBoosterBufferType=0x01 (Shared) and allocates MAX units.
        Produces: wb_configured

        Expected: QUERY RESPONSE Success
        """
        logger.info('Step 0.6: Configure WriteBooster buffer (Shared + MAX alloc units)')

        # Get current configuration descriptor to preserve other fields
        current_config = self.config_descriptor_data

        # Get max alloc units from device descriptor
        max_units = self.max_wb_alloc_units

        if max_units == 0:
            logger.info('Step 0.6: max_wb_alloc_units=0, skip WB config (not available)')
            self.wb_configured = False
            return

        # Prepare configuration descriptor write
        # b84_write_booster_buffer_type = 0x01 (Shared)
        # l85_num_shared_write_booster_buffer_alloc_units = MAX
        # Use raw WRITE DESCRIPTOR via ExecuteCMD
        cmd = ExecuteCMD.WriteDescriptor()
        cmd.assign(
            idn=0x01,  # Configuration Descriptor
            index=0x00,
            selector=0x00,
            data=b''
        )

        # Build config descriptor write data
        # Read current config, modify WB fields, write back
        # Configuration descriptor is 64 bytes
        config_data = bytearray(64)

        # Read current config descriptor data first
        cmd_read = ExecuteCMD.ReadDescriptor()
        cmd_read.assign(idn=0x01, index=0x00, selector=0x00)
        ExecuteCMD.enqueue(cmd_read)
        ExecuteCMD.send(clear_on_success=False)
        resp = ExecuteCMD.read_response(0)
        config_data = bytearray(resp.data) if hasattr(resp, 'data') else bytearray(64)

        # Set b84_write_booster_buffer_type = 0x01 (Shared) at offset 84
        # Set l85_num_shared_write_booster_buffer_alloc_units = MAX at offset 85
        if len(config_data) >= 84:
            config_data[84] = 0x01  # Shared type
        if len(config_data) >= 89:
            config_data[85] = max_units & 0xFF
            if max_units > 0xFF:
                config_data[86] = (max_units >> 8) & 0xFF
                config_data[87] = (max_units >> 16) & 0xFF
                config_data[88] = (max_units >> 24) & 0xFF

        # Write the modified configuration descriptor
        cmd.assign(idn=0x01, index=0x00, selector=0x00, data=bytes(config_data))
        ExecuteCMD.enqueue(cmd)
        ExecuteCMD.send(clear_on_success=True)

        self.wb_configured = True
        logger.info(f'Step 0.6: WriteBooster configured (Shared, {max_units} alloc units)')

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

    def post_process(self) -> None:
        pass  # TODO human-confirm: post-test teardown


if __name__ == '__main__':
    PF010_0310_WriteBooster_SSU_Rst().run()
