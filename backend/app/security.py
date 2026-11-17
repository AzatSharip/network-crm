import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .db import engine, get_db
from .models import AgentToken, LoginAttempt, Member, SessionToken, User, Workspace, now

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
ORIGIN = os.environ.get("APP_ORIGIN", "http://localhost:8080").rstrip("/")
SECURE = ORIGIN.startswith("https://")
COOKIE = "__Host-crm_session" if SECURE else "crm_session"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def verify(password, stored):
    try:
        return hasher.verify(stored, password)
    except VerificationError:
        return False


def fail(code=404, detail="Не найдено"):
    raise HTTPException(code, detail)


@dataclass
class Principal:
    user: User
    agent_workspace: UUID | None = None


def principal(request: Request, db: Session = Depends(get_db, scope="function")) -> Principal:
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        # Tokens are separately constrained to a workspace. No contact data read is allowed.
        raw = authorization[7:]
        token = db.scalar(
            select(AgentToken).where(
                AgentToken.token_hash == digest(raw),
                AgentToken.revoked.is_(False),
                AgentToken.expires_at > now(),
            )
        )
        if not token:
            fail(401, "Требуется вход")
        user = db.get(User, token.user_id)
        if not user or not user.active:
            fail(401, "Требуется вход")
        allowed = request.method == "POST" and request.url.path.endswith(
            ("/suggestions", "/sources")
        )
        if not allowed:
            fail(403, "Токен разрешает только создание источников и предложений")
        return Principal(user, token.workspace_id)
    token = db.get(SessionToken, digest(request.cookies.get(COOKIE, "")))
    if not token or token.expires_at <= now():
        fail(401, "Требуется вход")
    user = db.get(User, token.user_id)
    if not user or not user.active:
        fail(401, "Требуется вход")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(
            token.csrf_hash, digest(request.headers.get("x-csrf-token", ""))
        ):
            fail(403, "Некорректный CSRF-токен")
    return Principal(user)


@dataclass
class Context:
    db: Session
    user: User
    workspace_id: UUID
    role: str
    agent: bool


def context(
    workspace_id: UUID,
    who: Principal = Depends(principal),
    db: Session = Depends(get_db, scope="function"),
) -> Context:
    if who.agent_workspace and who.agent_workspace != workspace_id:
        fail()
    member = db.get(Member, (workspace_id, who.user.id))
    workspace = db.get(Workspace, workspace_id)
    if (
        not member
        or not workspace
        or (workspace.kind == "personal" and workspace.owner_id != who.user.id)
    ):
        fail()
    db.execute(text("SELECT set_config('app.workspace_id', :w, true)"), {"w": str(workspace_id)})
    return Context(db, who.user, workspace_id, member.role, who.agent_workspace is not None)


def write(ctx: Context, admin=False):
    if ctx.role not in (("admin",) if admin else ("admin", "editor")):
        fail(403, "Недостаточно прав")


def limit_login(request, email):
    # Database-backed counters work across worker processes. Persist failed attempts too.
    keys = [
        "ip:" + (request.client.host if request.client else "unknown"),
        "account:" + email.lower(),
    ]
    with Session(engine) as db:
        for value in keys:
            key = digest(value)
            db.execute(
                insert(LoginAttempt)
                .values(key=key, count=0, window_start=now())
                .on_conflict_do_nothing()
            )
            row = db.scalar(select(LoginAttempt).where(LoginAttempt.key == key).with_for_update())
            if row.window_start < now() - timedelta(minutes=15):
                row.count, row.window_start = 0, now()
            row.count += 1
            if row.count > (80 if value.startswith("ip:") else 12):
                db.commit()
                fail(429, "Слишком много попыток. Повторите позже.")
        db.commit()
