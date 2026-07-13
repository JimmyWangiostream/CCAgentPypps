# Authenticated VU - Hello (0x40F1)

## Description

The **Authenticated VU - Hello** command is used to initiate an authentication handshake between the host and the UFS device.

Upon receiving this command, the UFS device returns the information required to establish a trusted authentication session, including:

- Authentication Public Key
- 256-bit Nonce (random challenge)
- Device Unique ID (serial number)

The host uses these values to verify the authenticity of the device and proceed with subsequent authenticated Vendor Unique (VU) operations.

---

## Command Information

| Item | Value |
|--------|--------|
| Command Name | Authenticated VU - Hello |
| Function Code | 0x40 |
| Opcode | 0xF1 |
| Direction | Host → Device / Device → Host |

---

## Input

### Command Format

| Byte | Field | Value | Description |
|------|--------|--------|-------------|
| 0 | bOpcode | 0xF1 | Vendor Opcode |
| 1 | bFunc | 0x40 | Authenticated VU - Hello |
| 2-3 | hTransferLength | 0x0000 | Reserved |
| 4-7 | wRandomStamp | 0x00000000 | Reserved |
| 8-11 | wSplitPkgIndex | 0x00000000 | Reserved |
| 12-43 | Reserved | 0x00 | Reserved |

### Notes

- All reserved fields shall be set to zero.
- This command does not require any authentication payload from the host.

---

## Output

### Response Data Layout

| Offset | Size (Bytes) | Field | Description |
|----------|----------|---------|-------------|
| 0 - 383 | 384 | Authentication Public Key | Device public key used for authentication |
| 384 - 415 | 32 | Nonce | Device-generated 256-bit random challenge |
| 416 - 431 | 16 | Device Unique ID | Device serial number |

### Response Memory Map

```text
+--------------------------------------------------+
| Authentication Public Key                        |
| Offset : 0 ~ 383                                 |
| Size   : 384 Bytes                               |
+--------------------------------------------------+
| Nonce (256-bit Random Number)                    |
| Offset : 384 ~ 415                               |
| Size   : 32 Bytes                                |
+--------------------------------------------------+
| Device Unique ID (Serial Number)                 |
| Offset : 416 ~ 431                               |
| Size   : 16 Bytes                                |
+--------------------------------------------------+
```
