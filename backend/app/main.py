import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    AgentToken,
    Audit,
    Connection,
    Contact,
    Invitation,
    Member,
    Organization,
    Person,
    PersonTag,
    Relationship,
    SessionToken,
    Source,
    Suggestion,
    Tag,
    User,
    Workspace,
    now,
)
from .schemas import (
    AgentIn,
    InviteAccept,
    InviteIn,
    Login,
    PasswordChange,
    PersonIn,
    PersonPatch,
    RelationshipIn,
    SourceIn,
    SuggestionIn,
    WorkspaceIn,
)
from .security import (
    COOKIE,
    DUMMY_HASH,
    ORIGIN,
    SECURE,
    Context,
    Principal,
    context,
    digest,
    fail,
    hasher,
    limit_login,
    principal,
    verify,
    write,
)
from .services import (
    audit,
    locked_key,
    person,
    relationship_json,
    save_person,
    save_relationship,
    serialize,
    serialize_many,
)

app = FastAPI(title="Network CRM", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
PREFIX = "/api/v1"
W = PREFIX + "/workspaces/{workspace_id}"


class SecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        if scope["method"] not in ("GET", "HEAD", "OPTIONS") and not headers.get(
            b"authorization", b""
        ).startswith(b"Bearer "):
            if headers.get(b"origin", b"").decode() != ORIGIN:
                return await JSONResponse({"detail": "Недопустимый Origin"}, 403)(
                    scope, receive, send
                )
        chunks = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            total += len(body)
            if total > 262144:
                return await JSONResponse({"detail": "Запрос слишком большой"}, 413)(
                    scope, receive, send
                )
            chunks.append(body)
            if not message.get("more_body"):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        async def secure_send(message):
            if message["type"] == "http.response.start":
                message["headers"] += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"cache-control", b"no-store"),
                ]
            await send(message)

        await self.app(scope, replay, secure_send)


app.add_middleware(SecurityMiddleware)


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse({"detail": "Конфликт данных. Обновите страницу и повторите."}, 409)


@app.exception_handler(ValidationError)
async def validation_error(request, exc):
    return JSONResponse({"detail": "Некорректные поля предложения"}, 422)


@app.get("/healthz")
def health(db: Session = Depends(get_db, scope="function")):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get(PREFIX + "/openapi.json")
def schema(who: Principal = Depends(principal)):
    return app.openapi()


@app.post(PREFIX + "/auth/login")
def login(
    data: Login,
    request: Request,
    response: Response,
    db: Session = Depends(get_db, scope="function"),
):
    email = str(data.email).lower()
    limit_login(request, email)
    # Serialize session issuance with credential changes until commit. A login that
    # verified the old hash must not create a session after password revocation.
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    valid = verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        fail(401, "Неверные учётные данные")
    session, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    # Invalidate the supplied previous session on login.
    db.execute(
        delete(SessionToken).where(
            SessionToken.token_hash == digest(request.cookies.get(COOKIE, ""))
        )
    )
    db.add(
        SessionToken(
            token_hash=digest(session),
            csrf_hash=digest(csrf),
            user_id=user.id,
            expires_at=now() + timedelta(hours=12),
        )
    )
    response.set_cookie(
        COOKIE, session, max_age=43200, httponly=True, secure=SECURE, samesite="strict", path="/"
    )
    response.set_cookie(
        "crm_csrf", csrf, max_age=43200, httponly=False, secure=SECURE, samesite="strict", path="/"
    )
    return {"id": str(user.id), "name": user.name}


@app.post(PREFIX + "/auth/logout")
def logout(
    request: Request,
    response: Response,
    who: Principal = Depends(principal),
    db: Session = Depends(get_db, scope="function"),
):
    db.execute(
        delete(SessionToken).where(
            SessionToken.token_hash == digest(request.cookies.get(COOKIE, ""))
        )
    )
    response.delete_cookie(COOKIE, path="/", secure=SECURE, httponly=True, samesite="strict")
    response.delete_cookie("crm_csrf", path="/", secure=SECURE, samesite="strict")
    return {"ok": True}


@app.get(PREFIX + "/me")
def me(who: Principal = Depends(principal)):
    return {"id": str(who.user.id), "name": who.user.name, "email": who.user.email}


