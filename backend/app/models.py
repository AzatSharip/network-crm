import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now():
    return datetime.now(UTC)


class Identity:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class User(Identity, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Workspace(Identity, Base):
    __tablename__ = "workspaces"
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (
        CheckConstraint("kind IN ('personal','family')"),
        Index(
            "one_personal_per_user",
            "owner_id",
            unique=True,
            postgresql_where=text("kind='personal'"),
        ),
    )


class Member(Base):
    __tablename__ = "workspace_members"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(12))
    __table_args__ = (CheckConstraint("role IN ('admin','editor','viewer')"),)


class SessionToken(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Invitation(Identity, Base):
    __tablename__ = "invitations"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    email: Mapped[str] = mapped_column(String(254))
    role: Mapped[str] = mapped_column(String(12))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("role IN ('editor','viewer','admin')"),)


class Scoped(Identity):
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)


class Person(Scoped, Base):
    __tablename__ = "persons"
    display_name: Mapped[str] = mapped_column(String(200))
    first_name: Mapped[str] = mapped_column(String(100), default="")
    last_name: Mapped[str] = mapped_column(String(100), default="")
    middle_name: Mapped[str] = mapped_column(String(100), default="")
    aliases: Mapped[list] = mapped_column(JSONB, default=list)
    city: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    profession: Mapped[str] = mapped_column(String(200), default="")
    competencies: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    search_text: Mapped[str] = mapped_column(Text, default="")
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('russian', display_name), 'A') || setweight(to_tsvector('russian', search_text), 'B') || setweight(to_tsvector('simple', search_text), 'C')",
            persisted=True,
        ),
    )
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        Index("ix_person_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_person_search_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
    )


class Contact(Scoped, Base):
    __tablename__ = "person_contacts"
    person_id: Mapped[uuid.UUID] = mapped_column(UUID)
    platform: Mapped[str] = mapped_column(String(50))
    kind: Mapped[str] = mapped_column(String(20))
    value: Mapped[str] = mapped_column(String(1000))
    normalized_value: Mapped[str] = mapped_column(String(1000), index=True)
    label: Mapped[str] = mapped_column(String(100), default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(500), default="")
    verification: Mapped[str] = mapped_column(String(16), default="unverified")
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "person_id"],
            ["persons.workspace_id", "persons.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("person_id", "platform", "kind", "normalized_value"),
    )


class Connection(Base):
    __tablename__ = "person_connections"
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    person_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    knows: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[str | None] = mapped_column(String(1))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "person_id"],
            ["persons.workspace_id", "persons.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "user_id"],
            ["workspace_members.workspace_id", "workspace_members.user_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("priority IS NULL OR priority IN ('A','B','C')"),
        Index(
            "one_primary_connection", "person_id", unique=True, postgresql_where=text("is_primary")
        ),
    )


class Tag(Scoped, Base):
    __tablename__ = "tags"
    name: Mapped[str] = mapped_column(String(80))
    __table_args__ = (
        UniqueConstraint("workspace_id", "name"),
        UniqueConstraint("workspace_id", "id"),
    )


class PersonTag(Base):
    __tablename__ = "person_tags"
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    person_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "person_id"],
            ["persons.workspace_id", "persons.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["workspace_id", "tag_id"], ["tags.workspace_id", "tags.id"]),
    )


class Organization(Scoped, Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        UniqueConstraint("workspace_id", "name"),
        UniqueConstraint("workspace_id", "id"),
    )


class PersonOrganization(Base):
    __tablename__ = "person_organizations"
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    person_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "person_id"],
            ["persons.workspace_id", "persons.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "organization_id"], ["organizations.workspace_id", "organizations.id"]
        ),
    )


class Relationship(Scoped, Base):
    __tablename__ = "relationships"
    from_person_id: Mapped[uuid.UUID] = mapped_column(UUID)
    to_person_id: Mapped[uuid.UUID] = mapped_column(UUID)
    type: Mapped[str] = mapped_column(String(80))
    directed: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "from_person_id"],
            ["persons.workspace_id", "persons.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "to_person_id"],
            ["persons.workspace_id", "persons.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("from_person_id <> to_person_id"),
        UniqueConstraint("workspace_id", "from_person_id", "to_person_id", "type", "directed"),
    )


class Source(Scoped, Base):
    __tablename__ = "sources"
    name: Mapped[str] = mapped_column(String(200))
    reference: Mapped[str] = mapped_column(String(1000), default="")
    __table_args__ = (UniqueConstraint("workspace_id", "id"),)


class Suggestion(Scoped, Base):
    __tablename__ = "ai_suggestions"
    operation: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID)
    expected_version: Mapped[int | None] = mapped_column(Integer)
    before: Mapped[dict] = mapped_column(JSONB, default=dict)
    payload: Mapped[dict] = mapped_column(JSONB)
    confidence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="pending")
    job_key: Mapped[str] = mapped_column(String(100))
    record_key: Mapped[str] = mapped_column(String(100))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "source_id"], ["sources.workspace_id", "sources.id"]),
        ForeignKeyConstraint(["workspace_id", "target_id"], ["persons.workspace_id", "persons.id"]),
        UniqueConstraint("workspace_id", "job_key", "record_key"),
        CheckConstraint("status IN ('pending','approved','rejected','applied')"),
        CheckConstraint("confidence BETWEEN 0 AND 100"),
    )


class AgentToken(Scoped, Base):
    __tablename__ = "agent_tokens"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "user_id"],
            ["workspace_members.workspace_id", "workspace_members.user_id"],
            ondelete="CASCADE",
        ),
    )


class Audit(Scoped, Base):
    __tablename__ = "audit_log"
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
