import json
import re
import uuid

from sqlalchemy import delete, select, text

from .models import (
    Audit,
    Connection,
    Contact,
    Member,
    Organization,
    Person,
    PersonOrganization,
    PersonTag,
    Relationship,
    Tag,
    now,
)
from .schemas import PersonIn, RelationshipIn
from .security import digest, fail

FIELDS = (
    "display_name",
    "first_name",
    "last_name",
    "middle_name",
    "aliases",
    "city",
    "country",
    "profession",
    "competencies",
    "description",
    "notes",
)


def audit(ctx, action, entity_id=None, detail=None):
    ctx.db.add(
        Audit(
            workspace_id=ctx.workspace_id,
            actor_id=ctx.user.id,
            action=action,
            entity_id=entity_id,
            detail=detail or {},
        )
    )


def locked_key(ctx, key):
    ctx.db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"),
        {"k": str(ctx.workspace_id) + ":" + key},
    )


def normalize(c):
    value = c.value.strip()
    if c.kind == "phone":
        digits = re.sub(r"\D", "", value)
        if len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        return digits
    if c.kind == "username":
        return value.lstrip("@").casefold()
    if c.kind == "email":
        return value.casefold()
    if c.kind == "numeric_id":
        return str(int(value))
    return value


def person(ctx, pid, lock=False):
    query = select(Person).where(Person.id == pid, Person.workspace_id == ctx.workspace_id)
    p = ctx.db.scalar(query.with_for_update() if lock else query)
    if not p:
        fail()
    return p


def serialize(ctx, p):
    return serialize_many(ctx, [p])[0]


def serialize_many(ctx, people):
    if not people:
        return []
    db, wid = ctx.db, ctx.workspace_id
    ids = [p.id for p in people]
    result = {}
    for p in people:
        result[p.id] = {k: getattr(p, k) for k in FIELDS}
        result[p.id].update(
            id=str(p.id),
            version=p.version,
            updated_at=p.updated_at.isoformat(),
            workspace_id=str(wid),
            contacts=[],
            tags=[],
            organizations=[],
            connections=[],
        )
    for c in db.scalars(
        select(Contact)
        .where(Contact.workspace_id == wid, Contact.person_id.in_(ids))
        .order_by(Contact.created_at, Contact.id)
    ):
        result[c.person_id]["contacts"].append(
            {
                k: getattr(c, k)
                for k in (
                    "platform",
                    "kind",
                    "value",
                    "normalized_value",
                    "label",
                    "is_primary",
                    "source",
                    "verification",
                )
            }
        )
    for pid, name in db.execute(
        select(PersonTag.person_id, Tag.name)
        .join(Tag, Tag.id == PersonTag.tag_id)
        .where(PersonTag.workspace_id == wid, PersonTag.person_id.in_(ids))
        .order_by(Tag.name)
    ):
        result[pid]["tags"].append(name)
    for pid, name, title in db.execute(
        select(PersonOrganization.person_id, Organization.name, PersonOrganization.title)
        .join(Organization, Organization.id == PersonOrganization.organization_id)
        .where(PersonOrganization.workspace_id == wid, PersonOrganization.person_id.in_(ids))
    ):
        result[pid]["organizations"].append({"name": name, "title": title})
    for c in db.scalars(
        select(Connection).where(Connection.workspace_id == wid, Connection.person_id.in_(ids))
    ):
        result[c.person_id]["connections"].append(
            {
                "user_id": str(c.user_id),
                "knows": c.knows,
                "priority": c.priority,
                "is_primary": c.is_primary,
            }
        )
    return [result[p.id] for p in people]


