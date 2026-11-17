#!/usr/bin/env python3
"""Create a fresh disposable PostgreSQL database, migrate, test, remove only it."""

import os
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

base = make_url(os.environ["MIGRATION_DATABASE_URL"])
name = "crm_test_" + uuid.uuid4().hex[:16]
admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
with admin.connect() as c:
    c.execute(text(f'CREATE DATABASE "{name}"'))
env = {
    **os.environ,
    "MIGRATION_DATABASE_URL": base.set(database=name).render_as_string(hide_password=False),
    "DATABASE_URL": make_url(os.environ["DATABASE_URL"])
    .set(database=name)
    .render_as_string(hide_password=False),
    "CRM_TEST_DATABASE": name,
}
try:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        env=env,
        check=True,
    )
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", *sys.argv[1:]], env=env)
    raise SystemExit(result.returncode)
finally:
    with admin.connect() as c:
        c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
