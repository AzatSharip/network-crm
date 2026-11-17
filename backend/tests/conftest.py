import os
import uuid

import pytest
from app.main import app
from app.models import Member, User, Workspace
from app.security import ORIGIN, hasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

PASSWORD = "Synthetic-Only-Password-42!"
admin = create_engine(os.environ["MIGRATION_DATABASE_URL"])


@pytest.fixture(autouse=True)
def isolated_db():
    name = os.environ.get("CRM_TEST_DATABASE", "")
    assert name.startswith("crm_test_"), "Refusing to reset a non-test database"
    with admin.begin() as c:
        c.execute(text("TRUNCATE users, workspaces, login_attempts CASCADE"))
    yield


@pytest.fixture
def setup():
    with Session(admin) as db:
        users = []
        spaces = []
        for i in range(3):
            u = User(
                email=f"user{i}@example.com",
                name=f"Тестовый участник {i}",
                password_hash=hasher.hash(PASSWORD),
            )
            db.add(u)
            db.flush()
            w = Workspace(name=f"Личное {i}", kind="personal", owner_id=u.id)
            db.add(w)
            db.flush()
            db.add(Member(workspace_id=w.id, user_id=u.id, role="admin"))
            users.append(u.id)
            spaces.append(w.id)
        family = Workspace(name="Тестовая семья", kind="family", owner_id=users[0])
        db.add(family)
        db.flush()
        for uid, role in zip(users, ["admin", "editor", "viewer"], strict=True):
            db.add(Member(workspace_id=family.id, user_id=uid, role=role))
        fid = family.id
        db.commit()
    clients = []
    for i in range(3):
        client = TestClient(app, headers={"Origin": ORIGIN})
        response = client.post(
            "/api/v1/auth/login", json={"email": f"user{i}@example.com", "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        client.headers["X-CSRF-Token"] = client.cookies["crm_csrf"]
        clients.append(client)
    yield {"users": users, "personal": spaces, "family": fid, "clients": clients}
    for c in clients:
        c.close()


def create(client, wid, **values):
    return client.post(
        f"/api/v1/workspaces/{wid}/people",
        json={"display_name": "Синтетический контакт", **values},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