@app.get(PREFIX + "/workspaces")
def workspaces(
    who: Principal = Depends(principal), db: Session = Depends(get_db, scope="function")
):
    return [
        {"id": str(w.id), "name": w.name, "kind": w.kind, "role": m.role}
        for w, m in db.execute(
            select(Workspace, Member)
            .join(Member, Member.workspace_id == Workspace.id)
            .where(Member.user_id == who.user.id)
        ).all()
        if w.kind != "personal" or w.owner_id == who.user.id
    ]


@app.post(PREFIX + "/workspaces", status_code=201)
def create_workspace(
    data: WorkspaceIn,
    who: Principal = Depends(principal),
    db: Session = Depends(get_db, scope="function"),
):
    w = Workspace(name=data.name, kind="family", owner_id=who.user.id)
    db.add(w)
    db.flush()
    db.add(Member(workspace_id=w.id, user_id=who.user.id, role="admin"))
    return {"id": str(w.id), "name": w.name, "kind": w.kind, "role": "admin"}


@app.get(W + "/members")
def members(ctx: Context = Depends(context)):
    return [
        {"user_id": str(u.id), "name": u.name, "role": m.role}
        for u, m in ctx.db.execute(
            select(User, Member)
            .join(Member, Member.user_id == User.id)
            .where(Member.workspace_id == ctx.workspace_id)
        )
    ]


@app.post(W + "/invitations", status_code=201)
def invite(data: InviteIn, ctx: Context = Depends(context)):
    write(ctx, True)
    w = ctx.db.get(Workspace, ctx.workspace_id)
    if w.kind != "family":
        fail(403, "Приглашения доступны только в Family")
    raw = secrets.token_urlsafe(32)
    inv = Invitation(
        workspace_id=w.id,
        email=str(data.email).lower(),
        role=data.role,
        token_hash=digest(raw),
        expires_at=now() + timedelta(days=3),
    )
    ctx.db.add(inv)
    ctx.db.flush()
    audit(ctx, "invitation.created", inv.id)
    return {"id": str(inv.id), "token": raw, "expires_at": inv.expires_at.isoformat()}


@app.post(PREFIX + "/invitations/accept")
def accept(data: InviteAccept, request: Request, db: Session = Depends(get_db, scope="function")):
    limit_login(request, "invite:" + digest(data.token))
    inv = db.scalar(
        select(Invitation).where(Invitation.token_hash == digest(data.token)).with_for_update()
    )
    if not inv or inv.accepted_at or inv.expires_at <= now():
        fail(400, "Приглашение недействительно")
    w = db.get(Workspace, inv.workspace_id)
    if w.kind != "family":
        fail(400, "Приглашение недействительно")
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": inv.email})
    user = db.scalar(select(User).where(User.email == inv.email))
    if user:
        if not user.active or not verify(data.password, user.password_hash):
            fail(401, "Неверные учётные данные")
    else:
        user = User(email=inv.email, name=data.name, password_hash=hasher.hash(data.password))
        db.add(user)
        db.flush()
        personal = Workspace(name="Личное", kind="personal", owner_id=user.id)
        db.add(personal)
        db.flush()
        db.add(Member(workspace_id=personal.id, user_id=user.id, role="admin"))
    if not db.get(Member, (inv.workspace_id, user.id)):
        db.add(Member(workspace_id=inv.workspace_id, user_id=user.id, role=inv.role))
    inv.accepted_at = now()
    return {"ok": True, "email": inv.email}


