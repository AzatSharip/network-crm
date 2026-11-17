#!/usr/bin/env python3
"""Run browser checks with synthetic credentials loaded outside the source tree."""

import os
import subprocess
import sys
from pathlib import Path

env = dict(os.environ)
if "CRM_E2E_PASSWORD" not in env:
    path = Path.home() / "Library/Application Support/Network CRM/demo.env"
    env.update(dict(line.split("=", 1) for line in path.read_text().splitlines() if line))
raise SystemExit(
    subprocess.run(
        ["npm", "test", *sys.argv[1:]],
        cwd=Path(__file__).resolve().parents[1] / "frontend",
        env=env,
    ).returncode
)
