import package_root
from Script import api
from Script.lib import sdk_lib as lib
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
import Script.api.cmd_seq as ExecuteCMD
from typing import List
import random


class PF002_0098_Boot_Stress_Test(UFSTC):
    """PF002_0098 — PF002_0098_Boot_Stress_Test-Normalized-TestFlow"""

    def pre_process(self) -> None:
        pass  # TODO human-confirm: pre-test device setup

    def _loop0_step_0_1(self, loop_idx: int) -> None:
        # sig: api.get_config_descriptors(print: bool = False) -> List[ConfigDescriptorUnion]  via gitnexus context
        # sig: api.push_write_config(config_desc: ConfigDescriptorUnion, index: int, selector: int = 0) -> None  via gitnexus context
        # sig: api.read_config_descriptor(index: int, selector: int = 0) -> ConfigDescriptorUnion
        config_descs = api.get_config_descriptors(print=False)
        config_descs[0].header.b3_boot_enable = api.BootEnable.BOOT_ENABLE
        api.push_write_config(config_descs[0], index=0)
        ExecuteCMD.send(clear_on_success=False)
        # Verify write succeeded
        verify_descs = api.get_config_descriptors(print=False)
        if verify_descs[0].header.b3_boot_enable != api.BootEnable.BOOT_ENABLE:
            raise api.PATTERN_ASSERT_EXECUTOR_UNIDENTIFIED_RESPONSE(
                f"bBootEnable verify failed: expected {api.BootEnable.BOOT_ENABLE}, "
                f"got {verify_descs[0].header.b3_boot_enable}"
            )
        logger.info("Device Descriptor: bBootEnable set to BOOT_ENABLE")

    def _loop0_step_0_2(self, loop_idx: int) -> None:
        # sig: api.write_attribute(idn: int, val: int, index: int = 0, selector: int = 0) -> None  via gitnexus context
        # sig: api.read_attribute(idn: int, index: int = 0, selector: int = 0) -> int
        api.write_attribute(idn=api.AttributeIDN.BOOT_LUN_EN, val=api.BootLUNID.BOOT_LUN_A)
        # Verify write succeeded
        verify_val = api.read_attribute(idn=api.AttributeIDN.BOOT_LUN_EN)
        if verify_val != api.BootLUNID.BOOT_LUN_A:
            raise api.PATTERN_ASSERT_EXECUTOR_UNIDENTIFIED_RESPONSE(
                f"BOOT_LUN_EN verify failed: expected {api.BootLUNID.BOOT_LUN_A}, got {verify_val}"
            )
        logger.info("bBootLunEn set to BOOT_LUN_A")

    def _loop0_step_0_3(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.Write10() -> Write10  via gitnexus context
        # sig: cmd.assign(lun: int, lba: int, length: int, fua: int) -> Self  (BaseWrite10.assign)
        # sig: cmd.set_option(wait_queue_empty: bool = None, pattern_mode: CmdParamPatternMode = None) -> Self
        # sig: ExecuteCMD.enqueue(cmd) -> int
        # sig: ExecuteCMD.send(clear_on_success: bool = False) -> None
        import random
        import Script.api.shared as shared

        # Boot W-LUN address: 0xB0 = BOOT_WELL_KNOWN_LU_A (JESD220H Section 10.6.5)
        boot_lun = 0xB0
        lun_desc = shared.param.gUnit[boot_lun]
        total_blocks = getattr(lun_desc, 'q11_logical_block_count', 0)
        test_blocks = min(total_blocks, 128)  # write 128 blocks max for test pattern

        write10 = ExecuteCMD.Write10()
        write10.assign(lun=boot_lun, lba=0, length=test_blocks, fua=0)
        write10.set_option(
            wait_queue_empty=True,
            pattern_mode=api.CmdParamPatternMode.HW_FIX
        )
        cmd_idx = ExecuteCMD.enqueue(write10)
        ExecuteCMD.send(clear_on_success=False)

        self.boot_lun_id = boot_lun
        self.write_pattern = 'HW_FIX'
        self.written_lba_start = 0
        self.written_transfer_length = test_blocks
        logger.info(f"Written test pattern to Boot LUN 0x{boot_lun:02X}: {test_blocks} blocks")

    def _loop0_step_1_1(self, loop_idx: int) -> None:
        # sig: api.init_tester_to_unit_ready(resetmode: Dcmd5ResetType, stop_after_device_init: bool = False, ...) -> None
        # Randomly select one of 4 reset types: HW_RESET, RST_N, ENDPOINT_RESET, UNIPRO_RESET
        reset_types = [
            api.Dcmd5ResetType.HW_RESET,
            api.Dcmd5ResetType.RESET_N,
            api.Dcmd5ResetType.ENDPOINT_RESET,
            api.Dcmd5ResetType.UNIPRO_RESET,
        ]
        selected_reset = random.choice(reset_types)
        logger.info(f"[Loop {loop_idx}] Selected reset type: {selected_reset.name} (0x{selected_reset.value:02X})")
        # Issue reset only; stop before device-init so Step 2_1 can confirm readiness
        api.init_tester_to_unit_ready(resetmode=selected_reset, stop_after_device_init=True)
        logger.info(f"[Loop {loop_idx}] Reset {selected_reset.name} issued")

    def _loop0_step_2_1(self, loop_idx: int) -> None:
        # sig: api.init_tester_to_unit_ready(resetmode: Dcmd5ResetType, stop_after_device_init: bool = False, ...) -> None
        # sig: api.FlagIDN.DEVICE_INIT = 0x01 (fDeviceInit flag)
        # Complete device init after reset: call with default (no reset) to wait for ready
        api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.SKIP_RESET, stop_after_device_init=False)
        logger.info(f"[Loop {loop_idx}] Device initialized and ready after reset")

    def _loop0_step_2_2(self, loop_idx: int) -> None:
        # sig: ExecuteCMD.Read10() -> Read10  via gitnexus context
        # sig: cmd.assign(lun: int, lba: int, length: int, fua: int) -> Self  (BaseRead10.assign)
        # sig: ExecuteCMD.enqueue(cmd) -> int
        # sig: ExecuteCMD.send(clear_on_success: bool = False) -> None
        boot_lun = getattr(self, 'boot_lun_id', 0xB0)
        lba_start = getattr(self, 'written_lba_start', 0)
        transfer_len = getattr(self, 'written_transfer_length', 128)

        read10 = ExecuteCMD.Read10()
        read10.assign(lun=boot_lun, lba=lba_start, length=transfer_len, fua=0)
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

    def step1(self) -> None:
        """Loop loop_0 (Burn-in Loop) — wrapper. The loop body is decomposed into
        one helper per IR sub-step (_loop0_*), each called once per
        iteration. Control flow lives here; sub-step logic lives in the helpers."""
        _LOOP_ITERATIONS = 10  # TODO human-confirm: loop count (loop_type='condition'; not given by TC)
        for loop_idx in range(_LOOP_ITERATIONS):
            self._loop0_step_0_1(loop_idx)
            self._loop0_step_0_2(loop_idx)
            self._loop0_step_0_3(loop_idx)
            self._loop0_step_1_1(loop_idx)
            self._loop0_step_2_1(loop_idx)
            self._loop0_step_2_2(loop_idx)

    def post_process(self) -> None:
        pass  # TODO human-confirm: post-test teardown


if __name__ == '__main__':
    PF002_0098_Boot_Stress_Test().run()