@app.get(W + "/people")
def people(
    ctx: Context = Depends(context),
    q: str = Query("", max_length=200),
    city: str = "",
    country: str = "",
    profession: str = "",
    tag: str = "",
    priority: str = "",
    known_by: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
):
    db, wid = ctx.db, ctx.workspace_id
    query = select(Person).where(Person.workspace_id == wid)
    for column, value in (
        (Person.city, city),
        (Person.country, country),
        (Person.profession, profession),
    ):
        if value:
            query = query.where(func.lower(column) == value.lower())
    if tag:
        query = query.where(
            Person.id.in_(
                select(PersonTag.person_id)
                .join(Tag, Tag.id == PersonTag.tag_id)
                .where(PersonTag.workspace_id == wid, Tag.name == tag)
            )
        )
    if priority:
        query = query.where(
            Person.id.in_(
                select(Connection.person_id).where(
                    Connection.workspace_id == wid,
                    Connection.user_id == ctx.user.id,
                    Connection.priority == priority,
                )
            )
        )
    if known_by:
        query = query.where(
            Person.id.in_(
                select(Connection.person_id).where(
                    Connection.workspace_id == wid,
                    Connection.user_id == known_by,
                    Connection.knows.is_(True),
                )
            )
        )
    if q.strip():
        db.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = 0.45"))
        for term in q.casefold().split()[:12]:
            pattern = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            # Identifiers and numbers must not fuzzy-match an entire email domain.
            clauses = [Person.search_text.ilike(pattern)]
            identifier = any(c.isdigit() for c in term) or any(c in term for c in "@./:+")
            if not identifier:
                clauses.extend(
                    [
                        Person.search_vector.op("@@")(func.plainto_tsquery("russian", term)),
                        Person.search_vector.op("@@")(func.plainto_tsquery("simple", term)),
                    ]
                )
                if len(term) >= 4:
                    clauses.append(Person.search_text.op("%>")(term))
            query = query.where(or_(*clauses))
        rank = func.ts_rank_cd(Person.search_vector, func.plainto_tsquery("russian", q))
        query = query.order_by(
            (func.lower(Person.display_name) == q.lower()).desc(),
            Person.id.in_(
                select(Contact.person_id).where(
                    Contact.workspace_id == wid,
                    Contact.normalized_value == q.casefold().lstrip("@"),
                )
            ).desc(),
            rank.desc(),
            func.similarity(Person.display_name, q).desc(),
        )
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(
        query.order_by(Person.display_name, Person.id).offset((page - 1) * size).limit(size)
    ).all()
    return {"items": serialize_many(ctx, rows), "total": total, "page": page, "size": size}


@app.get(W + "/people/{person_id}")
def get_person(person_id: UUID, ctx: Context = Depends(context)):
    return serialize(ctx, person(ctx, person_id))


@app.post(W + "/people", status_code=201)
def create_person(
    data: PersonIn, request: Request, allow_duplicate: bool = False, ctx: Context = Depends(context)
):
    write(ctx)
    key = request.headers.get("idempotency-key", "")
    if not key or len(key) > 100:
        fail(422, "Требуется Idempotency-Key длиной 1–100")
    locked_key(ctx, "request:" + key)
    fingerprint = digest(data.model_dump_json() + str(allow_duplicate))
    prior = ctx.db.scalar(
        select(Audit).where(
            Audit.workspace_id == ctx.workspace_id,
            Audit.action == "request.person.create",
            Audit.detail["key"].astext == key,
        )
    )
    if prior:
        if prior.detail["fingerprint"] != fingerprint:
            fail(409, "Idempotency-Key уже использован для других данных")
        return serialize(ctx, person(ctx, prior.entity_id))
    result = save_person(ctx, data, allow_duplicate=allow_duplicate)
    audit(
        ctx, "request.person.create", UUID(result["id"]), {"key": key, "fingerprint": fingerprint}
    )
    return result


@app.patch(W + "/people/{person_id}")
def update_person(
    person_id: UUID,
    data: PersonPatch,
    allow_duplicate: bool = False,
    ctx: Context = Depends(context),
):
    write(ctx)
    return save_person(ctx, data, person_id, data.expected_version, allow_duplicate)


@app.get(W + "/tags")
def tags(ctx: Context = Depends(context)):
    return [
        {"id": str(t.id), "name": t.name}
        for t in ctx.db.scalars(
            select(Tag).where(Tag.workspace_id == ctx.workspace_id).order_by(Tag.name)
        )
    ]


@app.get(W + "/organizations")
def organizations(ctx: Context = Depends(context)):
    return [
        {"id": str(o.id), "name": o.name}
        for o in ctx.db.scalars(
            select(Organization)
            .where(Organization.workspace_id == ctx.workspace_id)
            .order_by(Organization.name)
        )
    ]


