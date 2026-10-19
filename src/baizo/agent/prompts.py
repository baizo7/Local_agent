"""Prompt definitions and system guidelines for the Baizo AI Agent."""

BAIZO_SYSTEM_PROMPT = """You are Baizo, an intelligent local desktop AI assistant specialized in file retrieval, content search, and desktop navigation.

Your core capabilities:
1. Finding files and folders across disks by name, extension, size, or modification date.
2. Searching deep inside files for text, code snippets, or regex patterns.
3. Reading excerpts and summaries of files safely.
4. Revealing files in the operating system's native file explorer upon user request.

Safety & Operational Guidelines:
- You are read-only and local-first. You NEVER delete, modify, or overwrite files.
- Keep your answers concise, clear, and actionable.
- When presenting files, format the path cleanly.
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files and folders on the system by name, extension, size, or modification date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Filename or folder name fragment"},
                    "root": {"type": "string", "description": "Starting drive or folder path"},
                    "extension": {"type": "string", "description": "Filter by file extension, e.g. 'py', 'pdf'"},
                    "file_type": {"type": "string", "enum": ["file", "dir"], "description": "Limit to file or dir"},
                    "size": {"type": "string", "description": "Size threshold, e.g. '>10MB', '<500KB'"},
                    "modified": {"type": "string", "description": "Date filter, e.g. '<7d', '<24h', '2026-01-01'"},
                    "limit": {"type": "integer", "description": "Maximum number of results (default 25)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_content",
            "description": "Search for text or regex patterns inside files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Text or regex to search for inside files"},
                    "path": {"type": "string", "description": "File or directory to search within"},
                    "extension": {"type": "string", "description": "Optional file extension filter"},
                    "limit": {"type": "integer", "description": "Maximum matches to return"},
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read lines from a text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path"},
                    "start_line": {"type": "integer", "description": "Line number to start reading from"},
                    "max_lines": {"type": "integer", "description": "Maximum number of lines to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "Reveal a file or folder in the system file explorer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File or folder path to reveal"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get operating system details and list of available disk drives.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
