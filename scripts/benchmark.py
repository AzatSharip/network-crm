#!/usr/bin/env python3
"""10k synthetic search benchmark in a fresh disposable PostgreSQL database."""

import json
import os
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

if "--worker" not in sys.argv:
    base = make_url(os.environ["MIGRATION_DATABASE_URL"])
    name = "crm_bench_" + uuid.uuid4().hex[:12]
    engine = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    env = {
        **os.environ,
        "MIGRATION_DATABASE_URL": base.set(database=name).render_as_string(hide_password=False),
        "DATABASE_URL": make_url(os.environ["DATABASE_URL"])
        .set(database=name)
        .render_as_string(hide_password=False),
    }
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
            env=env,
            check=True,
        )
        subprocess.run([sys.executable, __file__, "--worker"], env=env, check=True)
    finally:
        with engine.connect() as c:
            c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    raise SystemExit()

from app.main import app
from app.models import Member, Person, User, Workspace
from app.security import ORIGIN, hasher
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

admin = create_engine(os.environ["MIGRATION_DATABASE_URL"])
password = "Benchmark-synthetic-password-123"
with Session(admin) as db:
    u = User(
        email="benchmark@example.com",
        name="Синтетический тест",
        password_hash=hasher.hash(password),
    )
    db.add(u)
    db.flush()
    w = Workspace(name="Benchmark", kind="personal", owner_id=u.id)
    db.add(w)
    db.flush()
    db.add(Member(workspace_id=w.id, user_id=u.id, role="admin"))
    wid = str(w.id)
    for i in range(10000):
        city = ["Уфа", "Казань", "Москва", "Алматы"][i % 4]
        profession = ["Стоматолог", "Разработчик", "Юрист", "Логист"][i % 4]
        name = f"Синтетический Контакт {i:05}"
        # Fixture-only bulk load, not a production write/import path.
        db.add(
            Person(
                workspace_id=w.id,
                display_name=name,
                city=city,
                profession=profession,
                updated_by=u.id,
                search_text=f"{name} {city} {profession} компания{i % 70} synthetic{i}@example.com".casefold(),
            )
        )
    db.commit()
with admin.begin() as c:
    c.execute(text("ANALYZE persons"))
client = TestClient(app, headers={"Origin": ORIGIN})
assert (
    client.post(
        "/api/v1/auth/login", json={"email": "benchmark@example.com", "password": password}
    ).status_code
    == 200
)
results = []
for q in [
    "Синтетический Контакт 04731",
    "Уфа стоматология",
    "synthetic713@example.com",
    "компания24",
    "Синтетичский",
    "ZZZ_NOT_FOUND",
]:
    durations = []
    for _ in range(6):
        start = time.perf_counter()
        r = client.get(f"/api/v1/workspaces/{wid}/people", params={"q": q})
        assert r.status_code == 200, r.text
        durations.append((time.perf_counter() - start) * 1000)
    results.append(
        {
            "query": q,
            "matches": r.json()["total"],
            "median_ms": round(statistics.median(durations[1:]), 2),
            "max_ms": round(max(durations[1:]), 2),
        }
    )
plans = {}
with admin.connect() as c:
    for name, sql in [
        (
            "fts",
            "SELECT id FROM persons WHERE workspace_id=:w AND search_vector @@ plainto_tsquery('russian','Уфа стоматология')",
        ),
        (
            "trigram",
            "SELECT id FROM persons WHERE workspace_id=:w AND search_text ILIKE '%synthetic713%'",
        ),
    ]:
        plans[name] = "\n".join(
            c.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + sql), {"w": wid}).scalars()
        )
version = admin.connect().execute(text("SHOW server_version")).scalar()
report = {
    "database": version,
    "records": 10000,
    "query_runs": 6,
    "warmup_excluded": True,
    "http_in_process": True,
    "results": results,
    "plans": plans,
}
Path("docs/search-benchmark.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps({k: v for k, v in report.items() if k != "plans"}, ensure_ascii=False))
