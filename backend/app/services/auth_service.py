"""Administrator accounts: creating them, logging in and recognising a token."""

from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    MAX_PASSWORD_BYTES,
    create_access_token,
    hash_password,
    read_access_token,
    verify_password,
)
from app.models import AdminUser
from app.repositories.admin_repository import AdminRepository

MIN_PASSWORD_LENGTH = 8


@lru_cache
def _unused_hash() -> str:
    """Checked when the username does not exist, so a miss takes as long as a wrong password."""
    return hash_password("unused-password")


class AuthService:
    def __init__(self, db: Session, admins: AdminRepository, settings: Settings) -> None:
        self._db = db
        self._admins = admins
        self._settings = settings

    def create_admin(self, username: str, password: str) -> AdminUser:
        if not username:
            raise ValueError("Username is required.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if len(password.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
        if self._admins.get_by_username(username):
            raise ValueError(f"Admin '{username}' already exists.")
        admin = AdminUser(username=username, password_hash=hash_password(password))
        self._admins.add(admin)
        self._db.commit()
        return admin

    def login(self, username: str, password: str) -> str:
        admin = self._admins.get_by_username(username)
        password_hash = admin.password_hash if admin else _unused_hash()
        if not verify_password(password, password_hash) or admin is None:
            raise AuthenticationError("Incorrect username or password.")
        return create_access_token(
            str(admin.id), self._settings.secret_key, self._settings.access_token_expire_minutes
        )

    def admin_from_token(self, token: str) -> AdminUser:
        subject = read_access_token(token, self._settings.secret_key)
        admin = self._admins.get(int(subject)) if subject.isdigit() else None
        if admin is None:
            raise AuthenticationError("Invalid or expired token.")
        return admin
