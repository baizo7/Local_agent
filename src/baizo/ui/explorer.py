from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_path_in_file_manager(path: Path) -> bool:
    """Reveal or open the given path in the operating system's native file manager."""
    try:
        resolved = path.resolve()
        if not resolved.exists():
            return False

        if os.name == "nt":
            if resolved.is_file():
                # Highlight file in Windows File Explorer
                subprocess.Popen(["explorer", f"/select,{str(resolved)}"])
            else:
                os.startfile(str(resolved))  # type: ignore[attr-defined]
            return True
        elif sys.platform == "darwin":
            if resolved.is_file():
                subprocess.Popen(["open", "-R", str(resolved)])
            else:
                subprocess.Popen(["open", str(resolved)])
            return True
        else:
            target = resolved if resolved.is_dir() else resolved.parent
            subprocess.Popen(["xdg-open", str(target)])
            return True
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"Error opening location: {exc}", file=sys.stderr)
        return False


def copy_to_clipboard(text: str) -> bool:
    """Copy the provided text string to the system clipboard."""
    try:
        # Check if pyperclip is installed
        import pyperclip  # type: ignore

        pyperclip.copy(text)
        return True
    except ImportError:
        pass

    # Platform native fallback
    try:
        if os.name == "nt":
            process = subprocess.Popen(["clip.exe"], stdin=subprocess.PIPE, shell=True)
            process.communicate(text.encode("utf-16"))
            return process.returncode == 0
        elif sys.platform == "darwin":
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-8"))
            return process.returncode == 0
        else:
            for tool in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                try:
                    p = subprocess.Popen(tool, stdin=subprocess.PIPE)
                    p.communicate(text.encode("utf-8"))
                    return p.returncode == 0
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return False
