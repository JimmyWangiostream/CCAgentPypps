=== GROUNDING LOG ===
python graph_query.py FlagIDN → api/ufs_api/defines/enum_define.py:133 (FlagIDN) — WRITEBOOSTER_EN=0x0E, WRITEBOOSTER_BUFFER_FLUSH_EN=0x0F, WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE=0x10, DEVICE_INIT=0x01
python graph_query.py set_flag → api/ufs_api/attr_flag_functions.py:115 (set_flag)
python graph_query.py clear_flag → api/ufs_api/attr_flag_functions.py:133 (clear_flag)
python graph_query.py read_flag → api/ufs_api/attr_flag_functions.py:97 (read_flag)
python graph_query.py Write10 → api/cmd_seq/cmds.py:359 (Write10) — assign(lun, lba, length, fua)
python graph_query.py Read10 → api/cmd_seq/cmds.py:122 (Read10) — assign(lun, lba, length, fua=0), set_hw_cmp(mark_tag, pattern_mode)
python graph_query.py BaseWrite10 → api/ufs_api/upiu/upiu.py:403 (BaseWrite10) — assign(lun, lba, length, fua: int)
python graph_query.py BaseRead10 → api/ufs_api/upiu/upiu.py:128 (BaseRead10) — assign(lun, lba, length, fua=0)
python graph_query.py StartStopUnit → api/cmd_seq/cmds.py:266 (StartStopUnit) — assign(lun, immed, power_condition, no_flush, start)
python graph_query.py BaseStartStopUnit → api/ufs_api/upiu/upiu.py:266 (BaseStartStopUnit) — assign(lun, immed, power_condition, no_flush, start)
python graph_query.py init_tester_to_unit_ready → api/ufs_api/initial_device.py:69 (init_tester_to_unit_ready)
python graph_query.py Dcmd5ResetType → api/ufs_api/debug_cmd/dcmd_enum.py:51 (Dcmd5ResetType) — HW_RESET=0, ENDPOINT_RESET=2
python graph_query.py CmdParamPatternMode → api/ufs_api/defines/enum_define.py:490 (CmdParamPatternMode) — HW_FIX=2

=== EXTRA IMPORTS ===
import random
import time
import Script.api.shared as shared

