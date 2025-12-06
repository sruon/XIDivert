# Reference

## Index Offsets

For `EventNum2 = X` (where X ≠ current zone):

| Entry | Index Formula |
|-------|---------------|
| Event DATA | `X + 57881` |
| Event MESS | `57945 + X` |

Client adds 1000 internally when `EventNum2` differs from zone, then applies offset.

## VTABLE.DAT - ROM Folder Selector

1 byte per entry. Specifies which ROM folder to use:

| Value | Folder |
|-------|--------|
| 0 | File doesn't exist |
| 1 | ROM/ |
| 2-255 | ROM{n}/ |

## FTABLE.DAT - Folder/File Encoding

2 bytes per entry (little-endian). Encodes path within ROM:

```
value = (folder << 7) | file

folder = value >> 7      (0-511)
file   = value & 0x7F    (0-127)
```

## Path Resolution (sub_101C1DF0)

```c
v8 = FTABLE[index];  // 2 bytes
v9 = VTABLE[index];  // 1 byte

if (!v9)
    return -1;  // File doesn't exist

if (v9 == 1)
    sprintf(path, "/ROM/%d/%d.DAT", v8 >> 7, v8 & 0x7F);
else
    sprintf(path, "/ROM%d/%d/%d.DAT", v9, v8 >> 7, v8 & 0x7F);
```

## GetLangBasedFileId Lookup (English)

Memory: `FFXiMain.dll + 0x6346BC` → pointer to table

| Entry | Value | Used For |
|-------|-------|----------|
| 105 | 6420 | Event MESS zones 0-255 |
| 106 | 57945 | Event MESS zones 1000-1999 (EventNum2) |
| 107 | 68511 | Event MESS zones 2000+ |
| 108 | 85591 | Event MESS zones 256-999 |

## Client Functions

| Function | Purpose |
|----------|---------|
| `FUNC_Packet_Incoming_0x0034_RecvEventCalcNum` | Handles event packet |
| `FUNC_InitEvent` | Initializes event, adds +1000 offset |
| `FUNC_Inline_ReadEventDataFile` | Loads event script DAT |
| `FUNC_Inline_ReadEventMessFile` | Loads event text DAT |
| `FUNC_Helper_GetLangBasedFileId` | Language-specific FTABLE base |
| `sub_101C1DF0` | Resolves FTABLE index to ROM path |

## File Sizes

- VTABLE.DAT: 109,701 bytes
- FTABLE.DAT: 219,402 bytes (2x VTABLE)
