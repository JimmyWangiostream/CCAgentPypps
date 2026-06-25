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
        """step_0_1 — TEST UNIT READY (0x00): 確認裝置就緒."""
        param = shared.param
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable:
                ExecuteCMD.TestUnitReady().assign(lun=lun).enqueue()  # src[code]: api/cmd_seq/cmds.py:299
        ExecuteCMD.send(clear_on_success=True)
        logger.info("step1: TEST UNIT READY — GOOD Status confirmed for all enabled LUNs")

    def step2(self) -> None:
        """step_0_2 — READ CAPACITY(10) (0x25): 取得 MAX_LBA."""
        param = shared.param
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable:
                ExecuteCMD.ReadCapacity10().assign(lun=lun).enqueue()  # src[code]: api/cmd_seq/cmds.py:184
        ExecuteCMD.send(clear_on_success=True)
        # gLUCapacity is populated by ExecuteCMD.send after ReadCapacity10 # src[code]: api/ufs_api/rw_functions.py:25
        self._test_lun: int = 0
        self.max_lba: int = 0
        for lun in range(param.gMaxNumberLU):
            if param.gUnit[lun].b3_lu_enable and param.gLUCapacity[lun] > 0:
                self._test_lun = lun
                self.max_lba = param.gLUCapacity[lun]
                break
        logger.info(f"step2: test_lun={self._test_lun}, max_lba={self.max_lba}")

    def step3(self) -> None:
        """step_0_3 — READ ATTRIBUTE dExtendedUFSFeaturesSupport: 確認 WB 支援."""
        # dExtendedUFSFeaturesSupport is NOT in AttributeIDN enum (code-grounded enum ends at 0x1B).
        # The attribute is cached in shared.param.gDevice after first_init_to_max_hs_gear.
        # TODO human-confirm: verify IDN value for dExtendedUFSFeaturesSupport in this codebase's AttributeIDN enum
        param = shared.param
        ext_features = param.gDevice.l79_extended_ufs_features_support  # TODO human-confirm: field name
        WB_SUPPORT_BIT = 0  # bit 0 = WriteBooster support per JESD220H §14.1 # src[wiki]: wiki/Spec/
        if not (ext_features & (1 << WB_SUPPORT_BIT)):
            logger.warning("step3: dExtendedUFSFeaturesSupport bit0=0 — WB not supported")
            raise api.UFS_NON_SUPPORT
        logger.info(f"step3: dExtendedUFSFeaturesSupport=0x{ext_features:08X} — WB supported")

    def step4(self) -> None:
        """step_0_4 — READ dLUNumWriteBoosterBufferAllocUnits: 取得 max alloc units.

        Per UFS SPEC JESD220H §14.3.1, dLUNumWriteBoosterBufferAllocUnits is a
        READ-ONLY field inside Configuration Descriptor, NOT a standalone Attribute.
        TC note 'IDN 0x17' likely refers to the descriptor field offset, not AttributeIDN.
        """
        # TODO human-confirm: AttributeIDN.0x17 maps to REF_CLK_GATING_WAIT_TIME in code,
        #   not dLUNumWriteBoosterBufferAllocUnits. Read via Configuration Descriptor instead.
        config_descs = api.get_config_descriptors(print=False)  # src[code]: api/ufs_api/descriptors/configuration_desc/functions.py:18
        self._config_descs = config_descs
        self.max_alloc_units: int = config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units  # TODO human-confirm: field name
        logger.info(f"step4: WB shared buffer alloc units = {self.max_alloc_units}")

    def step5(self) -> None:
        """step_0_5 — READ DESCRIPTOR Configuration Descriptor (IDN 0x01): log full config."""
        api.get_config_descriptors(print=True)  # src[code]: api/ufs_api/descriptors/configuration_desc/functions.py:18
        # src[code]: DescriptorIDN.CONFIGURATION=0x01 @ api/ufs_api/defines/enum_define.py:123
        logger.info("step5: Configuration Descriptor logged")

    def step6(self) -> None:
        """step_0_6 — WRITE DESCRIPTOR Configuration Descriptor: Shared Type + MAX alloc units."""
        config_descs = self._config_descs
        # bWriteBoosterBufferType = 0x01 (Shared buffer) per JESD220H
        # src[wiki]: wiki/Spec/ — Shared WriteBooster buffer type
        config_descs[0].header.b17_write_booster_buffer_type = 0x01  # TODO human-confirm: field name
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = self.max_alloc_units  # TODO human-confirm: field name
        for i in range(4):
            config_descs[i].header.b2_conf_desc_continue = 0 if i == 3 else 1  # TODO human-confirm: field name
            api.push_write_config(config_descs[i], index=i)  # src[code]: api/ufs_api/descriptors/configuration_desc/functions.py:52
        ExecuteCMD.send(clear_on_success=True)
        logger.info("step6: WRITE DESCRIPTOR Configuration — WB Shared Type + MAX alloc units applied")

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

    def post_process(self) -> None:
        pass  # TODO human-confirm: post-test teardown


if __name__ == '__main__':
    PF010_0310_WriteBooster_SSU_Rst().run()
