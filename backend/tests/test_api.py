import uuid
from datetime import timedelta

import pytest
from app.db import engine
from app.main import app
from app.models import Invitation, now
from app.security import ORIGIN
from conftest import PASSWORD, admin, create
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session


def base(s):
    return f"/api/v1/workspaces/{s['family']}"


def test_minimal_create_edit_and_idempotency(setup):
    c = setup["clients"][0]
    url = base(setup) + "/people"
    key = str(uuid.uuid4())
    r = c.post(url, json={"display_name": "Тест"}, headers={"Idempotency-Key": key})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["version"] == 1
    assert (
        c.post(url, json={"display_name": "Тест"}, headers={"Idempotency-Key": key}).json()["id"]
        == p["id"]
    )
    assert (
        c.post(url, json={"display_name": "Другой"}, headers={"Idempotency-Key": key}).status_code
        == 409
    )
    assert (
        c.patch(
            url + "/" + p["id"], json={"display_name": "Обновлён", "expected_version": 1}
        ).json()["version"]
        == 2
    )
    assert (
        c.patch(
            url + "/" + p["id"], json={"display_name": "Старый", "expected_version": 1}
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "route", ["people", "tags", "organizations", "suggestions", "sources", "members", "audit"]
)
def test_workspace_isolation(setup, route):
    c = setup["clients"][1]
    assert c.get(f"/api/v1/workspaces/{setup['personal'][0]}/{route}").status_code == 404


def test_bola_and_rls(setup):
    owner, editor, _ = setup["clients"]
    private = create(owner, setup["personal"][0]).json()
    assert editor.get(base(setup) + "/people/" + private["id"]).status_code == 404
    assert editor.get(base(setup) + "/graph", params={"root": private["id"]}).status_code == 404
    assert (
        editor.post(
            base(setup) + "/relationships",
            json={
                "from_person_id": private["id"],
                "to_person_id": str(uuid.uuid4()),
                "type": "Знакомые",
            },
        ).status_code
        == 404
    )
    with Session(engine) as db:
        assert db.scalar(text("SELECT count(*) FROM persons")) == 0
        db.execute(
            text("SELECT set_config('app.workspace_id',:w,true)"), {"w": str(setup["personal"][1])}
        )
        assert db.scalar(text("SELECT count(*) FROM persons")) == 0
        assert not db.scalar(
            text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")
        )


@pytest.mark.parametrize(
    "endpoint,payload",
    [
        ("people", {"display_name": "Заблокирован"}),
        ("invitations", {"email": "other@example.com"}),
        ("sources", {"name": "Тест"}),
        ("agent-tokens", {"name": "Тест"}),
    ],
)
def test_viewer_cannot_write(setup, endpoint, payload):
    assert (
        setup["clients"][2]
        .post(base(setup) + "/" + endpoint, json=payload, headers={"Idempotency-Key": "test"})
        .status_code
        == 403
    )


def test_editor_cannot_invite(setup):
    assert (
        setup["clients"][1]
        .post(base(setup) + "/invitations", json={"email": "other@example.com"})
        .status_code
        == 403
    )


def test_contacts_duplicates_and_explicit_override(setup):
    c = setup["clients"][0]
    wid = setup["family"]
    contact = {"platform": "phone", "kind": "phone", "value": "+7 (000) 000-00-01"}
    first = create(c, wid, contacts=[contact])
    assert first.status_code == 201, first.text
    dup = create(c, wid, display_name="Иное имя", contacts=[{**contact, "value": "80000000001"}])
    assert dup.status_code == 409, dup.text
    assert dup.json()["detail"]["code"] == "duplicates"
    override = c.post(
        base(setup) + "/people?allow_duplicate=true",
        json={"display_name": "Иное имя", "contacts": [contact]},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert override.status_code == 201
    # Name alone never triggers automatic merging.
    assert create(c, wid).status_code == 201
    assert create(c, wid).status_code == 201


@pytest.mark.parametrize(
    "contact",
    [
        {"platform": "telegram", "kind": "numeric_id", "value": "@username"},
        {"platform": "website", "kind": "url", "value": "javascript:alert(1)"},
        {"platform": "website", "kind": "url", "value": "https://user:pass@example.com"},
        {"platform": "email", "kind": "email", "value": "invalid"},
    ],
)
def test_validation(setup, contact):
    assert create(setup["clients"][0], setup["family"], contacts=[contact]).status_code == 422


def test_search_multifield_and_filters(setup):
    c = setup["clients"][0]
    wid = setup["family"]
    p = create(
        c,
        wid,
        display_name="Александр Тестов",
        city="Уфа",
        country="США",
        profession="Стоматолог",
        notes="Обсуждали инвестиции",
        competencies="Логистика",
        tags=["Медицина"],
        organizations=[{"name": "Синтетическая клиника", "title": "Руководитель"}],
        contacts=[{"platform": "telegram", "kind": "username", "value": "@synthetic_dentist"}],
        connections=[{"user_id": str(setup["users"][0]), "priority": "A", "knows": True}],
    ).json()
    for q in [
        "Уфа стоматология",
        "сша",
        "synthetic_den",
        "Руководитель",
        "клиника",
        "АЛЕКСАНДР",
        "Медицина инвестиции",
        "Алексанр",
    ]:
        r = c.get(base(setup) + "/people", params={"q": q})
        assert r.status_code == 200, r.text
        assert p["id"] in [x["id"] for x in r.json()["items"]], q
    assert c.get(base(setup) + "/people?priority=B").json()["total"] == 0
    assert c.get(base(setup) + "/people?priority=A&tag=Медицина").json()["total"] == 1
    assert c.get(base(setup) + "/people", params={"q": "' OR 1=1 --"}).json()["total"] == 0


def test_graph_direction_path_and_limits(setup):
    c = setup["clients"][0]
    wid = setup["family"]
    ids = [create(c, wid, display_name=f"Узел {i}").json()["id"] for i in range(4)]
    for a, b in zip(ids, ids[1:], strict=False):
        r = c.post(
            base(setup) + "/relationships",
            json={"from_person_id": a, "to_person_id": b, "type": "Знакомые", "directed": True},
        )
        assert r.status_code == 201, r.text
    g = c.get(base(setup) + "/graph", params={"root": ids[0], "target": ids[-1]}).json()
    assert g["path"] == ids
    assert (
        c.get(base(setup) + "/graph", params={"root": ids[-1], "target": ids[0]}).json()["path"]
        == []
    )
    bounded = c.get(base(setup) + "/graph", params={"root": ids[0], "depth": 2, "limit": 2}).json()
    assert len(bounded["nodes"]) == 2 and bounded["truncated"]


def test_invitation_accept_once_and_expiry(setup):
    c = setup["clients"][0]
    r = c.post(base(setup) + "/invitations", json={"email": "new@example.com", "role": "viewer"})
    assert r.status_code == 201
    token = r.json()["token"]
    anon = TestClient(app, headers={"Origin": ORIGIN})
    body = {"token": token, "name": "Новый тестовый", "password": PASSWORD}
    assert anon.post("/api/v1/invitations/accept", json=body).status_code == 200
    assert anon.post("/api/v1/invitations/accept", json=body).status_code == 400
    assert (
        c.post(
            f"/api/v1/workspaces/{setup['personal'][0]}/invitations",
            json={"email": "no@example.com"},
        ).status_code
        == 403
    )
    inv = c.post(base(setup) + "/invitations", json={"email": "expired@example.com"}).json()
    with Session(admin) as db:
        row = db.get(Invitation, uuid.UUID(inv["id"]))
        row.expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert (
        anon.post("/api/v1/invitations/accept", json={**body, "token": inv["token"]}).status_code
        == 400
    )


def test_csrf_logout_and_public_endpoints(setup):
    c = setup["clients"][0]
    assert (
        c.post(
            base(setup) + "/sources", json={"name": "Bad"}, headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        c.post(
            base(setup) + "/sources",
            json={"name": "Bad"},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert TestClient(app).get("/api/v1/openapi.json").status_code == 401
    assert c.get("/docs").status_code == 404
    assert c.get("/api/v1/openapi.json").status_code == 200
    assert c.post("/api/v1/auth/logout").status_code == 200
    assert c.get("/api/v1/me").status_code == 401


def test_login_rate_limit():
    c = TestClient(app, headers={"Origin": ORIGIN})
    for _ in range(12):
        assert (
            c.post(
                "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "incorrect"}
            ).status_code
            == 401
        )
    assert (
        c.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "incorrect"}
        ).status_code
        == 429
    )


def test_agent_scope_review_and_conflict(setup):
    c = setup["clients"][0]
    b = base(setup)
    raw = c.post(b + "/agent-tokens", json={"name": "Импортёр"}).json()
    agent = TestClient(app, headers={"Authorization": "Bearer " + raw["token"]})
    assert agent.get(b + "/people").status_code == 403
    assert (
        agent.post(
            f"/api/v1/workspaces/{setup['personal'][0]}/sources", json={"name": "Bad"}
        ).status_code
        == 404
    )
    source = agent.post(b + "/sources", json={"name": "Синтетический импорт"}).json()
    data = {
        "operation": "create_person",
        "source_id": source["id"],
        "payload": {"display_name": "AI тест"},
        "confidence": 85,
        "job_key": "job-1",
        "record_key": "row-1",
    }
    s = agent.post(b + "/suggestions", json=data)
    assert s.status_code == 201, s.text
    sid = s.json()["id"]
    assert agent.post(b + "/suggestions", json=data).json()["id"] == sid
    assert (
        agent.post(
            b + "/suggestions", json={**data, "payload": {"display_name": "Changed"}}
        ).status_code
        == 409
    )
    assert agent.post(b + "/suggestions/" + sid + "/approve").status_code == 403
    assert c.get(b + "/people").json()["total"] == 0
    assert c.post(b + "/suggestions/" + sid + "/approve").json()["status"] == "applied"
    assert c.post(b + "/suggestions/" + sid + "/approve").json()["status"] == "applied"
    p = c.get(b + "/people").json()["items"][0]
    update = {
        **data,
        "operation": "update_person",
        "target_id": p["id"],
        "expected_version": 1,
        "record_key": "row-2",
        "payload": {"display_name": "AI обновил"},
    }
    sid2 = agent.post(b + "/suggestions", json=update).json()["id"]
    assert (
        c.patch(
            b + "/people/" + p["id"],
            json={"display_name": "Человек обновил", "expected_version": 1},
        ).status_code
        == 200
    )
    assert c.post(b + "/suggestions/" + sid2 + "/approve").status_code == 409
    assert c.get(b + "/suggestions").json()[0]["status"] == "pending"
    assert c.delete(b + "/agent-tokens/" + raw["id"]).status_code == 200
    assert agent.post(b + "/sources", json={"name": "Revoked"}).status_code == 401


def test_body_limit_and_foreign_member(setup):
    c = setup["clients"][0]
    assert c.post(base(setup) + "/people", content="x" * 262145).status_code == 413
    assert (
        create(
            c, setup["personal"][0], connections=[{"user_id": str(setup["users"][1])}]
        ).status_code
        == 422
    )
    with Session(admin) as db:
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "INSERT INTO workspace_members (workspace_id,user_id,role) VALUES (:w,:u,'viewer')"
                ),
                {"w": setup["personal"][0], "u": setup["users"][1]},
            )
            db.commit()


def test_identifier_search_does_not_match_common_domain(setup):
    c = setup["clients"][0]
    for i in range(3):
        assert (
            create(
                c,
                setup["family"],
                display_name=f"Персона {i}",
                contacts=[
                    {"platform": "email", "kind": "email", "value": f"synthetic{i}@example.com"}
                ],
            ).status_code
            == 201
        )
    r = c.get(base(setup) + "/people", params={"q": "synthetic1@example.com"}).json()
    assert r["total"] == 1
    assert r["items"][0]["display_name"] == "Персона 1"


def test_ai_preview_includes_cleared_fields(setup):
    c = setup["clients"][0]
    b = base(setup)
    p = create(
        c,
        setup["family"],
        notes="Сведения, которые нельзя скрытно удалить",
        contacts=[{"platform": "email", "kind": "email", "value": "preview@example.com"}],
    ).json()
    src = c.post(b + "/sources", json={"name": "Preview fixture"}).json()
    suggestion = {
        "operation": "update_person",
        "target_id": p["id"],
        "expected_version": 1,
        "source_id": src["id"],
        "payload": {"display_name": "Изменение"},
        "confidence": 70,
        "job_key": "preview",
        "record_key": "1",
    }
    assert c.post(b + "/suggestions", json=suggestion).status_code == 201
    preview = c.get(b + "/suggestions").json()[0]
    assert preview["before"]["notes"] and preview["payload"]["notes"] == ""
    assert preview["before"]["contacts"] and preview["payload"]["contacts"] == []
    assert c.post(b + "/suggestions", json=suggestion).json()["id"] == preview["id"]


def test_phone_duplicates_across_platforms(setup):
    c = setup["clients"][0]
    assert (
        create(
            c,
            setup["family"],
            contacts=[{"platform": "phone", "kind": "phone", "value": "+70000000001"}],
        ).status_code
        == 201
    )
    assert (
        create(
            c,
            setup["family"],
            contacts=[{"platform": "whatsapp", "kind": "phone", "value": "+70000000001"}],
        ).status_code
        == 409
    )


def test_secure_cookie_configuration(setup):
    import os
    import subprocess
    import sys

    script = """
from fastapi.testclient import TestClient
from app.main import app
from app.security import ORIGIN
client=TestClient(app,base_url=ORIGIN,headers={'Origin':ORIGIN})
r=client.post('/api/v1/auth/login',json={'email':'user0@example.com','password':'Synthetic-Only-Password-42!'})
assert r.status_code==200
cookies=r.headers.get_list('set-cookie')
assert any('__Host-crm_session=' in c and 'Secure' in c and 'HttpOnly' in c and 'SameSite=strict' in c and 'Path=/' in c for c in cookies)
assert client.get('/api/v1/me').status_code==200
client.headers['X-CSRF-Token']=client.cookies['crm_csrf']
assert client.post('/api/v1/auth/logout').status_code==200
assert client.get('/api/v1/me').status_code==401
"""
    subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "APP_ORIGIN": "https://crm.example.invalid"},
        check=True,
        capture_output=True,
    )


