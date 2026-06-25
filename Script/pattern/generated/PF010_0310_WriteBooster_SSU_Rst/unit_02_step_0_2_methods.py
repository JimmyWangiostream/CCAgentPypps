=== GROUNDING LOG ===
Step: step_0_2 (READ CAPACITY)
Source: Script/api/cmd_seq/cmds.py — ReadCapacity10
Returns: logical_block_count -> max_lba

=== EXTRA IMPORTS ===

=== METHODS ===
    def step2(self) -> None:
        """Step 0.2: Get max_lba via READ CAPACITY(10)

        Expected: GOOD Status, logical_block_count >= 1
        """
        logger.info('Step 0.2: Issue READ CAPACITY(10) to get max LBA')
        capacity = ExecuteCMD.ReadCapacity10()
        ExecuteCMD.send(clear_on_success=True)
        # Extract max_lba from capacity response (logical_block_count - 1)
        logical_block_count = int(capacity.get('logical_block_count', 0))
        max_lba = max(logical_block_count - 1, 0)
        self.max_lba = max_lba
        logger.info(f'Step 0.2: max_lba = {self.max_lba}')
