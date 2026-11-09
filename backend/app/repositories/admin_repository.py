from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AdminUser


class AdminRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, admin: AdminUser) -> None:
        self._db.add(admin)
        self._db.flush()

    def get(self, admin_id: int) -> AdminUser | None:
        return self._db.get(AdminUser, admin_id)

    def get_by_username(self, username: str) -> AdminUser | None:
        return self._db.scalars(select(AdminUser).where(AdminUser.username == username)).first()
