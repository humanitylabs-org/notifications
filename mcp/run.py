#!/usr/bin/env python3
"""Start the Notifications MCP front from its source files (runtime.package: source).

The App Manager mounts the app's pinned source read-only at /app; the front service runs
`python /app/mcp/run.py`, so its start command stays a few bytes however large the front grows
(Linux refuses a single start argument over 128 KiB). The parts share one namespace and run in
this order, exactly as the old inlined compose command did.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARTS = ("front.py", "tools.py", "minimal_assets.py", "relay.py", "phone.py")


def source():
    return "\n\n".join((HERE / name).read_text() for name in PARTS)


def namespace(name="__main__"):
    return {"__name__": name, "__file__": str(HERE / "front.py"), "__builtins__": __builtins__}


if __name__ == "__main__":
    ns = namespace()
    exec(compile(source() + "\n\nif __name__ == \"__main__\":\n    asyncio.run(main())\n", "notifications-front", "exec"), ns)
