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
        """Step 0.1 — TEST UNIT READY (0x00). Expected: GOOD Status.

        step1 runs first, so initialise the test-wide state the later steps read.
        """
        # Test-wide state shared across steps via self.* (process() runs step1..stepN).
        self.default_lun: int = 0
        self.write_record = api.get_empty_write_record()  # src[code]: Script/api/util/write_record/functions.py:get_empty_write_record
        self.max_lba: int = 0

        logger.info('Step 0.1: TEST UNIT READY (0x00) on UFS device LUN')
        # sig: CmdSeqTestUnitReady.set_option(lun, timeout=100000, wait_queue_empty=False, delay_time=0) via reading the source file
        tur = ExecuteCMD.CmdSeqTestUnitReady()  # src[code]: Script/api/cmd_seq/cmds.py:CmdSeqTestUnitReady
        tur.set_option(api.WellKnownLUN.UFS_DEVICE, wait_queue_empty=True)  # src[code]: Script/api/ufs_api/defines/enum_define.py:WellKnownLUN.UFS_DEVICE
        # sig: IsEntry.enqueue() -> int via reading the source file
        tur.enqueue()
        ExecuteCMD.send(clear_on_success=True)
        logger.info('Step 0.1: device reported ready (GOOD Status expected)')

    def step2(self) -> None:
        """Step 0.2 — READ CAPACITY(10) (0x25). Produces: self.max_lba.

        Expected: GOOD Status; max_lba taken from the device LU capacity cache.
        """
        logger.info('Step 0.2: READ CAPACITY(10) to obtain LU capacity')
        # sig: ReadCapacity10.set_option(wait_queue_empty=None, timeout=None, delay_time=None) via reading the source file
        rc = ExecuteCMD.ReadCapacity10()  # src[code]: Script/api/cmd_seq/cmds.py:ReadCapacity10
        rc.set_option(wait_queue_empty=True)
        rc.enqueue()  # sig: IsEntry.enqueue() -> int via reading the source file
        ExecuteCMD.send(clear_on_success=True)
        # The LU capacity table is populated during device init; max LBA = capacity - 1.
        # src[code]: Script/api/__init__.py:shared (api.shared.param.gLUCapacity)
        self.max_lba = max(int(api.shared.param.gLUCapacity[self.default_lun]) - 1, 0)
        logger.info(f'Step 0.2: max_lba = {self.max_lba}')

    def step3(self) -> None:
        """Step 0.3 — READ ATTRIBUTE dExtendedUFSFeaturesSupport. Produces: self.wb_supported.

        Expected: QUERY RESPONSE Success; WriteBooster feature bit is set.
        """
        # TODO-REVIEW-NO-WIKI
        logger.info('Step 0.3: check WriteBooster support via dExtendedUFSFeaturesSupport')
        # sig: api.get_extended_ufs_features_support() -> ExtendedUFSFeaturesSupportUnion via reading the source file
        ext_feat = api.get_extended_ufs_features_support()  # src[code]: Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_ufs_features_support
        self.wb_supported = bool(ext_feat.u8_write_booster)  # src[code]: device_desc/structs.py:ExtendedUFSFeaturesSupport*.u8_write_booster
        if not self.wb_supported:
            logger.error('Step 0.3: WriteBooster NOT supported by device')
            raise api.UFS_NON_SUPPORT('WriteBooster not supported by device')  # src[code]: Script/api/exception.py:UFS_NON_SUPPORT
        logger.info('Step 0.3: WriteBooster supported (u8_write_booster=1)')

    def step4(self) -> None:
        """Step 0.4 — read the maximum WriteBooster buffer alloc units. Produces: self.max_wb_alloc_units.

        The TC reads dLUNumWriteBoosterBufferAllocUnits (per-LU, R/O). The MAX value the
        host may allocate is the Geometry Descriptor field dWriteBoosterBufferMaxNAllocUnits,
        which is what Step 0.6 needs to program a MAX-sized shared buffer.
        Expected: QUERY RESPONSE Success; max alloc units returned.
        """
        # TODO-REVIEW-NO-WIKI
        logger.info('Step 0.4: read max WriteBooster buffer alloc units (Geometry Descriptor)')
        # sig: api.get_geometry_descriptor() -> GeometryDescriptorUnion via reading the source file
        geo_desc = api.get_geometry_descriptor()  # src[code]: Script/api/ufs_api/descriptors/geometry_desc/functions.py:get_geometry_descriptor
        self.max_wb_alloc_units = int(geo_desc.l79_write_booster_buffer_max_n_alloc_units)  # src[code]: geometry_desc/structs.py:l79_write_booster_buffer_max_n_alloc_units
        logger.info(f'Step 0.4: max_wb_alloc_units = {self.max_wb_alloc_units}')

    def step5(self) -> None:
        """Step 0.5 — READ DESCRIPTOR (Configuration Descriptor). Produces: self.config_descriptor_data.

        Expected: QUERY RESPONSE Success. The parsed config descriptor list is kept so
        Step 0.6 can modify the WriteBooster fields and write it back.
        """
        # TODO-REVIEW-NO-WIKI
        logger.info('Step 0.5: READ DESCRIPTOR (Configuration Descriptor)')
        # sig: api.get_config_descriptors(print: bool=False) -> List[ConfigDescriptorUnion] via reading the source file
        self.config_descriptor_data = api.get_config_descriptors()  # src[code]: Script/api/ufs_api/descriptors/configuration_desc/functions.py:get_config_descriptors
        logger.info(f'Step 0.5: read {len(self.config_descriptor_data)} configuration descriptor block(s)')

    def step6(self) -> None:
        """Step 0.6 — WRITE DESCRIPTOR (Configuration): WriteBooster Shared Type + MAX units.

        Consumes: self.max_wb_alloc_units, self.config_descriptor_data.
        dLUNumWriteBoosterBufferAllocUnits is R/O, so the shared-buffer size is set via the
        Configuration Descriptor. Expected: QUERY RESPONSE Success.
        """
        # TODO-REVIEW-NO-WIKI
        logger.info('Step 0.6: configure WriteBooster buffer (Shared type + MAX alloc units)')
        max_units = self.max_wb_alloc_units
        if max_units == 0:
            logger.warning('Step 0.6: max_wb_alloc_units == 0 — WB buffer not allocatable, skipping config')
            self.wb_configured = False
            return

        # Modify the first config descriptor block (covers LUN 0-7) and write it back.
        config_desc = self.config_descriptor_data[0]
        config_desc.header.b17_write_booster_buffer_type = api.WriteBoosterBufferType.SHARED  # src[code]: enum_define.py:WriteBoosterBufferType.SHARED
        config_desc.header.l18_num_shared_write_booster_buffer_alloc_units = max_units  # src[code]: configuration_desc/structs.py:l18_num_shared_write_booster_buffer_alloc_units
        # sig: api.push_write_config(config_desc, index, selector=0) -> None via reading the source file
        api.push_write_config(config_desc, index=0)  # src[code]: Script/api/ufs_api/descriptors/configuration_desc/functions.py:push_write_config
        ExecuteCMD.send(clear_on_success=True)

        self.wb_configured = True
        logger.info(f'Step 0.6: WriteBooster configured (Shared, {max_units} alloc units)')

    def _loop4_step_1_1(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.1 — Enable WriteBooster (SET FLAG fWriteBoosterEn)."""
        # TODO-REVIEW-NO-WIKI
        api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: Script/api/ufs_api/attr_flag_functions.py:set_flag

    def _loop4_step_1_2(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.2 — Verify fWriteBoosterEn == 1."""
        # TODO-REVIEW-NO-WIKI
        if api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN) != 1:  # src[code]: attr_flag_functions.py:read_flag
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION('Step 1.2: expected fWriteBoosterEn == 1')

    def _loop4_step_1_3(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.3 — WRITE(10) random LBA/size; keep the write record for the
        Step 1.4 compare. Sets self.write_lba/write_len (IR contract) and self.write_data
        (the write record handed to Step 1.4 within THIS iteration)."""
        # TODO-REVIEW-NO-WIKI
        lun = self.default_lun
        max_lba = self.max_lba if self.max_lba > 0 else 1024
        self.write_lba = random.randint(0, max_lba)
        self.write_len = random.choice([4096, 8192, 16384])
        self.write_data = api.get_empty_write_record()  # src[code]: rw_functions.py:get_empty_write_record
        # sig: sequential_write(lun,start_lba,total_size,chunk_size,fua,need_compare,compare_method,write_record)
        api.sequential_write(lun=lun, start_lba=self.write_lba, total_size=self.write_len,
                             chunk_size=api.BLOCK4K_SIZE_512K_BYTE, fua=0,
                             need_compare=False, compare_method=api.CompareMethod.HW_COMPARE,
                             write_record=self.write_data)  # src[code]: rw_functions.py:sequential_write

    def _loop4_step_1_4(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.4 — READ(10) + HW compare against the Step 1.3 write record
        (self.write_data, set earlier in this iteration)."""
        # TODO-REVIEW-NO-WIKI
        api.read_compare(self.write_data, api.CompareMethod.HW_COMPARE)  # src[code]: rw_functions.py:read_compare

    def _loop4_step_1_5(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.5 — Random device reset (SSU / POR / LINKSTARTUP).
        This is the STANDARD reset; Step 2.4 reuses it. Expected: fDeviceInit == 1 after."""
        # TODO-REVIEW-NO-WIKI
        reset_type = random.choice(['SSU', 'POR', 'LINKSTARTUP'])
        logger.info(f'Step 1.5 random reset (iter {loop_idx}): {reset_type}')
        if reset_type == 'SSU':
            for power_condition in (0x02, 0x01):  # SLEEP then ACTIVE
                ssu = ExecuteCMD.StartStopUnit()  # src[code]: Script/api/cmd_seq/cmds.py:StartStopUnit
                ssu.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0,
                           power_condition=power_condition, no_flush=0, start=0)
                ssu.set_option(wait_queue_empty=True)
                ssu.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        elif reset_type == 'POR':
            por = ExecuteCMD.CmdSeqPowerCycle()  # src[code]: Script/api/cmd_seq/cmds.py:CmdSeqPowerCycle
            por.set_option(mode=api.PowerCycleMode.ALL_POWER_DOWN, wait_queue_empty=True, delay_time=100)
            por.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        else:  # LINKSTARTUP — link re-startup
            link = ExecuteCMD.CmdSeqPowerCycle()
            link.set_option(mode=api.PowerCycleMode.LINK_START_UP, wait_queue_empty=True, delay_time=100)
            link.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        if api.read_flag(idn=api.FlagIDN.DEVICE_INIT) != 1:  # src[code]: attr_flag_functions.py:read_flag
            logger.warning(f'Step 1.5 reset {reset_type}: fDeviceInit != 1 after reset')

    def _loop4_step_1_6(self, loop_idx: int) -> None:
        """Loop loop_4 Step 1.6 — Read fWriteBoosterEn after reset (volatile; log per SPEC)."""
        # TODO-REVIEW-NO-WIKI
        self.wb_flag_after_reset = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:read_flag
        logger.info(f'Step 1.6: fWriteBoosterEn after reset = {self.wb_flag_after_reset}')

    def _loop4_step_2_1(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.1 — WRITE(10) (record only; compared in Step 2.3 AFTER WB is
        disabled). Sets self.write_lba/write_len and self.write_data (the write record)."""
        # TODO-REVIEW-NO-WIKI
        lun = self.default_lun
        max_lba = self.max_lba if self.max_lba > 0 else 1024
        self.write_lba = random.randint(0, max_lba)
        self.write_len = random.choice([4096, 8192, 16384])
        self.write_data = api.get_empty_write_record()  # src[code]: rw_functions.py:get_empty_write_record
        api.sequential_write(lun=lun, start_lba=self.write_lba, total_size=self.write_len,
                             chunk_size=api.BLOCK4K_SIZE_512K_BYTE, fua=0,
                             need_compare=False, compare_method=api.CompareMethod.HW_COMPARE,
                             write_record=self.write_data)  # src[code]: rw_functions.py:sequential_write

    def _loop4_step_2_2(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.2 — Disable WriteBooster (CLEAR FLAG fWriteBoosterEn)."""
        # TODO-REVIEW-NO-WIKI
        api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:clear_flag

    def _loop4_step_2_3(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.3 — READ(10) + HW compare against the Step 2.1 record
        (data must still match after WB was disabled)."""
        # TODO-REVIEW-NO-WIKI
        api.read_compare(self.write_data, api.CompareMethod.HW_COMPARE)  # src[code]: rw_functions.py:read_compare

    def _loop4_step_2_4(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.4 — Random reset, identical to Step 1.5; reuse that helper
        rather than duplicating the SSU/POR/LINKSTARTUP logic."""
        # TODO-REVIEW-NO-WIKI
        self._loop4_step_1_5(loop_idx)

    def _loop4_step_2_5(self, loop_idx: int) -> None:
        """Loop loop_4 Step 2.5 — Verify fWriteBoosterEn == 0 after reset."""
        # TODO-REVIEW-NO-WIKI
        self.wb_disabled_state = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:read_flag
        if self.wb_disabled_state != 0:
            logger.warning(f'Step 2.5: expected fWriteBoosterEn == 0, got {self.wb_disabled_state}')

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

    def _loop4_step_3_4(self, loop_idx: int) -> None:
        """Loop loop_4 Step 3.4 — Phase-3 random reset (POR_delay / SSU+Hibernate+POR).
        Expected: fDeviceInit == 1 after the reset."""
        # TODO-REVIEW-NO-WIKI
        reset_type = random.choice(['POR_DELAY', 'SSU_HIB_POR'])
        logger.info(f'Step 3.4 phase-3 reset (iter {loop_idx}): {reset_type}')
        if reset_type == 'SSU_HIB_POR':
            for power_condition in (0x02, 0x01):  # SLEEP then ACTIVE
                ssu = ExecuteCMD.StartStopUnit()  # src[code]: Script/api/cmd_seq/cmds.py:StartStopUnit
                ssu.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0,
                           power_condition=power_condition, no_flush=0, start=0)
                ssu.set_option(wait_queue_empty=True)
                ssu.enqueue()
            ExecuteCMD.send(clear_on_success=True)
            # TODO human-confirm: exact SSU -> Hibernate -> POR sequencing for Phase 3
            por = ExecuteCMD.CmdSeqPowerCycle()  # src[code]: Script/api/cmd_seq/cmds.py:CmdSeqPowerCycle
            por.set_option(mode=api.PowerCycleMode.ALL_POWER_DOWN, wait_queue_empty=True, delay_time=100)
            por.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        else:  # POR_DELAY — Power-On Reset with a longer settle delay
            por = ExecuteCMD.CmdSeqPowerCycle()
            por.set_option(mode=api.PowerCycleMode.ALL_POWER_DOWN, wait_queue_empty=True, delay_time=1000)
            por.enqueue()
            ExecuteCMD.send(clear_on_success=True)
        if api.read_flag(idn=api.FlagIDN.DEVICE_INIT) != 1:  # src[code]: attr_flag_functions.py:read_flag
            logger.warning(f'Step 3.4 reset {reset_type}: fDeviceInit != 1 after reset')

    def _loop4_step_3_5(self, loop_idx: int) -> None:
        """Loop loop_4 Step 3.5 — Read the flush flag chosen in Step 3.3 after reset
        (self._wb_flush_idn / self._wb_flush_name, set earlier in this iteration)."""
        # TODO-REVIEW-NO-WIKI
        self.flush_flag_state = api.read_flag(idn=self._wb_flush_idn)  # src[code]: attr_flag_functions.py:read_flag
        logger.info(f'Step 3.5: {self._wb_flush_name} after reset = {self.flush_flag_state}')

    def step7(self) -> None:
        """Loop loop_4 (Burn-in) — wrapper. The loop body is decomposed into
        one helper per IR sub-step (_loop4_*), each called once per
        iteration. Control flow lives here; sub-step logic lives in the helpers."""
        _LOOP_ITERATIONS = 10  # TODO human-confirm: loop count (loop_type='condition'; not given by TC)
        for loop_idx in range(_LOOP_ITERATIONS):
            self._loop4_step_1_1(loop_idx)
            self._loop4_step_1_2(loop_idx)
            self._loop4_step_1_3(loop_idx)
            self._loop4_step_1_4(loop_idx)
            self._loop4_step_1_5(loop_idx)
            self._loop4_step_1_6(loop_idx)
            self._loop4_step_2_1(loop_idx)
            self._loop4_step_2_2(loop_idx)
            self._loop4_step_2_3(loop_idx)
            self._loop4_step_2_4(loop_idx)
            self._loop4_step_2_5(loop_idx)
            self._loop4_step_3_3(loop_idx)
            self._loop4_step_3_4(loop_idx)
            self._loop4_step_3_5(loop_idx)

    def post_process(self) -> None:
        pass  # TODO human-confirm: post-test teardown


if __name__ == '__main__':
    PF010_0310_WriteBooster_SSU_Rst().run()
