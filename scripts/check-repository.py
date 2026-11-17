#!/usr/bin/env python3
"""Conservative filename checks across the complete Git history. Not a PII detector."""

import re
import subprocess
import sys

names = set(subprocess.check_output(["git", "ls-files"], text=True).splitlines())
names.update(
    subprocess.check_output(
        ["git", "log", "--all", "--format=", "--name-only"], text=True
    ).splitlines()
)
blocked = []
for name in names:
    if not name:
        continue
    if re.search(
        r"(^|/)(\.env($|\.(?!example$))|id_rsa|id_ed25519|credentials|secrets)(/|$)|\.(dump|age|pem|key|sqlite|sqlite3|vcf)$|(^|/)(node_modules|backups|exports|data)/",
        name,
        re.I,
    ):
        blocked.append(name)
if blocked:
    print("Forbidden data/secret paths:")
    print("\n".join(sorted(blocked)))
    sys.exit(1)
print(
    f"Checked {len(names)} unique historical/current paths; no forbidden data filenames. Manual PII review still required."
)
