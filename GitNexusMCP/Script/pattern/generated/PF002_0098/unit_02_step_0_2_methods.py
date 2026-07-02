=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/attr_flag_functions.py:write_attribute (gitnexus rank1)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===
import random

=== METHODS ===
    def _loop0_step_0_2(self, loop_idx: int) -> None:
        # sig: api.write_attribute(idn: int, val: int, index: int = 0, selector: int = 0) -> None  via gitnexus context
        api.write_attribute(idn=api.AttributeIDN.BOOT_LUN_EN, val=api.BootLUNID.BOOT_LUN_A)
        logger.info("bBootLunEn set to BOOT_LUN_A")
