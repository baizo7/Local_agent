from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .tools import tool_find_files, tool_get_system_info, tool_grep_content, tool_open_file, tool_read_file


class NaturalLanguageIntentEngine:
    """Offline heuristic natural language parser for Baizo desktop tasks."""

    KNOWN_EXTENSIONS = {
        "python": "py",
        "py": "py",
        "javascript": "js",
        "typescript": "ts",
        "pdf": "pdf",
        "word": "docx",
        "excel": "xlsx",
        "csv": "csv",
        "json": "json",
        "markdown": "md",
        "text": "txt",
        "html": "html",
        "css": "css",
        "rust": "rs",
        "go": "go",
    }

    def process(self, query: str) -> Tuple[str, Dict[str, Any]]:
        clean_query = query.strip()
        lower = clean_query.lower()

        # Check for system info
        if any(k in lower for k in ["system info", "show drives", "list drives", "hardware info", "pc info"]):
            res = tool_get_system_info()
            roots_str = ", ".join(res["available_roots"])
            msg = f"🖥️ System: {res['os']} {res['release']} ({res['machine']})\nAccessible Drives: {roots_str}\nHome Directory: {res['home']}"
            return msg, {"tool": "get_system_info", "data": res}

        # Check for read file intention
        read_match = re.search(r"\b(read|cat|view|show content of)\s+([\"']?)([^\"']+)\2", clean_query, re.IGNORECASE)
        if read_match:
            candidate_path = read_match.group(3).strip()
            if Path(candidate_path).is_file():
                res = tool_read_file(candidate_path, max_lines=40)
                if "content" in res:
                    msg = f"📄 Content of {candidate_path} (first {res['lines_read']} lines):\n\n{res['content']}"
                    return msg, {"tool": "read_file", "data": res}

        # Check for grep/content search intention
        grep_match = re.search(
            r"\b(grep|search inside|find text|search for text|contains|content of)\s+[\"']([^\"']+)[\"'](?:\s+in\s+([\"']?)([^\"']+)\3)?",
            clean_query,
            re.IGNORECASE,
        )
        if grep_match:
            pattern = grep_match.group(2).strip()
            target_path = (grep_match.group(4) or os.getcwd()).strip()
            res = tool_grep_content(pattern=pattern, path=target_path)
            if res.get("match_count", 0) > 0:
                lines = [f"Found {res['match_count']} occurrence(s) for '{pattern}':"]
                for m in res["matches"][:10]:
                    lines.append(f"  • {m['file']}:{m['line']} -> {m['text']}")
                return "\n".join(lines), {"tool": "grep_content", "data": res}
            else:
                return f"No occurrences of '{pattern}' found in {target_path}.", {"tool": "grep_content", "data": res}

        # Check for find files / locate intention
        wants_open = any(k in lower for k in ["and open", "reveal", "open it", "launch", "open "])

        # Standard user directories
        standard_dirs = {
            "downloads": Path.home() / "Downloads",
            "documents": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop",
            "pictures": Path.home() / "Pictures",
            "videos": Path.home() / "Videos",
            "music": Path.home() / "Music",
            "home": Path.home(),
        }

        # 1. Parse target root path if explicitly specified (e.g. "in D:\projects", "in C:\Users\...")
        root: Optional[str] = None
        in_match = re.search(r"\b(in|from)\s+(my\s+)?([A-Za-z]:[\\/][^\s\"']+|downloads|documents|desktop|pictures|videos)", clean_query, re.IGNORECASE)
        if in_match:
            raw_root = in_match.group(3)
            lower_root = raw_root.lower()
            if lower_root in standard_dirs:
                root = str(standard_dirs[lower_root])
            else:
                root = raw_root
            clean_query = clean_query[:in_match.start()] + " " + clean_query[in_match.end():]
            lower = clean_query.lower()

        # 2. Check for explicit drive mention (e.g. "D drive", "D disk drive", "D:", "drive D", "disk D", "in D")
        explicit_drive: Optional[str] = None
        if root is None:
            drive_regexes = [
                (r"\b([a-zA-Z]):(?![\\/][A-Za-z0-9_])", 1),
                (r"\b(?:drive|disk)\s+([a-zA-Z])\b", 1),
                (r"\b([a-zA-Z])\s+(?:disk\s+drive|drive|disk)\b", 1),
                (r"\b(?:in|on|from)\s+([a-zA-Z])\b", 1),
            ]
            for pattern_str, group_idx in drive_regexes:
                m = re.search(pattern_str, clean_query, re.IGNORECASE)
                if m:
                    candidate_letter = m.group(group_idx).upper()
                    if len(candidate_letter) == 1 and candidate_letter.isalpha():
                        if candidate_letter == "A" and not (":" in m.group(0) or "drive" in m.group(0).lower() or "disk" in m.group(0).lower()):
                            continue
                        explicit_drive = candidate_letter
                        clean_query = clean_query[:m.start()] + " " + clean_query[m.end():]
                        lower = clean_query.lower()
                        break

        # 3. Check if the user is asking directly for their standard user folder
        # (e.g., "find my downloads folder", "where is my desktop", "open downloads")
        for folder_name, default_path in standard_dirs.items():
            pattern = rf"\b(my\s+)?{folder_name}(\s+folder|\s+directory)?\b"
            if re.search(pattern, lower):
                # Ensure the user isn't asking to search inside it (e.g. "find file in downloads")
                if not re.search(rf"\b(in|from)\s+(my\s+)?{folder_name}", lower):
                    if explicit_drive:
                        drive_root = Path(f"{explicit_drive}:\\")
                        candidates = [
                            drive_root / folder_name.capitalize(),
                            drive_root / folder_name.lower(),
                            drive_root / folder_name.upper(),
                        ]
                        found_target = None
                        for cand in candidates:
                            try:
                                if cand.is_dir():
                                    found_target = cand
                                    break
                            except OSError:
                                pass

                        if found_target:
                            if wants_open or lower.startswith("open"):
                                tool_open_file(str(found_target))
                                return f"📂 Opened your {folder_name.capitalize()} folder on drive {explicit_drive}:\\ in File Explorer:\n   {found_target}", {"tool": "open_file", "path": str(found_target)}
                            return f"📁 Your {folder_name.capitalize()} folder on drive {explicit_drive}:\\ is located at:\n   {found_target}", {"tool": "find_files", "path": str(found_target)}

                        # Search specifically on that drive
                        res = tool_find_files(query=folder_name, root=str(drive_root), file_type="dir", limit=5)
                        if res.get("count", 0) > 0:
                            top = res["results"][0]["path"]
                            if wants_open or lower.startswith("open"):
                                tool_open_file(top)
                                return f"📂 Opened your {folder_name.capitalize()} folder on drive {explicit_drive}:\\ in File Explorer:\n   {top}", {"tool": "open_file", "path": top}
                            return f"📁 Your {folder_name.capitalize()} folder on drive {explicit_drive}:\\ is located at:\n   {top}", {"tool": "find_files", "path": top}
                    else:
                        if wants_open or lower.startswith("open"):
                            tool_open_file(str(default_path))
                            return f"📂 Opened your {folder_name.capitalize()} folder in File Explorer:\n   {default_path}", {"tool": "open_file", "path": str(default_path)}
                        return f"📁 Your {folder_name.capitalize()} folder is located at:\n   {default_path}", {"tool": "find_files", "path": str(default_path)}
        
        # Parse extension
        ext: Optional[str] = None
        for alias, ext_code in self.KNOWN_EXTENSIONS.items():
            ext_pattern = re.compile(rf"\b{alias}\s+(files?|scripts?|documents?)\b", re.IGNORECASE)
            if ext_pattern.search(clean_query):
                ext = ext_code
                clean_query = ext_pattern.sub(" ", clean_query)
                break

        # Parse date
        modified: Optional[str] = None
        if "today" in lower:
            modified = "<24h"
        elif "yesterday" in lower:
            modified = "<48h"
        elif "this week" in lower or "past week" in lower:
            modified = "<7d"
        elif "this month" in lower:
            modified = "<30d"

        # Parse size
        size: Optional[str] = None
        size_match = re.search(r"\b(larger than|greater than|>|\+)\s*([\d.]+)\s*(kb|mb|gb)", lower)
        if size_match:
            size = f">{size_match.group(2)}{size_match.group(3)}"
        else:
            size_match_less = re.search(r"\b(smaller than|less than|<|-)\s*([\d.]+)\s*(kb|mb|gb)", lower)
            if size_match_less:
                size = f"<{size_match_less.group(2)}{size_match_less.group(3)}"

        # If explicit drive was specified and root wasn't set, default root to that drive
        if root is None and explicit_drive:
            root = f"{explicit_drive}:\\"

        # Detect folder vs file intention
        file_type: Optional[str] = None
        if re.search(r"\b(folders?|directories?|directory)\b", clean_query, re.IGNORECASE):
            file_type = "dir"
        elif re.search(r"\b(files?)\b", clean_query, re.IGNORECASE):
            file_type = "file"

        # Extract search keywords and remove conversational noise
        cleaned = re.sub(
            r"\b(find|search for|locate|where is|where are|show me|list all|all|files?|folders?|directories?|directory|disk\s+drive|drive|disk|my|the|a|an|please|can you|could you|and open it|and open)\b",
            "",
            clean_query,
            flags=re.IGNORECASE,
        )
        # Remove size phrases
        cleaned = re.sub(r"\b(larger|smaller|greater|less)\s+than\s+[\d.]+\s*[a-zA-Z]+\b", "", cleaned, flags=re.IGNORECASE)
        # Remove date phrases
        cleaned = re.sub(r"\b(today|yesterday|this week|past week|this month)\b", "", cleaned, flags=re.IGNORECASE)
        # Extract quoted query if present
        quote_match = re.search(r"[\"']([^\"']+)[\"']", clean_query)
        target_name = quote_match.group(1) if quote_match else cleaned.strip()

        # If extension was found but query contains it, keep query clean
        if ext and target_name.endswith(f".{ext}"):
            pass

        res = tool_find_files(
            query=target_name,
            root=root,
            extension=ext,
            file_type=file_type,
            size=size,
            modified=modified,
            limit=15,
        )

        count = res.get("count", 0)
        if count == 0:
            return f"No files found matching '{target_name}'. Try broadening your search or specifying a different folder.", {"tool": "find_files", "data": res}

        items = res.get("results", [])
        lines = [f"Found {count} matching item(s):"]
        for idx, item in enumerate(items[:10], start=1):
            kind = "DIR " if item["is_dir"] else "FILE"
            lines.append(f"  {idx}. [{kind}] {item['size']:>8}  {item['name']}  ({item['path']})")

        if wants_open and items:
            first_path = items[0]["path"]
            tool_open_file(first_path)
            lines.append(f"\n📂 Opened first match in File Explorer: {first_path}")

        return "\n".join(lines), {"tool": "find_files", "data": res}
