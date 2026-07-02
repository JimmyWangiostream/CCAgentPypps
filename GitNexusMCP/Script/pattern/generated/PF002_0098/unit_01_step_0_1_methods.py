=== WIKI REFS ===
NO MATCH

=== CODE REFS ===
Script/api/ufs_api/descriptors/configuration_desc/functions.py:get_config_descriptors (gitnexus rank1)
Script/api/ufs_api/descriptors/configuration_desc/functions.py:push_write_config (gitnexus rank1)

=== REVIEW FLAGS ===

=== EXTRA IMPORTS ===
from typing import List

=== METHODS ===
    def _loop0_step_0_1(self, loop_idx: int) -> None:
        # sig: api.get_config_descriptors(print: bool = False) -> List[ConfigDescriptorUnion]  via gitnexus context
        # sig: api.push_write_config(config_desc: ConfigDescriptorUnion, index: int, selector: int = 0) -> None  via gitnexus context
        config_descs = api.get_config_descriptors(print=False)
        config_descs[0].header.b3_boot_enable = api.BootEnable.BOOT_ENABLE
        api.push_write_config(config_descs[0], index=0)
        ExecuteCMD.send(clear_on_success=False)
        logger.info("Device Descriptor: bBootEnable set to BOOT_ENABLE")
