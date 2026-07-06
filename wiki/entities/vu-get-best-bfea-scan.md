---
type: entity
title: "VU Get_Best_Bfea_Scan (0xB1/0x40)"
tags: [vendor-unique, vu, bfea, micron, opcode-b1, func-40, virtual-block, chip-enable, scan]
aliases: [0xB1, 40B1, Get_Best_Bfea_Scan, issue_40B1_Get_Best_Bfea_Scan, micron_vu_40B1, BFEA scan, best BFEA bin]
sources: [customerreq, script]
created: 2026-07-06
updated: 2026-07-06
---

# VU Get_Best_Bfea_Scan (0xB1/0x40)

Micron vendor-unique command: run a best-BFEA scan against a specific VB/CE and return
the scan result. **micron_vendor_cmd family** — 44-byte parameter block, transport,
direction/sender mapping and naming convention all per [[micron-vendor-cmd]]; this page
is the per-VU delta only.

## Command Parameters

| Field | Value | Payload offset |
|-------|-------|----------------|
| opcode | 0xB1 | byte[0] |
| func | 0x40 | byte[1] |
| transfer_length | 0x1000 | byte[2..3], little-endian |
| VB (virtual block) | caller-supplied | byte[12..15], little-endian |
| CE (chip enable / die) | caller-supplied | **byte[16..19], little-endian (4 bytes — width is normative)** |

Direction: **Data-In** — device returns 0x1000 (4096) bytes.

CE width is ruled by CustomerReq (2026-07-05); a conflicting implementation was found —
resolution and the fail-loud rule are recorded in [[conflicts]] Conflict #3.

## Returned data

Raw 4096-byte buffer holding the best-BFEA scan result ("best BFEA bin") for the
requested VB/CE. The internal field layout of the buffer is not documented here —
**TODO human-confirm before asserting on buffer contents** (do not invent offsets).

## Related

[[micron-vendor-cmd]] — family header, transport, sender mapping
[[conflicts]] — Conflict #3: CE field width (CustomerReq vs implementation)