@app.get(W + "/relationships")
def relationships(person_id: UUID, ctx: Context = Depends(context)):
    person(ctx, person_id)
    return [
        relationship_json(r)
        for r in ctx.db.scalars(
            select(Relationship)
            .where(
                Relationship.workspace_id == ctx.workspace_id,
                or_(
                    Relationship.from_person_id == person_id, Relationship.to_person_id == person_id
                ),
            )
            .limit(200)
        )
    ]


@app.post(W + "/relationships", status_code=201)
def create_relationship(data: RelationshipIn, ctx: Context = Depends(context)):
    write(ctx)
    return save_relationship(ctx, data)


@app.delete(W + "/relationships/{relationship_id}")
def delete_relationship(relationship_id: UUID, ctx: Context = Depends(context)):
    write(ctx)
    r = ctx.db.scalar(
        select(Relationship).where(
            Relationship.id == relationship_id, Relationship.workspace_id == ctx.workspace_id
        )
    )
    if not r:
        fail()
    ctx.db.delete(r)
    audit(ctx, "relationship.deleted", r.id)
    return {"ok": True}


@app.get(W + "/graph")
def graph(
    root: UUID,
    depth: int = Query(1, ge=1, le=2),
    limit: int = Query(80, ge=1, le=150),
    target: UUID | None = None,
    ctx: Context = Depends(context),
):
    person(ctx, root)
    if target:
        person(ctx, target)
    visited = {root}
    frontier = {root}
    edges = {}
    parents = {}
    truncated = False
    for _ in range(6 if target else depth):
        if not frontier:
            break
        rows = ctx.db.scalars(
            select(Relationship)
            .where(
                Relationship.workspace_id == ctx.workspace_id,
                or_(
                    Relationship.from_person_id.in_(frontier),
                    Relationship.to_person_id.in_(frontier),
                ),
            )
            .order_by(Relationship.id)
            .limit(1001)
        ).all()
        if len(rows) > 1000:
            truncated = True
            rows = rows[:1000]
        next_frontier = set()
        for r in rows:
            a, b = r.from_person_id, r.to_person_id
            # Directed edges are traversed only forwards; symmetric edges both ways.
            steps = []
            if a in frontier:
                steps.append((a, b))
            if b in frontier and not r.directed:
                steps.append((b, a))
            for src, dst in steps:
                if dst not in visited:
                    if len(visited) >= limit:
                        truncated = True
                        continue
                    visited.add(dst)
                    next_frontier.add(dst)
                    parents[dst] = src
                if a in visited and b in visited:
                    edges[r.id] = r
        frontier = next_frontier
        if target in visited:
            break
    path = []
    if target and target in visited:
        cur = target
        path = [str(cur)]
        while cur != root:
            cur = parents[cur]
            path.append(str(cur))
        path.reverse()
    nodes = serialize_many(
        ctx,
        list(
            ctx.db.scalars(
                select(Person).where(
                    Person.workspace_id == ctx.workspace_id, Person.id.in_(visited)
                )
            )
        ),
    )
    return {
        "nodes": nodes,
        "edges": [relationship_json(r) for r in edges.values()],
        "path": path,
        "truncated": truncated,
        "max_depth": 6 if target else depth,
    }


@app.post(W + "/sources", status_code=201)
def source(data: SourceIn, ctx: Context = Depends(context)):
    write(ctx)
    locked_key(ctx, "source:" + digest(data.model_dump_json()))
    existing = ctx.db.scalar(
        select(Source).where(
            Source.workspace_id == ctx.workspace_id,
            Source.name == data.name,
            Source.reference == data.reference,
        )
    )
    if existing:
        return {"id": str(existing.id), "name": existing.name, "reference": existing.reference}
    s = Source(workspace_id=ctx.workspace_id, **data.model_dump())
    ctx.db.add(s)
    ctx.db.flush()
    audit(ctx, "source.created", s.id)
    return {"id": str(s.id), "name": s.name, "reference": s.reference}


@app.get(W + "/sources")
def sources(ctx: Context = Depends(context)):
    return [
        {"id": str(s.id), "name": s.name, "reference": s.reference}
        for s in ctx.db.scalars(
            select(Source).where(Source.workspace_id == ctx.workspace_id).limit(100)
        )
    ]


