=== WIKI REFS ===
entities/flags.md — fWriteBoosterEn / flush flags accessed via SET/READ/CLEAR FLAG; volatile flags reset on power cycle
entities/scsi-commands.md — WRITE(10)/READ(10) for the W/R compare phases; START STOP UNIT (1Bh) for SSU power transitions

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py: set_flag / read_flag / clear_flag (gitnexus rank1) — return flag value
Script/api/ufs_api/rw_functions.py: random_write / read_compare (rank2) — random W/R + HW compare via write_record
Script/api/ufs_api/initial_device.py: init_tester_to_unit_ready(resetmode, powerdown) (rank3) — powerdown=True -> POR, powerdown=False -> reset/link
Script/pattern/read_disturb/PSW_F_P3_Read_Disturb_0004_RD_Flush_Test.py: StartStopUnit().assign(lun=UFS_DEVICE, immed, power_condition, no_flush, start) (rank4) — SSU idiom
Script/api/ufs_api/defines/enum_define.py: FlagIDN.WRITEBOOSTER_EN=0x0E, WRITEBOOSTER_BUFFER_FLUSH_EN=0x0F, WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE=0x10 (rank5)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===
import random
import time
import Script.api.shared as shared

=== METHODS ===
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