=== METHODS ===
    # loop_type=condition, no fixed count in TC
    _BURN_IN_LOOP_COUNT = 10  # TODO human-confirm: exact loop termination condition

    def step7(self) -> None:
        """loop_4 — Burn-in: Phase1 (WB Enable+W/R+Reset) + Phase2 (WB Disable+W/R+Reset) + Phase3 (Flush+Reset).

        Loop type=condition; using fixed BURN_IN_LOOP_COUNT as placeholder.
        All three sub-phases are inlined per-iteration.
        """
        lun = self._test_lun
        max_lba = self.max_lba

        for iteration in range(self._BURN_IN_LOOP_COUNT):
            logger.info(f"=== Burn-in iteration {iteration + 1}/{self._BURN_IN_LOOP_COUNT} ===")

            # ── Phase 1: WB Enable + W/R + Reset ────────────────────────────
            logger.info("--- Phase 1: WB Enable ---")

            # step_1_1: SET FLAG fWriteBoosterEn (IDN 0x0E)
            api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: api/ufs_api/attr_flag_functions.py:115
            # src[code]: FlagIDN.WRITEBOOSTER_EN=0x0E @ api/ufs_api/defines/enum_define.py:144
            logger.info("step_1_1: SET FLAG fWriteBoosterEn")

            # step_1_2: READ FLAG fWriteBoosterEn → expect 1
            wb_en = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: api/ufs_api/attr_flag_functions.py:97
            if wb_en != 1:
                raise api.SPEC_ASSERT_FLAG_VALUE_MISMATCH(f"step_1_2: fWriteBoosterEn expected 1, got {wb_en}")  # TODO human-confirm: exception class name
            logger.info(f"step_1_2: fWriteBoosterEn={wb_en} ✓")

            # step_1_3: WRITE(10) test data — random LBA + length
            length = random.randint(1, 256)
            lba = random.randint(0, max(0, max_lba - length))
            mark_tag = lba & 0xFFFFFFFF
            w = ExecuteCMD.Write10()  # src[code]: api/cmd_seq/cmds.py:359
            w.assign(lun=lun, lba=lba, length=length, fua=0)
            w.set_option(pattern_mode=api.CmdParamPatternMode.HW_FIX)  # src[code]: api/ufs_api/defines/enum_define.py:492
            ExecuteCMD.enqueue(w)
            ExecuteCMD.send(clear_on_success=True)
            logger.info(f"step_1_3: WRITE(10) lun={lun} lba={lba} length={length}")

            # step_1_4: READ(10) compare — expect GOOD Status + Data Match
            r = ExecuteCMD.Read10()  # src[code]: api/cmd_seq/cmds.py:122
            r.assign(lun=lun, lba=lba, length=length)
            r.set_hw_cmp(mark_tag=mark_tag, pattern_mode=api.CmdParamPatternMode.HW_FIX)
            ExecuteCMD.enqueue(r)
            ExecuteCMD.send(clear_on_success=True)
            logger.info(f"step_1_4: READ(10) compare passed")

            # step_1_5: Random Reset (SSU / POR / LINKSTARTUP)
            # TODO human-confirm: exact mapping of SSU/POR/LINKSTARTUP to Dcmd5ResetType
            reset_type = random.choice([
                api.Dcmd5ResetType.HW_RESET,       # covers SSU power cycle and POR
                api.Dcmd5ResetType.ENDPOINT_RESET,  # covers LINKSTARTUP
            ])  # src[code]: api/ufs_api/debug_cmd/dcmd_enum.py:51
            logger.info(f"step_1_5: Random Reset type={reset_type.name}")
            api.init_tester_to_unit_ready(resetmode=reset_type)  # src[code]: api/ufs_api/initial_device.py:69

            # step_1_6: READ FLAG fWriteBoosterEn after reset — confirm volatile flag state
            wb_en_after = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: api/ufs_api/attr_flag_functions.py:97
            # Per JESD220H, fWriteBoosterEn is volatile: value after reset depends on spec # src[wiki]: wiki/Spec/
            # TODO human-confirm: expected value of fWriteBoosterEn after reset (volatile vs persistent)
            logger.info(f"step_1_6: fWriteBoosterEn after reset={wb_en_after} (spec-confirm required)")

            # ── Phase 2: WB Disable + W/R + Reset ──────────────────────────
            logger.info("--- Phase 2: WB Disable ---")

            # step_2_1: WRITE(10) test data (FUA=0)
            length2 = random.randint(1, 256)
            lba2 = random.randint(0, max(0, max_lba - length2))
            mark_tag2 = lba2 & 0xFFFFFFFF
            w2 = ExecuteCMD.Write10()  # src[code]: api/cmd_seq/cmds.py:359
            w2.assign(lun=lun, lba=lba2, length=length2, fua=0)
            w2.set_option(pattern_mode=api.CmdParamPatternMode.HW_FIX)
            ExecuteCMD.enqueue(w2)
            ExecuteCMD.send(clear_on_success=True)
            logger.info(f"step_2_1: WRITE(10) lun={lun} lba={lba2} length={length2} FUA=0")

            # step_2_2: CLEAR FLAG fWriteBoosterEn (IDN 0x0E)
            api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: api/ufs_api/attr_flag_functions.py:133
            logger.info("step_2_2: CLEAR FLAG fWriteBoosterEn")

            # step_2_3: READ(10) compare
            r2 = ExecuteCMD.Read10()  # src[code]: api/cmd_seq/cmds.py:122
            r2.assign(lun=lun, lba=lba2, length=length2)
            r2.set_hw_cmp(mark_tag=mark_tag2, pattern_mode=api.CmdParamPatternMode.HW_FIX)
            ExecuteCMD.enqueue(r2)
            ExecuteCMD.send(clear_on_success=True)
            logger.info("step_2_3: READ(10) compare passed")

            # step_2_4: Random Reset (same types as step_1_5)
            reset_type2 = random.choice([
                api.Dcmd5ResetType.HW_RESET,
                api.Dcmd5ResetType.ENDPOINT_RESET,
            ])  # src[code]: api/ufs_api/debug_cmd/dcmd_enum.py:51
            # TODO human-confirm: exact mapping of SSU/POR/LINKSTARTUP to Dcmd5ResetType
            logger.info(f"step_2_4: Random Reset type={reset_type2.name}")
            api.init_tester_to_unit_ready(resetmode=reset_type2)  # src[code]: api/ufs_api/initial_device.py:69

            # step_2_5: READ FLAG fWriteBoosterEn → expect 0 (WB disabled)
            wb_dis = api.read_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)  # src[code]: api/ufs_api/attr_flag_functions.py:97
            if wb_dis != 0:
                logger.warning(f"step_2_5: fWriteBoosterEn={wb_dis} after disable; expected 0 per TC")
                # TODO human-confirm: whether mismatch should raise or warn per spec
            logger.info(f"step_2_5: fWriteBoosterEn after disable={wb_dis}")

            # ── Phase 3: Flush Enable + Reset ──────────────────────────────
            logger.info("--- Phase 3: Flush Enable ---")

            # step_3_1/3_2: SET FLAG — random branch 50%/50%
            # src[code]: FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN=0x0F @ api/ufs_api/defines/enum_define.py:145
            # src[code]: FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE=0x10 @ api/ufs_api/defines/enum_define.py:146
            flush_flag = random.choice([
                api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN,
                api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_DURING_HIBERNATE,
            ])
            api.set_flag(idn=flush_flag)  # src[code]: api/ufs_api/attr_flag_functions.py:115
            logger.info(f"step_3_1/3_2: SET FLAG {flush_flag.name} (IDN=0x{flush_flag:02X})")

            # step_3_3: Random delay 0–2 seconds (wait for flush trigger)
            delay_s = random.uniform(0, 2)
            logger.info(f"step_3_3: Random delay {delay_s:.2f}s")
            time.sleep(delay_s)

            # step_3_4: Random Reset (POR_delay or SSU+Hibernate+POR)
            # TODO human-confirm: POR_delay and SSU+Hibernate+POR sequences not found in graph.
            # Using HW_RESET as placeholder for both complex sequences.
            logger.warning("TODO human-confirm: step_3_4 POR_delay / SSU+Hibernate+POR — exact DCMD5 sequence unresolved")
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET)  # src[code]: api/ufs_api/initial_device.py:69

            # step_3_5: READ FLAG (the flush flag selected in step_3_1/3_2) — confirm state per SPEC
            flush_val = api.read_flag(idn=flush_flag)  # src[code]: api/ufs_api/attr_flag_functions.py:97
            # TODO human-confirm: expected value of flush flag after reset (volatile per spec)
            logger.info(f"step_3_5: {flush_flag.name} after reset={flush_val} (spec-confirm required)")
