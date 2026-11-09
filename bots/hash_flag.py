"""Make a challenge's flag.sha256 without the flag ever touching the repo.

  python bots/hash_flag.py challenges/2026-11-30-my-challenge

It prompts for the flag (input hidden) and writes flag.sha256 in that folder.
"""

import getpass
import hashlib
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("usage: python bots/hash_flag.py challenges/<slug>")
folder = Path(sys.argv[1])
if not folder.is_dir():
    sys.exit(f"{folder} is not a folder")

flag = getpass.getpass("Flag (input hidden): ").strip()
again = getpass.getpass("Again: ").strip()
if flag != again:
    sys.exit("Flags didn't match; nothing written.")
if len(flag) < 12:
    print("Warning: short flags can be guessed from the public hash. Add a random suffix like _4e9b.")

(folder / "flag.sha256").write_text(hashlib.sha256(flag.encode()).hexdigest() + "\n")
print(f"Wrote {folder / 'flag.sha256'}")
