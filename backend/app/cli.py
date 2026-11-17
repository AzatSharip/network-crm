import argparse
import getpass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .db import engine
from .models import Member, User, Workspace
from .security import hasher


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["bootstrap"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    from email_validator import validate_email

    email = validate_email(args.email, check_deliverability=False).normalized.lower()
    password = getpass.getpass("Новый пароль (минимум 12 символов): ")
    if len(password) < 12 or len(password) > 256:
        raise SystemExit("Пароль: 12–256 символов")
    if password != getpass.getpass("Повторите пароль: "):
        raise SystemExit("Пароли не совпадают")
    with Session(engine) as db:
        db.execute(text("SELECT pg_advisory_xact_lock(975301)"))
        if db.scalar(select(User.id).limit(1)):
            raise SystemExit("Bootstrap закрыт: пользователь уже существует")
        u = User(email=email, name=args.name, password_hash=hasher.hash(password))
        db.add(u)
        db.flush()
        for kind, name in [("personal", "Личное"), ("family", "Семья")]:
            w = Workspace(kind=kind, name=name, owner_id=u.id)
            db.add(w)
            db.flush()
            db.add(Member(workspace_id=w.id, user_id=u.id, role="admin"))
        db.commit()
    print("Пользователь и два пространства созданы.")


if __name__ == "__main__":
    main()