@app.post(W + "/suggestions", status_code=201)
def suggest(data: SuggestionIn, ctx: Context = Depends(context)):
    write(ctx)
    schema = RelationshipIn if data.operation == "create_relationship" else PersonIn
    data.payload = schema.model_validate(data.payload).model_dump(mode="json")
    locked_key(ctx, "suggestion:" + data.job_key + ":" + data.record_key)
    existing = ctx.db.scalar(
        select(Suggestion).where(
            Suggestion.workspace_id == ctx.workspace_id,
            Suggestion.job_key == data.job_key,
            Suggestion.record_key == data.record_key,
        )
    )
    if existing:
        same = (
            existing.payload == data.payload
            and existing.operation == data.operation
            and existing.target_id == data.target_id
            and existing.source_id == data.source_id
            and existing.expected_version == data.expected_version
            and existing.confidence == data.confidence
        )
        if not same:
            fail(409, "Исходная запись уже импортирована с другим содержимым")
        return {"id": str(existing.id), "status": existing.status}
    if not ctx.db.scalar(
        select(Source).where(Source.workspace_id == ctx.workspace_id, Source.id == data.source_id)
    ):
        fail()
    before = {}
    if data.operation == "update_person":
        if not data.target_id or data.expected_version is None:
            fail(422, "Нужны target_id и expected_version")
        p = person(ctx, data.target_id)
        if p.version != data.expected_version:
            fail(409, "Версия карточки изменилась")
        before = serialize(ctx, p)
        for key in ("id", "version", "updated_at", "workspace_id"):
            before.pop(key, None)
        before["contacts"] = [
            {k: v for k, v in c.items() if k != "normalized_value"} for c in before["contacts"]
        ]
        PersonIn.model_validate(data.payload)
    elif data.operation == "create_person":
        if data.target_id or data.expected_version is not None:
            fail(422, "Создание не должно иметь target_id/version")
        PersonIn.model_validate(data.payload)
    else:
        rel = RelationshipIn.model_validate(data.payload)
        person(ctx, rel.from_person_id)
        person(ctx, rel.to_person_id)
        if data.target_id or data.expected_version is not None:
            fail(422, "Для связи не нужны target_id/version")
    s = Suggestion(
        workspace_id=ctx.workspace_id, created_by=ctx.user.id, before=before, **data.model_dump()
    )
    ctx.db.add(s)
    ctx.db.flush()
    audit(ctx, "suggestion.created", s.id)
    return {"id": str(s.id), "status": s.status}


@app.get(W + "/suggestions")
def suggestions(
    ctx: Context = Depends(context), page: int = Query(1, ge=1), status: str = "pending"
):
    rows = ctx.db.scalars(
        select(Suggestion)
        .where(Suggestion.workspace_id == ctx.workspace_id, Suggestion.status == status)
        .order_by(Suggestion.created_at.desc())
        .offset((page - 1) * 25)
        .limit(25)
    )
    return [
        {
            **{
                k: getattr(s, k)
                for k in (
                    "operation",
                    "payload",
                    "before",
                    "confidence",
                    "status",
                    "expected_version",
                )
            },
            "id": str(s.id),
            "target_id": str(s.target_id) if s.target_id else None,
            "source_id": str(s.source_id),
        }
        for s in rows
    ]


@app.post(W + "/suggestions/{suggestion_id}/{decision}")
def review_suggestion(
    suggestion_id: UUID,
    decision: str,
    allow_duplicate: bool = False,
    ctx: Context = Depends(context),
):
    write(ctx)
    if ctx.agent:
        fail(403, "Требуется подтверждение человеком")
    if decision not in ("approve", "reject"):
        fail()
    s = ctx.db.scalar(
        select(Suggestion)
        .where(Suggestion.workspace_id == ctx.workspace_id, Suggestion.id == suggestion_id)
        .with_for_update()
    )
    if not s:
        fail()
    if s.status != "pending":
        if (s.status == "applied" and decision == "approve") or (
            s.status == "rejected" and decision == "reject"
        ):
            return {"status": s.status}
        fail(409, "Предложение уже рассмотрено")
    s.reviewed_by = ctx.user.id
    s.reviewed_at = now()
    if decision == "reject":
        s.status = "rejected"
    else:
        s.status = "approved"
        audit(ctx, "suggestion.approved", s.id)
        if s.operation == "create_relationship":
            save_relationship(ctx, RelationshipIn.model_validate(s.payload))
        else:
            save_person(
                ctx,
                PersonIn.model_validate(s.payload),
                s.target_id,
                s.expected_version,
                allow_duplicate,
            )
        s.status = "applied"
    audit(ctx, "suggestion." + s.status, s.id)
    return {"status": s.status}


