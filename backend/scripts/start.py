import os
import subprocess

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.security import hash_password
from app.models import User, UserRole
from app.repositories import user_repo


def migrate() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)  # noqa: S603, S607


def ensure_admin() -> None:
    settings = get_settings()
    email = (settings.bootstrap_admin_email or "").strip().lower()
    password = settings.bootstrap_admin_password or ""
    if not email or not password:
        return
    with Session(get_engine()) as session:
        if user_repo.get_by_email(session, email) is None:
            session.add(
                User(
                    name="Administrador",
                    email=email,
                    hashed_password=hash_password(password),
                    role=UserRole.ADMIN,
                    must_change_password=True,
                )
            )
            session.commit()


def main() -> None:
    migrate()
    ensure_admin()
    port = os.environ.get("PORT", "8000")
    os.execvp(
        "uvicorn",
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", port],
    )


if __name__ == "__main__":
    main()
