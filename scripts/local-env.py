#!/usr/bin/env python3
"""Run a command with local DB URLs, without exposing secrets in arguments/output."""

import os
import sys
from pathlib import Path

config = Path.home() / "Library/Application Support/Network CRM/local.env"
values = dict(
    line.split("=", 1)
    for line in config.read_text().splitlines()
    if line and not line.startswith("#")
)
name = os.environ.get("CRM_DB_NAME", "network_crm")
env = {
    **os.environ,
    "DATABASE_URL": f"postgresql+psycopg://crm_app:{values['DB_APP_PASSWORD']}@127.0.0.1:18432/{name}",
    "MIGRATION_DATABASE_URL": f"postgresql+psycopg://crm_migrator:{values['DB_ADMIN_PASSWORD']}@127.0.0.1:18432/{name}",
    "APP_ORIGIN": values["APP_ORIGIN"],
    "PYTHONPATH": "backend",
}
os.execvpe(sys.argv[1], sys.argv[1:], env)
