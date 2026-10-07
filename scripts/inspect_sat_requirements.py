from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/SAT.mdb")
    print(f"SAT path: {path}")
    print(f"exists: {path.exists()}")
    print(f"mdb-export: {shutil.which('mdb-export') or 'NOT FOUND'}")
    if not path.exists():
        return 2
    if shutil.which("mdb-export") is None:
        print("Install mdbtools or provide a neutral JSONL export for F0.2-B.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