def save_person(ctx, data: PersonIn, pid=None, expected_version=None, allow_duplicate=False):
    db, wid = ctx.db, ctx.workspace_id
    locked_key(ctx, "people-write")
    p = person(ctx, pid, True) if pid else None
    if p and p.version != expected_version:
        fail(409, {"code": "version_conflict", "current_version": p.version})
    contacts = []
    seen = set()
    duplicates = {}
    for c in data.contacts:
        norm = normalize(c)
        key = (c.platform, c.kind, norm)
        if key in seen:
            fail(422, "Повтор способа связи")
        seen.add(key)
        if c.kind in ("phone", "email", "numeric_id"):
            match_query = select(Contact).where(
                Contact.workspace_id == wid,
                Contact.kind == c.kind,
                Contact.normalized_value == norm,
            )
            if c.kind == "numeric_id":
                match_query = match_query.where(Contact.platform == c.platform)
            matches = db.scalars(match_query)
            for match in matches:
                if match.person_id != pid:
                    found = person(ctx, match.person_id)
                    duplicates[str(found.id)] = found.display_name
        contacts.append((c, norm))
    if duplicates and not allow_duplicate:
        fail(
            409,
            {
                "code": "duplicates",
                "matches": [{"id": k, "display_name": v} for k, v in duplicates.items()],
            },
        )
    for c in data.connections:
        if not db.get(Member, (wid, c.user_id)):
            fail(422, "Участник не принадлежит пространству")
        if p and c.user_id != ctx.user.id:
            previous = db.get(Connection, (wid, p.id, c.user_id))
            if c.priority != (previous.priority if previous else None):
                fail(403, "Личный приоритет может менять только сам участник")
        elif not p and c.user_id != ctx.user.id and c.priority:
            fail(403, "Личный приоритет может менять только сам участник")
    if p:
        # Preserve other users' priorities if the submitted form omits their acquaintance.
        previous = list(
            db.scalars(
                select(Connection).where(
                    Connection.workspace_id == wid, Connection.person_id == p.id
                )
            )
        )
        provided = {c.user_id for c in data.connections}
        if any(
            c.user_id != ctx.user.id and c.priority and c.user_id not in provided for c in previous
        ):
            fail(403, "Нельзя удалить чужой личный приоритет")
    else:
        p = Person(workspace_id=wid, updated_by=ctx.user.id)
        db.add(p)
    for k in FIELDS:
        setattr(p, k, getattr(data, k))
    if pid:
        p.version += 1
    p.updated_at, p.updated_by = now(), ctx.user.id
    chunks = [str(getattr(data, k)) if k != "aliases" else " ".join(data.aliases) for k in FIELDS]
    chunks.extend(v for c, norm in contacts for v in (c.value, norm, c.label))
    chunks.extend(data.tags)
    chunks.extend(v for o in data.organizations for v in (o.name, o.title))
    p.search_text = " ".join(chunks).casefold()
    db.flush()
    for cls in (Contact, Connection, PersonTag, PersonOrganization):
        db.execute(delete(cls).where(cls.workspace_id == wid, cls.person_id == p.id))
    for c, norm in contacts:
        db.add(Contact(workspace_id=wid, person_id=p.id, normalized_value=norm, **c.model_dump()))
    for c in data.connections:
        db.add(Connection(workspace_id=wid, person_id=p.id, **c.model_dump()))
    for name in data.tags:
        t = db.scalar(select(Tag).where(Tag.workspace_id == wid, Tag.name == name))
        if not t:
            t = Tag(workspace_id=wid, name=name)
            db.add(t)
            db.flush()
        db.add(PersonTag(workspace_id=wid, person_id=p.id, tag_id=t.id))
    for o in data.organizations:
        org = db.scalar(
            select(Organization).where(
                Organization.workspace_id == wid, Organization.name == o.name
            )
        )
        if not org:
            org = Organization(workspace_id=wid, name=o.name)
            db.add(org)
            db.flush()
        db.add(
            PersonOrganization(
                workspace_id=wid, person_id=p.id, organization_id=org.id, title=o.title
            )
        )
    db.flush()
    audit(ctx, "person.updated" if pid else "person.created", p.id, {"version": p.version})
    return serialize(ctx, p)


def save_relationship(ctx, data: RelationshipIn):
    person(ctx, data.from_person_id)
    person(ctx, data.to_person_id)
    values = data.model_dump()
    if not data.directed:
        values["from_person_id"], values["to_person_id"] = sorted(
            (data.from_person_id, data.to_person_id)
        )
    locked_key(ctx, "relationship:" + digest(json.dumps(values, sort_keys=True, default=str)))
    existing = ctx.db.scalar(
        select(Relationship).where(
            Relationship.workspace_id == ctx.workspace_id,
            Relationship.from_person_id == values["from_person_id"],
            Relationship.to_person_id == values["to_person_id"],
            Relationship.type == data.type,
            Relationship.directed == data.directed,
        )
    )
    if existing:
        return relationship_json(existing)
    r = Relationship(workspace_id=ctx.workspace_id, created_by=ctx.user.id, **values)
    ctx.db.add(r)
    ctx.db.flush()
    audit(ctx, "relationship.created", r.id)
    return relationship_json(r)


def relationship_json(r):
    return {
        k: str(getattr(r, k)) if isinstance(getattr(r, k), uuid.UUID) else getattr(r, k)
        for k in ("id", "from_person_id", "to_person_id", "type", "directed", "comment", "source")
    }
