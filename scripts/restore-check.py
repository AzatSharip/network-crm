#!/usr/bin/env python3
"""Verify encrypted dump by restoring to a new isolated database; never overwrite live DB."""

import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

backup = Path(sys.argv[1]).resolve()
identity = Path(os.environ["AGE_IDENTITY"]).resolve()
repo = Path(__file__).resolve().parents[1]
env_file = Path(os.environ["ENV_FILE"]).resolve()
if backup.is_relative_to(repo) or identity.is_relative_to(repo):
    raise SystemExit("Backup/key must be outside source checkout")
name = "crm_restore_" + uuid.uuid4().hex[:16]
probe = subprocess.run(["docker", "compose", "version"], capture_output=True)
compose = (["docker", "compose"] if probe.returncode == 0 else ["docker-compose"]) + [
    "--env-file",
    str(env_file),
    "-f",
    str(repo / "compose.yaml"),
    "exec",
    "-T",
    "db",
]
subprocess.run(compose + ["createdb", "-U", "crm_migrator", name], check=True)
try:
    decrypt = subprocess.Popen(
        ["age", "-d", "-i", str(identity), str(backup)], stdout=subprocess.PIPE
    )
    restore = subprocess.run(
        compose + ["pg_restore", "-U", "crm_migrator", "-d", name, "--no-owner", "--exit-on-error"],
        stdin=decrypt.stdout,
        capture_output=True,
    )
    decrypt.stdout.close()
    if decrypt.wait() or restore.returncode:
        raise SystemExit("Restore failed; live database unchanged")
    sql = "SELECT json_build_object('persons',(SELECT count(*) FROM persons),'workspaces',(SELECT count(*) FROM workspaces),'suggestions',(SELECT count(*) FROM ai_suggestions),'migration',(SELECT version_num FROM alembic_version));"
    result = subprocess.run(
        compose + ["psql", "-U", "crm_migrator", "-d", name, "-Atc", sql],
        check=True,
        capture_output=True,
        text=True,
    )
    counts = json.loads(result.stdout)
    if counts["migration"] != "0001":
        raise SystemExit("Unexpected schema revision")
    receipt = backup.with_suffix(backup.suffix + ".verified.json")
    receipt.write_text(
        json.dumps(
            {
                "restored": True,
                "counts": counts,
                "sha256": hashlib.file_digest(backup.open("rb"), "sha256").hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    receipt.chmod(0o600)
    print(
        json.dumps(
            {
                "restored": True,
                "counts": counts,
                "sha256": hashlib.file_digest(backup.open("rb"), "sha256").hexdigest(),
            }
        )
    )
finally:
    subprocess.run(compose + ["dropdb", "-U", "crm_migrator", "--if-exists", name], check=True)
