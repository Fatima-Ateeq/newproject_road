"""Create an administrator account:  python -m app.cli.create_admin"""

import sys
from getpass import getpass

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.repositories.admin_repository import AdminRepository
from app.services.auth_service import AuthService


def main() -> int:
    username = input("Admin username: ").strip()
    password = getpass("Password: ")
    if password != getpass("Repeat password: "):
        print("Passwords do not match.")
        return 1

    with get_session_factory()() as db:
        try:
            AuthService(db, AdminRepository(db), get_settings()).create_admin(username, password)
        except ValueError as error:
            print(error)
            return 1
    print(f"Admin '{username}' created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
