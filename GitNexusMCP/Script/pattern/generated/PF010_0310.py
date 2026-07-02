import package_root
from Script import api
from Script.lib import sdk_lib as lib
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
import Script.api.cmd_seq as ExecuteCMD
import Script.api.shared as shared
import random
import time


class PF010_0310_Write_Booster_SSU_Rst(UFSTC):
    """PF010_0310 — PF010_0310_Write-Booster-SSU-Rst-Normalized-TestFlow"""

    def pre_process(self) -> None:
        pass  # TODO human-confirm: pre-test device setup

    # ------------------------------------------------------------------
    # Shared reset helper — factors out CP-5 (fDeviceInit==1) and
    # CP-3/fWriteBoosterEn==0 verification that MUST follow every reset.
    # Called after init_tester_to_unit_ready() + access_vendor_mode().
    # ------------------------------------------------------------------
    def _verify_post_reset_flags(self, loop_idx: int, label: str) -> None:
        # CP-5: fDeviceInit must be 1 after ANY reset
        fdev = api.read_flag(idn=api.FlagIDN.DEVICE_INIT)
        if fdev != 1:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
                f"[PF010_0310] fDeviceInit must be 1 after {label}, got {fdev} (loop {loop_idx})"
            )
        # CP-3 / CP-10: fWriteBoosterEn must be 0 after ANY reset (volatile per UFS Spec 6.3.4)
        wb_en = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
        if wb_en != 0:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
                f"[PF010_0310] fWriteBoosterEn must be 0 after {label}, got {wb_en} (loop {loop_idx})"
            )
        logger.info(f"[PF010_0310] Post-reset flags OK: fDeviceInit={fdev}, fWriteBoosterEn={wb_en} ({label}, loop {loop_idx})")

    def step1(self) -> None:
        # sig: api.get_extended_ufs_features_support() -> ExtendedUFSFeaturesSupportUnion  via gitnexus context
        # Find MaxCapacity Enabled Normal LUN using shared.param.gLUCapacity (pre-computed logical block count).
        # Note: l4_num_alloc_units only exists on ConfigDescriptor sub-struct, NOT on UnitDescriptor.

        # 1. Check WriteBooster support via canonical path (NOT the FFU bit)
        # src[code]: Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_ufs_features_support
        extended_features = api.get_extended_ufs_features_support()
        wb_support = extended_features.u8_write_booster  # bit mask; != 0 means supported
        logger.info(f"[PF010_0310] WriteBooster support: {wb_support}")
        if not wb_support:
            raise api.UFS_NON_SUPPORT("WriteBooster is not supported on this device")

        # 2. Find MaxCapacity Enabled Normal LUN
        # src[wiki]: default.md -- Default LUN Selection (UserPrompt overrides ModelDefault)
        max_lun = 0
        max_capacity = 0
        max_luns = shared.param.gMaxNumberLU
        logger.info(f"[PF010_0310] Total LUNs: {max_luns}")

        for lun in range(max_luns):
            unit = shared.param.gUnit[lun]
            if unit.b3_lu_enable == 0:
                continue  # skip disabled LUNs
            # Skip Well-Known LUNs (0xC0-0xFF) per CustomerReq WriteBooster LUN Restriction
            if lun >= 0xC0:
                continue
            lun_capacity = shared.param.gLUCapacity[lun]
            logger.info(f"[PF010_0310] LUN {lun}: b3_lu_enable={unit.b3_lu_enable}, gLUCapacity={lun_capacity}")
            if lun_capacity > max_capacity:
                max_capacity = lun_capacity
                max_lun = lun

        logger.info(f"[PF010_0310] MaxCapacity Enabled LUN: {max_lun} (gLUCapacity={max_capacity})")
        if max_capacity == 0:
            raise api.UFS_NON_SUPPORT("No enabled Normal LUN with valid capacity found")

        self.max_capacity_lun = max_lun  # consumed by all loop steps
        self.wb_support = wb_support     # consumed by step2

    def step2(self) -> None:
        # sig: api.get_config_descriptors() -> list[ConfigDescriptorUnion]  via gitnexus context
        # sig: api.push_write_config(config_desc, index, selector=0)  via push_write_config context
        # sig: shared.param.gGeometry.l79_write_booster_buffer_max_n_alloc_units  via config_lun idiom
        # Set WriteBooster Buffer to SHARED type with maximum allocation units
        # src[code]: Script/api/ufs_api/descriptors/configuration_desc/functions.py:get_config_descriptors
        # src[code]: Script/pattern/rain/mutual_fun.py:config_lun (l79 field access)

        config_descs = api.get_config_descriptors()
        max_alloc_units = shared.param.gGeometry.l79_write_booster_buffer_max_n_alloc_units

        logger.info(f"[PF010_0310] Setting WB Buffer to SHARED, max_alloc_units={max_alloc_units}")

        # Set global WB buffer type to SHARED on config index 0
        config_descs[0].header.b17_write_booster_buffer_type = api.WriteBoosterBufferType.SHARED
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = max_alloc_units

        # Write all 4 config descriptor pages
        for idx in range(4):
            # src[code]: Script/api/ufs_api/descriptors/configuration_desc/functions.py:push_write_config
            api.push_write_config(config_descs[idx], index=idx)
        ExecuteCMD.send()

        self.max_alloc_units = max_alloc_units  # consumed by loop_1 steps

    # ------------------------------------------------------------------
    # Phase 1 helpers
    # ------------------------------------------------------------------
    def _loop1_step_1_1(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()  via read_attr_flag_sample.py step1
        # sig: ExecuteCMD.send()  via same source
        # Enable WriteBooster by setting fWriteBoosterEn flag
        # src[code]: Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1
        logger.info(f"[PF010_0310] Enabling WriteBooster (loop {loop_idx})")
        ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()
        ExecuteCMD.send()

    def _loop1_step_1_2(self, loop_idx: int) -> None:
        # sig: random_write(cmd_count, min_lun, max_lun, min_lba, max_lba, min_size, max_size, need_compare, compare_method, write_record) -> None
        #     via gitnexus context on Script/api/ufs_api/rw_functions.py:random_write
        # sig: api.get_empty_write_record() -> List[List[WriteRecordNode]]  via gitnexus
        # sig: api.BLOCK4K_SIZE_128K_BYTE, api.BLOCK4K_SIZE_1M_BYTE  via normal_rw_sample.py
        # sig: api.CompareMethod.HW_COMPARE  (int value, not an enum object -- anti-conflation)
        # Random write while WriteBooster is enabled -- write through WB buffer.
        # FIX (length-mismatch bug): store write_length so read-back uses the SAME length.
        # src[code]: Script/api/ufs_api/rw_functions.py:random_write
        write_record = api.get_empty_write_record()
        lun = self.max_capacity_lun
        max_lba = shared.param.gLUCapacity[lun]

        cmd_count = random.randint(8, 32)
        min_size = api.BLOCK4K_SIZE_128K_BYTE
        max_size = api.BLOCK4K_SIZE_1M_BYTE
        # Store length for read-back so read uses same data range
        write_length = random.randint(min_size, max_size)
        self._last_write_length = write_length

        logger.info(f"[PF010_0310] Random write loop {loop_idx}: lun={lun}, cmd_count={cmd_count}, length={write_length}")
        api.random_write(
            cmd_count=cmd_count,
            min_lun=lun,
            max_lun=lun,
            min_lba=0,
            max_lba=max_lba,
            min_size=write_length,
            max_size=write_length,
            need_compare=True,
            compare_method=api.CompareMethod.HW_COMPARE,
            write_record=write_record
        )
        self.write_record_p1 = write_record

    def _loop1_step_1_3(self, loop_idx: int) -> None:
        # sig: random_read(cmd_count, min_lun, max_lun, min_lba, max_lba, min_size, max_size, need_compare, write_record) -> None
        #     via gitnexus context on Script/api/ufs_api/rw_functions.py:random_read
        # Read back data written in step_1_2 using SAME length stored in self._last_write_length.
        # src[code]: Script/api/ufs_api/rw_functions.py:random_read
        lun = self.max_capacity_lun
        max_lba = shared.param.gLUCapacity[lun]
        write_record = self.write_record_p1
        write_length = getattr(self, '_last_write_length', api.BLOCK4K_SIZE_128K_BYTE)

        cmd_count = random.randint(8, 32)

        logger.info(f"[PF010_0310] Read-compare loop {loop_idx}: lun={lun}, cmd_count={cmd_count}, length={write_length}")
        api.random_read(
            cmd_count=cmd_count,
            min_lun=lun,
            max_lun=lun,
            min_lba=0,
            max_lba=max_lba,
            min_size=write_length,
            max_size=write_length,
            need_compare=True,
            write_record=write_record
        )

    def _loop1_step_1_4(self, loop_idx: int) -> None:
        # sig: init_tester_to_unit_ready(resetmode: Dcmd5ResetType, powerdown: bool = False) -> None
        #     via gitnexus context on Script/api/ufs_api/initial_device.py
        # sig: access_vendor_mode() -> None  via same source
        # Power On Reset: random HW_RESET with or without power-down.
        # After reset: CP-5 verify fDeviceInit==1, CP-3 verify fWriteBoosterEn==0.
        # src[code]: Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready
        # src[code]: Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode
        logger.info(f"[PF010_0310] POR loop {loop_idx}")
        if random.randint(0, 1):
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=False)
        else:
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
        api.access_vendor_mode()
        self._verify_post_reset_flags(loop_idx, "POR (Phase 1)")

    # ------------------------------------------------------------------
    # Phase 2 helpers
    # ------------------------------------------------------------------
    def _loop1_step_2_1(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.ClearFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()  via read_attr_flag_sample.py step1
        # sig: ExecuteCMD.send()  via same source
        # Disable WriteBooster by clearing fWriteBoosterEn flag.
        # Pattern (from volatile-flag-assert-discipline ref): read → conditional-clear → re-read assert.
        # src[code]: Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1
        logger.info(f"[PF010_0310] Disabling WriteBooster (loop {loop_idx})")
        ExecuteCMD.ClearFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_EN).enqueue()
        ExecuteCMD.send()
        # Verify flag is actually cleared (CP-4)
        wb_en_after = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
        if wb_en_after != 0:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
                f"[PF010_0310] fWriteBoosterEn must be 0 after clear, got {wb_en_after} (loop {loop_idx})"
            )

    def _loop1_step_2_2(self, loop_idx: int) -> None:
        # sig: random_write(cmd_count, min_lun, max_lun, min_lba, max_lba, min_size, max_size, need_compare, compare_method, write_record) -> None
        #     via gitnexus context on Script/api/ufs_api/rw_functions.py:random_write
        # sig: api.get_empty_write_record()  via gitnexus
        # Write without WriteBooster (WB was cleared in step_2_1).
        # FIX (length-mismatch): store length for read-back.
        # src[code]: Script/api/ufs_api/rw_functions.py:random_write
        write_record = api.get_empty_write_record()
        lun = self.max_capacity_lun
        max_lba = shared.param.gLUCapacity[lun]

        cmd_count = random.randint(8, 32)
        min_size = api.BLOCK4K_SIZE_128K_BYTE
        max_size = api.BLOCK4K_SIZE_1M_BYTE
        write_length = random.randint(min_size, max_size)
        self._last_write_length_p2 = write_length

        logger.info(f"[PF010_0310] Write-no-WB loop {loop_idx}: lun={lun}, cmd_count={cmd_count}, length={write_length}")
        api.random_write(
            cmd_count=cmd_count,
            min_lun=lun,
            max_lun=lun,
            min_lba=0,
            max_lba=max_lba,
            min_size=write_length,
            max_size=write_length,
            need_compare=True,
            compare_method=api.CompareMethod.HW_COMPARE,
            write_record=write_record
        )
        self.write_record_p2 = write_record

    def _loop1_step_2_3(self, loop_idx: int) -> None:
        # sig: random_read(cmd_count, min_lun, max_lun, min_lba, max_lba, min_size, max_size, need_compare, write_record) -> None
        #     via gitnexus context on Script/api/ufs_api/rw_functions.py:random_read
        # Read back data written in step_2_2 using SAME length stored in self._last_write_length_p2.
        # src[code]: Script/api/ufs_api/rw_functions.py:random_read
        lun = self.max_capacity_lun
        max_lba = shared.param.gLUCapacity[lun]
        write_record = self.write_record_p2
        write_length = getattr(self, '_last_write_length_p2', api.BLOCK4K_SIZE_128K_BYTE)

        cmd_count = random.randint(8, 32)

        logger.info(f"[PF010_0310] Read-compare (no-WB) loop {loop_idx}: lun={lun}, cmd_count={cmd_count}, length={write_length}")
        api.random_read(
            cmd_count=cmd_count,
            min_lun=lun,
            max_lun=lun,
            min_lba=0,
            max_lba=max_lba,
            min_size=write_length,
            max_size=write_length,
            need_compare=True,
            write_record=write_record
        )

    def _loop1_step_2_4(self, loop_idx: int) -> None:
        # sig: init_tester_to_unit_ready(resetmode: Dcmd5ResetType, powerdown: bool = False) -> None  via same source as Unit 6
        # sig: access_vendor_mode() -> None  via same source
        # Power On Reset after WB-disabled write (same idiom as step_1_4).
        # After reset: CP-5 verify fDeviceInit==1, CP-3 verify fWriteBoosterEn==0.
        # src[code]: Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready
        # src[code]: Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode
        logger.info(f"[PF010_0310] POR loop {loop_idx}")
        if random.randint(0, 1):
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=False)
        else:
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
        api.access_vendor_mode()
        self._verify_post_reset_flags(loop_idx, "POR (Phase 2)")

    # ------------------------------------------------------------------
    # Phase 3 helpers
    # ------------------------------------------------------------------
    def _loop1_step_3_1(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN).enqueue()  via same idiom as Unit 3
        # sig: ExecuteCMD.SetFlag().assign(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE).enqueue()  (same pattern)
        # sig: ExecuteCMD.send()  via same source
        # 50%/50% random: set one WB flush flag per iteration.
        # src[code]: Script/pattern/sample_code/read_attr_flag_sample.py:Pattern.step1
        if random.randint(0, 1) == 0:
            flag_idn = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN  # 0x0F
            logger.info(f"[PF010_0310] Set WB Buffer Flush En (loop {loop_idx})")
        else:
            flag_idn = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE  # 0x10
            logger.info(f"[PF010_0310] Set WB Buffer Flush During Hibernate (loop {loop_idx})")
        ExecuteCMD.SetFlag().assign(idn=flag_idn).enqueue()
        ExecuteCMD.send()

    def _loop1_step_3_2(self, loop_idx: int) -> None:
        # Random delay 0-2 seconds before next WB operation
        delay = random.uniform(0, 2)
        logger.info(f"[PF010_0310] Delay {delay:.3f}s (loop {loop_idx})")
        time.sleep(delay)

    def _loop1_step_3_3(self, loop_idx: int) -> None:
        # sig: init_tester_to_unit_ready(resetmode: Dcmd5ResetType, powerdown: bool = False) -> None
        #     via gitnexus context on Script/api/ufs_api/initial_device.py
        # sig: access_vendor_mode() -> None  via same source
        # POR after Flush Flag is set -- verify WB Buffer Flush under POR.
        # After reset: CP-5 verify fDeviceInit==1; CP-3 verify fWriteBoosterEn==0;
        # CP-10 verify flush flags == 0 (volatile).
        # src[code]: Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready
        # src[code]: Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode
        logger.info(f"[PF010_0310] POR after Flush Flag set (loop {loop_idx})")
        if random.randint(0, 1):
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=False)
        else:
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
        api.access_vendor_mode()
        self._verify_post_reset_flags(loop_idx, "POR (Phase 3 Flush)")
        # CP-10: flush flags are volatile — must be 0 after reset
        flush_en = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN)
        flush_hib = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE)
        if flush_en != 0 or flush_hib != 0:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
                f"[PF010_0310] Flush flags must be 0 after reset, got flush_en={flush_en}, flush_hib={flush_hib} (loop {loop_idx})"
            )

    def _loop1_step_3_4(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.StartStopUnit().assign(lun=WellKnownLUN, immed=int, power_condition=int, no_flush=int, start=int) -> Self
        # sig: ExecuteCMD.StartStopUnit().set_option(wait_queue_empty: bool) -> None
        # sig: ExecuteCMD.enqueue(cmd: IsEntry) -> None
        # via gitnexus context on Script/pattern/read_scan/mutual_fun.py:push_ssu
        # Enter Sleep via START STOP UNIT (Opcode 0x1B, START=0, PowerCondition=0x02).
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

    def _loop1_step_3_5(self, loop_idx: int) -> None:
        # sig: init_tester_to_unit_ready(resetmode: Dcmd5ResetType, powerdown: bool = False) -> None
        #     via gitnexus context on Script/api/ufs_api/initial_device.py
        # sig: access_vendor_mode() -> None  via same source
        # POR from Sleep state -- verify WB Buffer Flush under Sleep -> POR path.
        # After reset: CP-5 verify fDeviceInit==1; CP-3 verify fWriteBoosterEn==0;
        # CP-10 verify flush flags == 0 (volatile).
        # src[code]: Script/api/ufs_api/initial_device.py:init_tester_to_unit_ready
        # src[code]: Script/api/ufs_api/vendor_cmd/functions.py:access_vendor_mode
        logger.info(f"[PF010_0310] POR from Sleep (loop {loop_idx})")
        if random.randint(0, 1):
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=False)
        else:
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
        api.access_vendor_mode()
        self._verify_post_reset_flags(loop_idx, "POR from Sleep")
        # CP-10: flush flags are volatile — must be 0 after reset
        flush_en = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN)
        flush_hib = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE)
        if flush_en != 0 or flush_hib != 0:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
                f"[PF010_0310] Flush flags must be 0 after reset, got flush_en={flush_en}, flush_hib={flush_hib} (loop {loop_idx})"
            )

    def step3(self) -> None:
        """Loop loop_1 (Burn-in Loop) — wrapper. The loop body is decomposed into
        one helper per IR sub-step (_loop1_*), each called once per
        iteration. Control flow lives here; sub-step logic lives in the helpers."""
        _LOOP_ITERATIONS = 10  # TODO human-confirm: loop count (loop_type='condition'; not given by TC)
        for loop_idx in range(_LOOP_ITERATIONS):
            self._loop1_step_1_1(loop_idx)
            self._loop1_step_1_2(loop_idx)
            self._loop1_step_1_3(loop_idx)
            self._loop1_step_1_4(loop_idx)
            self._loop1_step_2_1(loop_idx)
            self._loop1_step_2_2(loop_idx)
            self._loop1_step_2_3(loop_idx)
            self._loop1_step_2_4(loop_idx)
            self._loop1_step_3_1(loop_idx)
            self._loop1_step_3_2(loop_idx)
            self._loop1_step_3_3(loop_idx)
            self._loop1_step_3_4(loop_idx)
            self._loop1_step_3_5(loop_idx)

    def post_process(self) -> None:
        pass  # TODO human-confirm: post-test teardown


if __name__ == '__main__':
    PF010_0310_Write_Booster_SSU_Rst().run()
