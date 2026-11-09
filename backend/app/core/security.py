"""Password hashing and access tokens. Nothing here knows about the database or HTTP."""

from datetime import timedelta

import bcrypt
import jwt

from app.core.clock import utc_now
from app.core.exceptions import AuthenticationError

_ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72  # bcrypt ignores or rejects anything longer


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(subject: str, secret_key: str, expires_minutes: int) -> str:
    payload = {"sub": subject, "exp": utc_now() + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, secret_key, algorithm=_ALGORITHM)


def read_access_token(token: str, secret_key: str) -> str:
    """Return the token's subject, or raise AuthenticationError if it is invalid or expired."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as error:
        raise AuthenticationError("Invalid or expired token.") from error
    return str(payload["sub"])