@app.post(W + "/agent-tokens", status_code=201)
def agent_token(data: AgentIn, ctx: Context = Depends(context)):
    write(ctx)
    raw = secrets.token_urlsafe(40)
    t = AgentToken(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.id,
        token_hash=digest(raw),
        name=data.name,
        expires_at=now() + timedelta(days=data.days),
    )
    ctx.db.add(t)
    ctx.db.flush()
    audit(ctx, "agent_token.created", t.id)
    return {"id": str(t.id), "token": raw, "expires_at": t.expires_at.isoformat()}


@app.get(W + "/agent-tokens")
def agent_tokens(ctx: Context = Depends(context)):
    write(ctx)
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "revoked": t.revoked,
            "expires_at": t.expires_at.isoformat(),
        }
        for t in ctx.db.scalars(
            select(AgentToken).where(
                AgentToken.workspace_id == ctx.workspace_id, AgentToken.user_id == ctx.user.id
            )
        )
    ]


@app.delete(W + "/agent-tokens/{token_id}")
def revoke(token_id: UUID, ctx: Context = Depends(context)):
    write(ctx)
    t = ctx.db.scalar(
        select(AgentToken).where(
            AgentToken.workspace_id == ctx.workspace_id,
            AgentToken.id == token_id,
            AgentToken.user_id == ctx.user.id,
        )
    )
    if not t:
        fail()
    t.revoked = True
    audit(ctx, "agent_token.revoked", t.id)
    return {"ok": True}


@app.get(W + "/audit")
def audits(ctx: Context = Depends(context), page: int = Query(1, ge=1)):
    write(ctx, True)
    return [
        {
            "id": str(a.id),
            "action": a.action,
            "entity_id": str(a.entity_id) if a.entity_id else None,
            "actor_id": str(a.actor_id),
            "created_at": a.created_at.isoformat(),
        }
        for a in ctx.db.scalars(
            select(Audit)
            .where(Audit.workspace_id == ctx.workspace_id)
            .order_by(Audit.created_at.desc())
            .offset((page - 1) * 50)
            .limit(50)
        )
    ]


@app.post(PREFIX + "/auth/revoke-all")
def revoke_sessions(
    response: Response,
    who: Principal = Depends(principal),
    db: Session = Depends(get_db, scope="function"),
):
    db.execute(delete(SessionToken).where(SessionToken.user_id == who.user.id))
    response.delete_cookie(COOKIE, path="/", secure=SECURE, httponly=True, samesite="strict")
    response.delete_cookie("crm_csrf", path="/", secure=SECURE, samesite="strict")
    return {"ok": True}


@app.post(PREFIX + "/auth/password")
def change_password(
    data: PasswordChange,
    request: Request,
    response: Response,
    who: Principal = Depends(principal),
    db: Session = Depends(get_db, scope="function"),
):
    limit_login(request, who.user.email)
    if not verify(data.current_password, who.user.password_hash):
        fail(401, "Неверный текущий пароль")
    locked = db.scalar(select(User).where(User.id == who.user.id).with_for_update())
    # Recheck after lock to prevent two concurrent password changes from racing.
    db.refresh(locked)
    if not verify(data.current_password, locked.password_hash):
        fail(409, "Пароль уже изменён")
    locked.password_hash = hasher.hash(data.new_password)
    db.execute(delete(SessionToken).where(SessionToken.user_id == who.user.id))
    response.delete_cookie(COOKIE, path="/", secure=SECURE, httponly=True, samesite="strict")
    response.delete_cookie("crm_csrf", path="/", secure=SECURE, samesite="strict")
    return {"ok": True}
