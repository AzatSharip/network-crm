#!/usr/bin/env python3
"""Dry run by default. Delete only older restore-verified CRM backups after explicit --apply."""

import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("directory", type=Path)
p.add_argument("--keep", type=int, default=14)
p.add_argument("--apply", action="store_true")
args = p.parse_args()
if args.keep < 3:
    raise SystemExit("Keep at least three verified snapshots")
verified = []
for f in args.directory.resolve().glob("network-crm-*.dump.age"):
    receipt = f.with_suffix(f.suffix + ".verified.json")
    if receipt.is_file():
        metadata = json.loads(receipt.read_text())
        with f.open("rb") as stream:
            same = metadata.get("sha256") == hashlib.file_digest(stream, "sha256").hexdigest()
        if metadata.get("restored") is True and same:
            verified.append(f)
old = sorted(verified, key=lambda f: f.name, reverse=True)[args.keep :]
for f in old:
    print(("DELETE " if args.apply else "WOULD DELETE ") + f.name)
    if args.apply:
        f.unlink()
        f.with_suffix(f.suffix + ".verified.json").unlink()
