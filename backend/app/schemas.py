import re
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Strict):
    email: EmailStr
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=1, max_length=256
    )


class InviteAccept(Strict):
    token: str = Field(min_length=20, max_length=200)
    name: str = Field(min_length=1, max_length=120)
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=12, max_length=256
    )


class WorkspaceIn(Strict):
    name: str = Field(min_length=1, max_length=120)


class InviteIn(Strict):
    email: EmailStr
    role: Literal["admin", "editor", "viewer"] = "editor"


class ContactIn(Strict):
    platform: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    kind: Literal["phone", "email", "username", "numeric_id", "url", "other"]
    value: str = Field(min_length=1, max_length=1000)
    label: str = Field(default="", max_length=100)
    is_primary: bool = False
    source: str = Field(default="", max_length=500)
    verification: Literal["unverified", "verified"] = "unverified"

    @model_validator(mode="after")
    def valid_value(self):
        if self.kind == "url":
            url = urlsplit(self.value)
            if (
                url.scheme not in ("http", "https")
                or not url.hostname
                or url.username
                or url.password
                or any(ord(c) < 33 for c in self.value)
            ):
                raise ValueError("Допустима только http(s)-ссылка без учётных данных")
        if self.kind == "numeric_id" and not re.fullmatch(r"[0-9]{1,30}", self.value):
            raise ValueError("Числовой ID должен содержать только цифры")
        if self.kind == "phone" and not 7 <= len(re.sub(r"\D", "", self.value)) <= 15:
            raise ValueError("Телефон должен содержать 7–15 цифр")
        if self.kind == "email":
            from email_validator import validate_email

            validate_email(self.value, check_deliverability=False)
        if self.kind == "username" and not re.fullmatch(r"@?[\w.\-]{1,100}", self.value):
            raise ValueError("Некорректный username")
        return self


class OrgIn(Strict):
    name: str = Field(min_length=1, max_length=200)
    title: str = Field(default="", max_length=200)


class ConnectionIn(Strict):
    user_id: UUID
    knows: bool = True
    priority: Literal["A", "B", "C"] | None = None
    is_primary: bool = False


class PersonIn(Strict):
    display_name: str = Field(min_length=1, max_length=200)
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)
    middle_name: str = Field(default="", max_length=100)
    aliases: list[str] = Field(default_factory=list, max_length=30)
    city: str = Field(default="", max_length=120)
    country: str = Field(default="", max_length=120)
    profession: str = Field(default="", max_length=200)
    competencies: str = Field(default="", max_length=2000)
    description: str = Field(default="", max_length=3000)
    notes: str = Field(default="", max_length=20000)
    contacts: list[ContactIn] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, max_length=50)
    organizations: list[OrgIn] = Field(default_factory=list, max_length=30)
    connections: list[ConnectionIn] = Field(default_factory=list, max_length=50)

    @field_validator("tags", "aliases")
    @classmethod
    def strings(cls, values):
        if any(not v.strip() or len(v) > 80 for v in values):
            raise ValueError("Значения должны содержать 1–80 символов")
        return list(dict.fromkeys(v.strip() for v in values))

    @model_validator(mode="after")
    def connections_valid(self):
        if (
            len({c.user_id for c in self.connections}) != len(self.connections)
            or sum(c.is_primary for c in self.connections) > 1
        ):
            raise ValueError("Повтор участника или несколько основных знакомых")
        if len({o.name.casefold() for o in self.organizations}) != len(self.organizations):
            raise ValueError("Повтор организации")
        return self


class PersonPatch(PersonIn):
    expected_version: int = Field(ge=1)


class RelationshipIn(Strict):
    from_person_id: UUID
    to_person_id: UUID
    type: str = Field(min_length=1, max_length=80)
    directed: bool = False
    comment: str = Field(default="", max_length=3000)
    source: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def distinct(self):
        if self.from_person_id == self.to_person_id:
            raise ValueError("Связь человека с самим собой запрещена")
        return self


class SourceIn(Strict):
    name: str = Field(min_length=1, max_length=200)
    reference: str = Field(default="", max_length=1000)


class SuggestionIn(Strict):
    operation: Literal["create_person", "update_person", "create_relationship"]
    target_id: UUID | None = None
    source_id: UUID
    expected_version: int | None = Field(default=None, ge=1)
    payload: dict
    confidence: int = Field(ge=0, le=100)
    job_key: str = Field(min_length=1, max_length=100)
    record_key: str = Field(min_length=1, max_length=100)


class AgentIn(Strict):
    name: str = Field(min_length=1, max_length=120)
    days: int = Field(default=30, ge=1, le=90)


class PasswordChange(Strict):
    current_password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=1, max_length=256
    )
    new_password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=12, max_length=256
    )
