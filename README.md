# ⚡ Baizo

**Baizo** is an intelligent, local-first desktop search engine, content indexer, and AI assistant built in Python.

It operates entirely on your machine, requires zero external services by default, and delivers high-performance multi-threaded file discovery, in-file grep, SQLite FTS5 full-text indexing, and conversational AI desktop intelligence.

---

## ✨ Features Across All 3 Phases

### Phase 1: High-Performance Search Engine
- **Multi-threaded Traversal**: Concurrently crawls drives and folders via Python's `concurrent.futures`.
- **Advanced Filtering**:
  - Glob & wildcard patterns (`*.pdf`, `budget_202*`, `test_*.py`).
  - Regular expressions (`--regex`).
  - Extension filters (`--ext py,pdf,docx`).
  - File vs. Directory filters (`--type file`, `--type dir`).
  - Size thresholds (`--size ">10MB"`, `--size "<500KB"`).
  - Date ranges (`--modified "<7d"`, `--modified "<24h"`, `--modified "2026-01-01"`).
- **Windows Integration**: Fast, native drive discovery using Win32 API (`GetLogicalDrives` and `GetDriveTypeW`) to skip empty CD-ROM/network hangs.
- **Interactive Terminal UI**:
  - Colored table output with match highlighting (via `rich` with graceful ANSI fallback).
  - Interactive selection prompt when opening files (`--open`).
  - Copy results to clipboard (`--copy`).

### Phase 2: Deep Content Grep & SQLite FTS5 Indexing
- **In-File Content Search (`baizo grep`)**: Fast line-by-line grep through source code and documents with line numbering and encoding fallback.
- **SQLite FTS5 Local Indexer (`baizo index`)**:
  - Index folders and file contents into a local SQLite database (`~/.baizo/index.db`).
  - Sub-millisecond full-text search across thousands of files.
  - Incremental updates based on file modification times.

### Phase 3: Conversational "Baizo" AI Agent
- **One-Shot Assistant (`baizo ask "<prompt>"`)**: Natural language desktop requests like:
  - `baizo ask "find all python files modified this week"`
  - `baizo ask "where is invoice.pdf in downloads and open it"`
  - `baizo ask "search for 'TODO' in D:\projects"`
- **Interactive Chat (`baizo chat`)**: Full conversational terminal chat session.
- **Hybrid Intelligence**:
  - Plugs into local LLMs (Ollama, local VOLT agent gateway, or OpenAI-compatible APIs).
  - Built-in heuristic NLP engine for 100% offline intelligence without any LLM configured.
- **Read-Only Safety**: Strictly prevents accidental file deletion, modification, or arbitrary remote execution.

---

## 🚀 Installation

Requires **Python 3.10** or newer.

### Option 1: Install Directly from GitHub (Recommended)

You can install Baizo directly on any machine without manually cloning the repository:

```powershell
# Using pip
pip install git+https://github.com/baizo7/Local_agent.git

# Recommended: as an isolated global CLI tool via pipx
pipx install git+https://github.com/baizo7/Local_agent.git
```

With optional document parsers (PDF, Word, Excel, PPTX) and real-time watcher:
```powershell
pip install "git+https://github.com/baizo7/Local_agent.git#egg=baizo[all]"
```

---

### Option 2: Install from Source (For Developers)

```powershell
git clone https://github.com/baizo7/Local_agent.git
cd Local_agent
py -m pip install -e .
```

---

### Option 3: Install from Built Wheel (.whl)

If you downloaded the `.whl` package:
```powershell
py -m pip install dist/baizo-0.2.0-py3-none-any.whl
```

Once installed, both `baizo` and `jarvis` commands will be immediately available in your terminal.

---

## 📖 Usage & Examples

### 1. File & Folder Search (`baizo find`)
```powershell
# Basic search
baizo find "main.py"

# Wildcard pattern in a specific folder
baizo find "*.pdf" --root "D:\Documents"

# Filter by extension and modified within the last 7 days
baizo find "report" --ext docx,pdf --modified "<7d"

# Files larger than 50MB
baizo find "" --size ">50MB" --root "C:\Users\LENOVO\Downloads"

# Reveal in File Explorer (opens interactive picker if multiple matches)
baizo find "schema.sql" --open

# Copy matching paths to clipboard
baizo find "*.env" --copy
```

### 2. Search Inside Files (`baizo grep`)
```powershell
# Search for a function or text across a project
baizo grep "def train_model" --path "D:\projects\VOLT" --ext py

# Search with regular expression
baizo grep "API_KEY\s*=" --path "D:\projects"
```

### 3. Local SQLite FTS5 Index (`baizo index`)
```powershell
# Index a directory (including file contents for text, PDF, Word, Excel, PPTX)
baizo index add "D:\projects\agent" --content

# Instant full-text search across the index
baizo index search "SearchEngine"

# View index stats
baizo index stats
```

### 4. Real-Time Directory Watcher (`baizo watch`)
```powershell
# Watch a directory and auto-sync file additions, edits, and deletions to the index in real-time
baizo watch "D:\projects\agent" --content
```

### 5. Semantic Vector Search (`baizo semantic`)
```powershell
# Search indexed documents by conceptual meaning using vector cosine similarity
baizo semantic "file system monitoring daemon"
baizo semantic "quarterly revenue forecast" --limit 5
```

### 6. Conversational AI Agent (`baizo ask` & `baizo chat`)
```powershell
# Ask Baizo in natural language
baizo ask "find all python scripts in agent project"
baizo ask "find my d disk drive downloads folder"
baizo ask "what drives are available on my system?"
baizo ask "find requirements.txt in D:\projects\VOLT and read it"

# Start interactive chat session
baizo chat
```

---

## 🧪 Running Tests

```powershell
py -m pytest
```

---

## 🔒 Safety & Privacy

Baizo is strictly **local-first** and **read-only**:
- Does not modify, overwrite, delete, or rename files.
- Does not upload your files or metadata to third-party cloud services.
- Explorer actions (`--open`) only reveal items in your local desktop File Explorer.
