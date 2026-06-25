import package_root
from Script import api
from Script.lib import sdk_lib as lib
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
import Script.api.cmd_seq as ExecuteCMD
import Script.api.shared as shared
import random
import time


class PF010_0310_WriteBooster_SSU_Rst(UFSTC):
    """PF010_0310 — PF010_0310_WriteBooster_SSU_Rst-Normalized-TestFlow"""

    def pre_process(self) -> None:
        pass  # TODO human-confirm: pre-test device setup

    def step1(self) -> None:
        """step_0_1 — TEST UNIT READY (0x00): confirm every enabled LUN is ready (GOOD Status)."""
        param = shared.param  # src[code]: Script/api/shared.py
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable:
                tur = ExecuteCMD.TestUnitReady()  # src[code]: Script/api/cmd_seq/cmds.py:TestUnitReady
                tur.assign(lun)
                ExecuteCMD.enqueue(tur)
        ExecuteCMD.send(clear_on_success=True)
        logger.info("step1: TEST UNIT READY — GOOD Status confirmed for all enabled LUNs")

    def step2(self) -> None:
        """step_0_2 — READ CAPACITY(10) (0x25): obtain MAX_LBA and pick the test LUN.

        gLUCapacity[] is populated during device init from gUnit[].q11_logical_block_count;
        READ CAPACITY(10) is issued to confirm GOOD Status on each enabled LUN.
        """
        param = shared.param
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable:
                rc = ExecuteCMD.ReadCapacity10()  # src[code]: Script/api/cmd_seq/cmds.py:ReadCapacity10
                rc.assign(lun)
                ExecuteCMD.enqueue(rc)
        ExecuteCMD.send(clear_on_success=True)
        # produces: max_lba — first enabled LUN with non-zero capacity is the W/R target
        self._test_lun: int = 0
        self.max_lba: int = 0
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable and param.gLUCapacity[lun] > 0:  # src[code]: Script/api/shared.py:gLUCapacity
                self._test_lun = lun
                self.max_lba = param.gLUCapacity[lun]
                break
        logger.info(f"step2: test_lun={self._test_lun}, max_lba={self.max_lba}")

    def step3(self) -> None:
        """step_0_3 — confirm WriteBooster support via dExtendedUFSFeaturesSupport.

        NOTE: the TC labels this 'READ ATTRIBUTE', but dExtendedUFSFeaturesSupport is a
        Device Descriptor field (offset 4Fh–52h), not an AttributeIDN. The library helper
        reads the Device Descriptor and exposes the WriteBooster support bit (bit 8).
        """
        # produces: wb_supported
        ext = api.get_extended_ufs_features_support()  # src[code]: device_desc/functions.py:get_extended_ufs_features_support
        self.wb_supported = bool(ext.u8_write_booster)  # src[code]: ExtendedUFSFeaturesSupport.u8_write_booster (bit 8)
        if not self.wb_supported:
            logger.warning("step3: WriteBooster NOT supported (dExtendedUFSFeaturesSupport.u8_write_booster=0)")
            raise api.UFS_NON_SUPPORT
        logger.info("step3: WriteBooster supported (dExtendedUFSFeaturesSupport.u8_write_booster=1)")

    def step4(self) -> None:
        """step_0_4 — obtain MAX WriteBooster shared-buffer alloc units.

        NOTE: the TC labels this 'READ ATTRIBUTE IDN 0x17', but AttributeIDN 0x17 is
        REF_CLK_GATING_WAIT_TIME. dLUNumWriteBoosterBufferAllocUnits is a Configuration
        Descriptor header field — read it from the Configuration Descriptor instead.
        """
        # src[code]: configuration_desc/functions.py:get_config_descriptors
        self._config_descs = api.get_config_descriptors(print=False)
        # produces: max_alloc_units
        # src[code]: ConfigDescriptorHeader.l18_num_shared_write_booster_buffer_alloc_units
        self.max_alloc_units: int = self._config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units
        logger.info(f"step4: max WriteBooster shared-buffer alloc units = {self.max_alloc_units}")

    def step5(self) -> None:
        """step_0_5 — READ DESCRIPTOR Configuration Descriptor (IDN 0x01): read and log full config."""
        # produces: config_descriptor_data
        # src[code]: configuration_desc/functions.py:get_config_descriptors ; DescriptorIDN.CONFIGURATION=0x01
        self.config_descriptor_data = api.get_config_descriptors(print=True)
        logger.info("step5: Configuration Descriptor read and logged")

    def step6(self) -> None:
        """step_0_6 — WRITE DESCRIPTOR Configuration Descriptor: Shared WB type + MAX alloc units.

        consumes: config_descriptor_data (step5), max_alloc_units (step4).
        """
        config_descs = self.config_descriptor_data
        # bWriteBoosterBufferType = 0x01 (Shared) ; apply MAX shared alloc units from step4
        # src[wiki]: wiki/entities/configuration-descriptor.md
        config_descs[0].header.b17_write_booster_buffer_type = 0x01  # src[code]: ConfigDescriptorHeader.b17_write_booster_buffer_type
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = self.max_alloc_units
        for index in range(4):
            api.push_write_config(config_descs[index], index=index)  # src[code]: configuration_desc/functions.py:push_write_config
        ExecuteCMD.send(clear_on_success=True)
        # NOTE: WRITE DESCRIPTOR on Configuration Descriptor requires bConfigDescrLock=0 and
        # typically a device reset to take effect.
        # TODO human-confirm: whether a reset is required here before the burn-in loop
        logger.info("step6: WRITE DESCRIPTOR Configuration — Shared WB type + MAX alloc units applied")

    # loop_4 is condition-typed in the TC (no fixed count) — fixed placeholder count used.
    _BURN_IN_LOOP_COUNT = 10  # TODO human-confirm: real loop termination condition

    def step7(self) -> None:
        """loop_4 — Burn-in loop. Each iteration runs three inlined sub-phases:
        Phase1 WB Enable + W/R + Reset, Phase2 WB Disable + W/R + Reset, Phase3 Flush + Reset.

        consumes: max_lba / _test_lun (from step2). Loop is condition-typed in the TC;
        a fixed _BURN_IN_LOOP_COUNT is used as a placeholder.
        """
        lun = self._test_lun
        max_lba = self.max_lba

        def do_reset(rt: str) -> None:
            """Inlined reset dispatch (kept local so step7 stays a single method).
            SSU = START STOP UNIT power transition; POR = power cycle; LINKSTARTUP = re-link.
            """
            if rt == "SSU":
                # START STOP UNIT to low-power (power_condition=0x02), then bring device back to unit-ready
                ExecuteCMD.StartStopUnit().assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0,
                                                  power_condition=0x02, no_flush=0, start=0
                                                  ).set_option(wait_queue_empty=True).enqueue()  # src[code]: read_disturb RD_Flush SSU idiom
                ExecuteCMD.send(clear_on_success=True)
                api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=False)
            elif rt in ("POR", "POR_delay"):
                if rt == "POR_delay":
                    time.sleep(random.uniform(0, 2))  # POR with delay
                api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)  # src[code]: initial_device.py:init_tester_to_unit_ready (POR = power cycle)
            elif rt == "LINKSTARTUP":
                api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=False)  # reset + re-link, no power cycle
            elif rt == "SSU+Hibernate+POR":
                # TODO human-confirm: explicit Hibernate enter/exit step (DCMD6 SSU_HIBERNATE_FLOW) before POR
                ExecuteCMD.StartStopUnit().assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0,
                                                  power_condition=0x02, no_flush=0, start=0
                                                  ).set_option(wait_queue_empty=True).enqueue()
                ExecuteCMD.send(clear_on_success=True)
                api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
            else:
                api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)

        for iteration in range(self._BURN_IN_LOOP_COUNT):
            logger.info(f"=== Burn-in iteration {iteration + 1}/{self._BURN_IN_LOOP_COUNT} ===")

            # ---- Phase 1: WB Enable + W/R + Reset -------------------------------
            # step_1_1: SET FLAG fWriteBoosterEn (0x0E)
            api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:set_flag ; FlagIDN.WRITEBOOSTER_EN=0x0E
            logger.info("step_1_1: SET FLAG fWriteBoosterEn")

            # step_1_2: READ FLAG fWriteBoosterEn -> expect 1
            wb_en = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:read_flag
            if wb_en != 1:
                logger.error(f"step_1_2: fWriteBoosterEn expected 1, got {wb_en}")
                raise api.SPEC_ASSERT_UFS_RSP_VALUE_NOT_MATCH  # src[code]: Script/api/exception
            logger.info(f"step_1_2: fWriteBoosterEn={wb_en}")

            # step_1_3: WRITE(10) random LBA/length (consumes max_lba)
            self.write_record = api.get_empty_write_record()  # src[code]: Script/api/util/write_record
            api.random_write(cmd_count=1, min_lun=lun, max_lun=lun, min_lba=0, max_lba=max_lba,
                             min_size=1, max_size=256, need_compare=True,
                             compare_method=api.CompareMethod.HW_COMPARE,
                             write_record=self.write_record, fua=0)  # src[code]: rw_functions.py:random_write
            logger.info("step_1_3: WRITE(10) random data")

            # step_1_4: READ(10) compare -> GOOD Status + Data Match
            api.read_compare(self.write_record, compare_method=api.CompareMethod.HW_COMPARE)  # src[code]: rw_functions.py:read_compare
            logger.info("step_1_4: READ(10) compare passed")

            # step_1_5: Random Reset (SSU / POR / LINKSTARTUP)
            reset_type = random.choice(["SSU", "POR", "LINKSTARTUP"])
            do_reset(reset_type)
            logger.info(f"step_1_5: Random Reset={reset_type} -> device unit-ready")

            # step_1_6: READ FLAG fWriteBoosterEn after reset (volatile)
            wb_after = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
            # TODO human-confirm: expected fWriteBoosterEn value after reset (volatile flag per spec)
            logger.info(f"step_1_6: fWriteBoosterEn after {reset_type} reset={wb_after}")

            # ---- Phase 2: WB Disable + W/R + Reset ------------------------------
            # step_2_1: WRITE(10) (FUA=0)
            self.write_record = api.get_empty_write_record()
            api.random_write(cmd_count=1, min_lun=lun, max_lun=lun, min_lba=0, max_lba=max_lba,
                             min_size=1, max_size=256, need_compare=True,
                             compare_method=api.CompareMethod.HW_COMPARE,
                             write_record=self.write_record, fua=0)
            logger.info("step_2_1: WRITE(10) random data (FUA=0)")

            # step_2_2: CLEAR FLAG fWriteBoosterEn
            api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: attr_flag_functions.py:clear_flag
            logger.info("step_2_2: CLEAR FLAG fWriteBoosterEn")

            # step_2_3: READ(10) compare
            api.read_compare(self.write_record, compare_method=api.CompareMethod.HW_COMPARE)
            logger.info("step_2_3: READ(10) compare passed")

            # step_2_4: Random Reset
            reset_type = random.choice(["SSU", "POR", "LINKSTARTUP"])
            do_reset(reset_type)
            logger.info(f"step_2_4: Random Reset={reset_type}")

            # step_2_5: READ FLAG fWriteBoosterEn -> expect 0 (disabled)
            wb_dis = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
            if wb_dis != 0:
                logger.warning(f"step_2_5: fWriteBoosterEn={wb_dis} after disable+reset; expected 0")
            logger.info(f"step_2_5: fWriteBoosterEn after disable={wb_dis}")

            # ---- Phase 3: Flush Enable + Reset ----------------------------------
            # step_3_1/3_2: branch 50%/50% SET FLAG flush flag
            # NOTE: TC labels flush IDNs 0x0B/0x0C, but the code enum is 0x0F/0x10 — code wins.
            flush_flag = random.choice([
                api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN,                # src[code]: FlagIDN=0x0F
                api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE,  # src[code]: FlagIDN=0x10
            ])
            api.set_flag(idn=flush_flag)
            logger.info(f"step_3_1/3_2: SET FLAG {flush_flag.name}")

            # step_3_3: random delay 0–2s (wait for flush trigger)
            delay_s = random.uniform(0, 2)
            time.sleep(delay_s)
            logger.info(f"step_3_3: random delay {delay_s:.2f}s")

            # step_3_4: Random Reset (POR_delay / SSU+Hibernate+POR)
            reset_type = random.choice(["POR_delay", "SSU+Hibernate+POR"])
            do_reset(reset_type)
            logger.info(f"step_3_4: Random Reset={reset_type}")

            # step_3_5: READ FLAG (the flush flag chosen above) after reset
            flush_val = api.read_flag(idn=flush_flag)
            # TODO human-confirm: expected flush flag value after reset (volatile per spec)
            logger.info(f"step_3_5: {flush_flag.name} after reset={flush_val}")

    def post_process(self) -> None:
        pass  # TODO human-confirm: post-test teardown


if __name__ == '__main__':
    PF010_0310_WriteBooster_SSU_Rst().run()
