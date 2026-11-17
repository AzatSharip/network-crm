#!/usr/bin/env python3
"""Explicitly seed an EMPTY local database with fictional records; password outside Git."""

import os
import secrets
from pathlib import Path

from app.db import engine
from app.models import Member, Source, Suggestion, User, Workspace
from app.schemas import PersonIn, RelationshipIn
from app.security import Context, hasher
from app.services import save_person, save_relationship
from sqlalchemy import select
from sqlalchemy.orm import Session

if os.environ.get("CRM_SEED_SYNTHETIC") != "yes":
    raise SystemExit("Set CRM_SEED_SYNTHETIC=yes to confirm synthetic-only initialization")
password = secrets.token_urlsafe(24)
with Session(engine) as db:
    if db.scalar(select(User.id).limit(1)):
        raise SystemExit("Refusing: database already contains users")
    u = User(email="demo@example.com", name="Демо участник", password_hash=hasher.hash(password))
    db.add(u)
    db.flush()
    spaces = []
    for kind, name in [("personal", "Личное"), ("family", "Семья")]:
        w = Workspace(kind=kind, name=name, owner_id=u.id)
        db.add(w)
        db.flush()
        db.add(Member(workspace_id=w.id, user_id=u.id, role="admin"))
        spaces.append(w)
    db.flush()
    from sqlalchemy import text

    db.execute(text("SELECT set_config('app.workspace_id', :w, true)"), {"w": str(spaces[1].id)})
    ctx = Context(db, u, spaces[1].id, "admin", False)
    fixtures = [
        ("Александр Тестов", "Уфа", "Россия", "Стоматолог", ["Медицина"], "Демо Клиника"),
        (
            "Мария Примерова",
            "Алматы",
            "Казахстан",
            "Продуктовый дизайнер",
            ["Дизайн", "IT"],
            "Демо Студия",
        ),
        (
            "Дмитрий Образцов",
            "Казань",
            "Россия",
            "Предприниматель",
            ["Бизнес", "Логистика"],
            "Демо Логистика",
        ),
        ("Анна Учебная", "Бостон", "США", "Исследователь", ["Наука", "США"], "Демо Лаборатория"),
        ("Михаил Макетов", "Уфа", "Россия", "Юрист", ["Право", "Недвижимость"], "Демо Право"),
        ("Елена Демонстрационная", "Москва", "Россия", "Разработчик", ["IT"], "Демо Технологии"),
    ]
    ids = []
    for i, (name, city, country, profession, tags, company) in enumerate(fixtures):
        result = save_person(
            ctx,
            PersonIn(
                display_name=name,
                city=city,
                country=country,
                profession=profession,
                tags=tags,
                organizations=[{"name": company, "title": profession}],
                contacts=[
                    {"platform": "email", "kind": "email", "value": f"person{i}@example.com"}
                ],
                notes="Полностью вымышленные сведения. Демонстрационный контакт.",
                connections=[
                    {
                        "user_id": u.id,
                        "knows": True,
                        "priority": "A" if i == 0 else "B",
                        "is_primary": True,
                    }
                ],
            ),
        )
        ids.append(result["id"])
    for a, b in zip(ids, ids[1:], strict=False):
        save_relationship(ctx, RelationshipIn(from_person_id=a, to_person_id=b, type="Знакомые"))
    source = Source(
        workspace_id=ctx.workspace_id, name="Синтетический пример", reference="synthetic://demo"
    )
    db.add(source)
    db.flush()
    db.add(
        Suggestion(
            workspace_id=ctx.workspace_id,
            operation="create_person",
            source_id=source.id,
            payload={
                "display_name": "София Учебная",
                "city": "Уфа",
                "profession": "Архитектор",
                "tags": ["Архитектура"],
            },
            confidence=91,
            job_key="demo",
            record_key="1",
            created_by=u.id,
        )
    )
    db.commit()
file = Path.home() / "Library/Application Support/Network CRM/demo.env"
file.parent.mkdir(parents=True, exist_ok=True)
file.write_text("CRM_E2E_EMAIL=demo@example.com\nCRM_E2E_PASSWORD=" + password + "\n")
file.chmod(0o600)
print("Synthetic demo initialized; credentials stored outside repository in Network CRM/demo.env")
