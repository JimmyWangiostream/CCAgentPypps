=== WIKI REFS ===
entities/write-booster.md -- Canonical idiom confirms WriteBooster support via get_extended_ufs_features_support().u8_write_booster
entities/device-descriptor.md -- Device Descriptor structure reference

=== CODE REFS ===
Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_ufs_features_support (gitnexus rank1)
Script/pattern/rain/mutual_fun.py:config_lun -- idioms for reading gMaxNumberLU, gUnit[lun].b3_lu_enable, gUnit[lun].l4_num_alloc_units
Script/api/ufs_api/descriptors/device_desc/functions.py:get_device_descriptor (caller of get_extended_ufs_features_support)
Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_write_booster_support (rank2)

=== REVIEW FLAGS ===
(empty)

=== EXTRA IMPORTS ===
(none needed -- shared.param already accessible via Script.api level access pattern)

=== METHODS ===
    def step1(self) -> None:
        # sig: api.get_extended_ufs_features_support() -> ExtendedUFSFeaturesSupportUnion  via gitnexus context
        # sig: shared.param access pattern from Script/pattern/rain/mutual_fun.py:config_lun
        # Procedure: enumerate enabled Normal LUNs, pick the one with highest dNumAllocUnits
        import Script.api.shared as shared

        # 1. Check WriteBooster support via canonical path (NOT the FFU bit)
        # src[code]: Script/api/ufs_api/descriptors/device_desc/functions.py:get_extended_ufs_features_support
        extended_features = api.get_extended_ufs_features_support()
        wb_support = extended_features.u8_write_booster  # bit mask; != 0 means supported
        logger.info(f"[PF010_0310] WriteBooster support: {wb_support}")
        if not wb_support:
            raise api.UFS_NON_SUPPORT("WriteBooster is not supported on this device")

        # 2. Find MaxCapacity Enabled Normal LUN
        # src[wiki]: default.md -- Default LUN Selection (UserPrompt overrides ModelDefault)
        # Procedure: enumerate all enabled Normal LUNs, read dNumAllocUnits, pick highest
        max_lun = 0
        max_alloc_units = 0
        max_luns = shared.param.gMaxNumberLU  # idiom from config_lun
        logger.info(f"[PF010_0310] Total LUNs: {max_luns}")

        for lun in range(max_luns):
            # Access cached unit descriptor via shared.param -- idiom from config_lun
            unit = shared.param.gUnit[lun]
            if unit.b3_lu_enable == 0:
                continue  # skip disabled LUNs
            # Skip Boot LUNs and Well-Known LUNs per CustomerReq WriteBooster LUN Restriction
            # bBootEnable is in device descriptor; Well-Known LUNs are 0xC0-0xFF
            if lun >= 0xC0:
                continue
            alloc_units = unit.l4_num_alloc_units
            logger.info(f"[PF010_0310] LUN {lun}: b3_lu_enable={unit.b3_lu_enable}, l4_num_alloc_units={alloc_units}")
            if alloc_units > max_alloc_units:
                max_alloc_units = alloc_units
                max_lun = lun

        logger.info(f"[PF010_0310] MaxCapacity Enabled LUN: {max_lun} (alloc_units={max_alloc_units})")
        if max_alloc_units == 0:
            raise api.UFS_NON_SUPPORT("No enabled Normal LUN with valid allocation units found")

        self.max_capacity_lun = max_lun  # consumed by step_0_2 and all loop steps
        self.wb_support = wb_support     # consumed by step_0_2
