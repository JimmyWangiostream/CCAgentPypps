# Target Environment

Project-wide defaults for the device-under-test that the TC does not itself pin.
Edit these per project. A single TC may override any of them via its own frontmatter
(e.g. `ufs_version: "3.1"` in the TC `.md` frontmatter wins for that TC).

## Target UFS spec version

Used deterministically: it selects the versioned Script structs (`DeviceDescriptor310/400/410`)
and lets the generator/validator exclude version-unavailable APIs (e.g.
`get_extended_write_booster_support` is UFS 4.1-only). Accepts `3.1` / `4.0` / `4.1`.

ufs_version: 4.1
