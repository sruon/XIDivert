#!/usr/bin/env python3
"""
XIDivert - FFXI Event DAT Redirection Tool
Patches VTABLE.DAT and FTABLE.DAT to redirect event DAT lookups to custom ROM folders.
"""

import os
import shutil
import stat
import struct
import sys
from pathlib import Path

import yaml


def load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_ffxi_path(ffxi_path: str) -> Path:
    path = Path(ffxi_path)
    if not path.exists():
        raise ValueError(f"FFXI path does not exist: {ffxi_path}")
    for dat in ["VTABLE.DAT", "FTABLE.DAT"]:
        if not (path / dat).exists():
            raise ValueError(f"{dat} not found in: {ffxi_path}")
    return path


def validate_rom_folder(rom_folder: int) -> int:
    if not isinstance(rom_folder, int) or rom_folder < 10 or rom_folder > 255:
        raise ValueError(f"rom_folder must be between 10 and 255, got: {rom_folder}")
    return rom_folder


def validate_swaps(swaps: list, swaps_dir: Path) -> list:
    validated = []
    for i, swap in enumerate(swaps):
        name = swap.get("name", f"Swap {i}")
        path = swap.get("path")
        if not path:
            raise ValueError(f"Swap '{name}' missing 'path' field")

        swap_path = swaps_dir / path
        if not swap_path.is_dir():
            raise ValueError(f"Swap '{name}' folder not found: {swap_path}")

        for dat in ["events.DAT", "strings.DAT"]:
            if not (swap_path / dat).exists():
                raise ValueError(f"Swap '{name}' missing {dat}")

        validated.append({
            "name": name,
            "path": path,
            "events_dat": swap_path / "events.DAT",
            "strings_dat": swap_path / "strings.DAT",
            "entity_ids": swap.get("entity_ids", {}),
        })
    return validated


def find_free_slots(vtable_path: Path, count: int, start: int = 400) -> list[int]:
    with open(vtable_path, "rb") as f:
        vtable = f.read()

    free = []
    for tt in range(start, 1000):
        if len(free) >= count:
            break
        data_idx, mess_idx = tt + 57881, 57945 + tt
        if data_idx < len(vtable) and mess_idx < len(vtable):
            if vtable[data_idx] == 0 and vtable[mess_idx] == 0:
                free.append(tt)

    if len(free) < count:
        raise ValueError(f"Could not find {count} free slots (found {len(free)})")
    return free


def replace_entity_ids(events_dat: Path, entity_ids: dict) -> int:
    with open(events_dat, "rb") as f:
        data = f.read()

    total = 0
    for old_id, new_id in entity_ids.items():
        old_bytes = struct.pack("<I", old_id)
        new_bytes = struct.pack("<I", new_id)
        count = data.count(old_bytes)
        if count > 0:
            data = data.replace(old_bytes, new_bytes)
            total += count

    if total > 0:
        with open(events_dat, "wb") as f:
            f.write(data)
    return total


def patch_tables(vtable_path: Path, ftable_path: Path, swaps: list, rom_folder: int):
    with open(vtable_path, "rb") as f:
        vtable = bytearray(f.read())
    with open(ftable_path, "rb") as f:
        ftable = bytearray(f.read())

    for swap in swaps:
        tt, folder = swap["text_table"], swap["folder_num"]
        data_idx, mess_idx = tt + 57881, 57945 + tt

        vtable[data_idx] = rom_folder
        vtable[mess_idx] = rom_folder

        for idx, file_num in [(data_idx, 1), (mess_idx, 2)]:
            val = (folder << 7) | file_num
            ftable[idx * 2] = val & 0xFF
            ftable[idx * 2 + 1] = (val >> 8) & 0xFF

    with open(vtable_path, "wb") as f:
        f.write(vtable)
    with open(ftable_path, "wb") as f:
        f.write(ftable)


def write_divert_lua(output_dir: Path, swaps: list):
    lua_path = output_dir / "divert.lua"
    with open(lua_path, "w", encoding="utf-8") as f:
        f.write("xi.divert =\n{\n")
        for swap in swaps:
            f.write(f"    {swap['path'].upper()} = {swap['text_table']},\n")
        f.write("}\n")


def main():
    script_dir = Path(__file__).parent
    manifest_path = script_dir / "manifest.yaml"

    print(f"Loading manifest: {manifest_path}")
    try:
        manifest = load_manifest(manifest_path)
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        ffxi_path = validate_ffxi_path(manifest.get("ffxi_path", ""))
        rom_folder = validate_rom_folder(manifest.get("rom_folder", 0))
        swaps = validate_swaps(manifest.get("swaps", []), script_dir / "swaps")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not swaps:
        print("No swaps defined")
        sys.exit(0)

    print(f"FFXI: {ffxi_path}")
    print(f"ROM folder: ROM{rom_folder}/")
    print(f"Swaps: {len(swaps)}")

    output_dir = script_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy and patch tables
    for dat in ["VTABLE.DAT", "FTABLE.DAT"]:
        shutil.copy2(ffxi_path / dat, output_dir / dat)

    vtable_path = output_dir / "VTABLE.DAT"
    ftable_path = output_dir / "FTABLE.DAT"

    # Find free slots and assign to swaps
    free_slots = find_free_slots(vtable_path, len(swaps))
    for i, swap in enumerate(swaps):
        swap["text_table"] = free_slots[i]
        swap["folder_num"] = i + 1

    # Copy swap DATs
    print(f"\nProcessing swaps:")
    for swap in swaps:
        rom_path = output_dir / f"ROM{rom_folder}" / str(swap["folder_num"])
        rom_path.mkdir(parents=True, exist_ok=True)

        events_dst = rom_path / "1.DAT"
        strings_dst = rom_path / "2.DAT"

        shutil.copy2(swap["events_dat"], events_dst)
        shutil.copy2(swap["strings_dat"], strings_dst)

        os.chmod(events_dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        os.chmod(strings_dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

        entity_ids = swap.get("entity_ids", {})
        replacements = replace_entity_ids(events_dst, entity_ids) if entity_ids else 0

        print(f"  {swap['path']} -> text_table={swap['text_table']}", end="")
        if replacements:
            print(f" ({replacements} entity replacements)", end="")
        print()

    # Patch tables
    patch_tables(vtable_path, ftable_path, swaps, rom_folder)

    # Write divert.lua
    write_divert_lua(output_dir, swaps)
    print(f"\nGenerated: {output_dir / 'divert.lua'}")

    print("\nDone! Copy output/ contents to your FFXI installation.")


if __name__ == "__main__":
    main()
