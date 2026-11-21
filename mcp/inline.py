#!/usr/bin/env python3
"""Guard: the MCP front runs from the app's source files, never inlined into the compose file.

Usage: python3 mcp/inline.py [--check]
The front used to be inlined into the front service's `command` as one start argument; at about 104 KB it came
close to Linux's 128 KiB limit for a single argument (past it the container crash-loops with "argument list too
long"). It now runs as `python /app/mcp/run.py` from the read-only source copy (wizard.md `runtime.package: source`).
This script (kept under its old name, which CI calls) exits 1 when the compose file inlines the front again or the
front service lost its source mount.
"""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
text = (root / "runtipi" / "docker-compose.yml").read_text()
front = text.split("\n  notifications:\n", 1)[-1].split("\n  notifications-engine:\n", 1)[0]
problems = []
if "BEGIN MCP FRONT" in text or "\n    - -c\n" in front:
    problems.append("the front is inlined into the compose command again; run it from /app/mcp/run.py")
if "    command:\n    - python\n    - /app/mcp/run.py\n" not in front:
    problems.append("the front service must run `python /app/mcp/run.py`")
if "    - ${APP_SOURCE_DIR}:/app:ro\n" not in front:
    problems.append("the front service must mount ${APP_SOURCE_DIR}:/app:ro")
if "  package: source\n" not in (root / "wizard.md").read_text():
    problems.append("wizard.md needs runtime.package: source")
if len(text.encode()) > 32 * 1024:
    problems.append("runtipi/docker-compose.yml is over 32 KB; keep code out of it")
for p in problems:
    print("inline check:", p, file=sys.stderr)
sys.exit(1 if problems else 0)