def test_password_change_revokes_sessions(setup):
    c = setup["clients"][0]
    other = TestClient(app, headers={"Origin": ORIGIN})
    assert (
        other.post(
            "/api/v1/auth/login", json={"email": "user0@example.com", "password": PASSWORD}
        ).status_code
        == 200
    )
    new = "Synthetic-new-password-123!"
    assert (
        c.post(
            "/api/v1/auth/password", json={"current_password": PASSWORD, "new_password": new}
        ).status_code
        == 200
    )
    assert c.get("/api/v1/me").status_code == 401
    assert other.get("/api/v1/me").status_code == 401
    assert (
        other.post(
            "/api/v1/auth/login", json={"email": "user0@example.com", "password": PASSWORD}
        ).status_code
        == 401
    )
    assert (
        other.post(
            "/api/v1/auth/login", json={"email": "user0@example.com", "password": new}
        ).status_code
        == 200
    )


def test_commit_failure_cannot_return_success(setup, monkeypatch):
    from app.models import Source
    from sqlalchemy.exc import IntegrityError

    def failed_commit(self):
        raise IntegrityError("synthetic commit failure", {}, Exception("synthetic"))

    monkeypatch.setattr(Session, "commit", failed_commit)
    response = setup["clients"][0].post(base(setup) + "/sources", json={"name": "Must rollback"})
    assert response.status_code == 409
    with Session(admin) as db:
        assert db.scalar(select(Source.id).where(Source.name == "Must rollback")) is None
