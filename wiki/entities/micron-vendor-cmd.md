---
type: entity
title: "Micron Vendor-Unique Command (micron_vendor_cmd family)"
tags: [vendor-unique, vu, micron, vcmd, parameter-block, write-buffer, read-buffer]
aliases: [micron_vendor_cmd, VU command, vendor unique command, vcmd, 44-byte parameter block, 0xE1, 0xC1]
sources: [script]
created: 2026-07-06
updated: 2026-07-06
---

# Micron Vendor-Unique Command (micron_vendor_cmd family)

The family spec every Micron VU command shares. A per-VU page documents ONLY its delta
(opcode, func, transfer_length, specialized payload fields, transfer direction, returned
data meaning) and references this page for everything below.

## 44-byte Parameter Block — common header

Every VU is described by a 44-byte parameter block:

| Bytes | Field | Value / rule |
|-------|-------|--------------|
| [0] | opcode | per-VU constant |
| [1] | func | per-VU constant (family/direction selector) |
| [2..3] | transfer_length | little-endian; bytes moved in the data phase |
| [4..7] | random_stamp | random non-zero, little-endian; fresh per issue |
| [8..11] | split_pkg_index | 0 unless the VU defines split transfers |
| [12..43] | command-specific area | per-VU fields live here (each VU page defines offsets, width, endianness, and who supplies the value) |

All multi-byte fields are **little-endian** unless a VU page states otherwise.

## Transport

The parameter block is sent via **SCSI Write Buffer, vendor mode 0xE1**. When the VU
returns data, it is read back via **SCSI Read Buffer, mode 0xC1**, for exactly
`transfer_length` bytes. (See [[scsi-commands]] for the buffer commands themselves.)

## Transfer direction (decides the sender)

Each VU is exactly one of — its page MUST state which:

| Direction | Meaning |
|---|---|
| Data-In | device returns `transfer_length` bytes after the header |
| Data-Out | host sends a data payload after the header |
| No-data | header only |

The three matching sender helpers live in `Script/project_api/` — ground them via
gitnexus (`repo="GitNexusMCP"`) at generation time; this wiki intentionally carries no
code. Per-VU wrapper naming convention: `issue_<func><opcode>_<Name>` (e.g. func 0x40 +
opcode 0xB1 → `issue_40B1_...`).

## What a per-VU page must specify (nothing else)

1. Family membership (one line: "micron_vendor_cmd family — header per [[micron-vendor-cmd]]").
2. The three constants: opcode, func, transfer_length.
3. Each command-specific field: byte range **with width pinned**, endianness, value source
   (caller parameter vs constant). Field width is never left to inference — a real bug
   (CE documented loosely, implemented as 2 bytes instead of 4) came from exactly this.
4. Transfer direction (Data-In / Data-Out / No-data).
5. Meaning of returned data (what a pattern should assert), when Data-In.
