from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import List

# Windows Drive Type Constants
DRIVE_UNKNOWN = 0
DRIVE_NO_ROOT_DIR = 1
DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3
DRIVE_REMOTE = 4
DRIVE_CDROM = 5
DRIVE_RAMDISK = 6


def get_available_roots(include_removable: bool = True, include_network: bool = False) -> List[Path]:
    """Discover accessible drive roots on Windows, or standard roots on POSIX systems."""
    if os.name == "nt":
        return _get_windows_drives(include_removable=include_removable, include_network=include_network)
    return _get_posix_roots()


def _get_windows_drives(include_removable: bool = True, include_network: bool = False) -> List[Path]:
    valid_roots: List[Path] = []
    try:
        kernel32 = ctypes.windll.kernel32
        bitmask = kernel32.GetLogicalDrives()
        
        allowed_types = {DRIVE_FIXED}
        if include_removable:
            allowed_types.add(DRIVE_REMOVABLE)
        if include_network:
            allowed_types.add(DRIVE_REMOTE)

        for i in range(26):
            if bitmask & (1 << i):
                drive_str = f"{chr(65 + i)}:\\"
                drive_type = kernel32.GetDriveTypeW(drive_str)
                if drive_type in allowed_types:
                    path = Path(drive_str)
                    try:
                        if path.exists():
                            valid_roots.append(path)
                    except OSError:
                        pass
    except Exception:
        # Fallback if ctypes call fails
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            p = Path(f"{letter}:\\")
            try:
                if p.exists():
                    valid_roots.append(p)
            except OSError:
                pass

    # Ensure C:\ is first if it exists
    valid_roots.sort(key=lambda p: (str(p).upper() != "C:\\", str(p)))
    return valid_roots


def _get_posix_roots() -> List[Path]:
    roots = [Path.home()]
    for candidate in [Path("/"), Path("/mnt"), Path("/media"), Path("/Volumes")]:
        if candidate.is_dir():
            roots.append(candidate)
    return roots
