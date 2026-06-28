# LBA Pool Deduplication for Burn-In Write/Read

Session reference: PF010_0310_WriteBooster_SSU_Rst Fixed v1 (2026-06-25)

## Problem

In burn-in loops, using `random.randint(0, max_lba)` for LBA selection can produce duplicate LBAs. When `need_compare=True` is set on `api.random_read`, the framework looks up the expected data in `self.write_record` by (lun, lba). If the same LBA was written twice with different data, the lookup returns the FIRST write's data, causing the comparison to FAIL on valid firmware (false negative) or pass incorrectly if the second write overwrote the record internally.

## Fix: Pre-built LBA Pool

In `step2()` (after READ CAPACITY returns `max_lba`), build a shuffled pool of non-repeating LBAs:

```python
def step2(self) -> None:
    # ... existing code to get self.max_lba ...
    if self.max_lba > 256:
        self._lba_pool = list(range(max(0, self.max_lba - 256)))
        random.shuffle(self._lba_pool)
    else:
        self._lba_pool = list(range(0, max(0, self.max_lba - 1)))
    self._lba_idx = 0
```

Then in burn-in write steps, select via index instead of random:

```python
def _loop4_step_write(self, loop_idx: int) -> None:
    pool_len = len(self._lba_pool)
    lba = self._lba_pool[self._lba_idx % pool_len]
    self._lba_idx += 1
    # use lba for random_write ...
```

This guarantees no LBA reuse within a single burn-in run. If more iterations than pool size are needed, rebuild the pool at the end of `step12()`.

## Write/Read Length Pairing

Also store the write data length for paired read verification:

```python
# In write step:
self._last_write_length = random.randint(1, 256)
api.random_write(..., min_size=self._last_write_length, max_size=self._last_write_length, ...)

# In read step:
api.random_read(..., min_size=self._last_write_length, max_size=self._last_write_length, ...)
```

This prevents write/read length mismatch which causes `need_compare=True` to check the wrong data range.
