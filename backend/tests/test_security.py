import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    hash_password,
    read_access_token,
    verify_password,
)

SECRET = "unit-test-secret-0123456789-abcdefghij"


def test_password_round_trip():
    hashed = hash_password("a-good-password")
    assert verify_password("a-good-password", hashed)
    assert not verify_password("another-password", hashed)


def test_over_long_password_is_rejected_not_crashing():
    assert not verify_password("x" * 100, hash_password("short-password"))


def test_token_round_trip():
    token = create_access_token("7", SECRET, expires_minutes=5)
    assert read_access_token(token, SECRET) == "7"


def test_expired_token_is_rejected():
    token = create_access_token("7", SECRET, expires_minutes=-1)
    with pytest.raises(AuthenticationError):
        read_access_token(token, SECRET)


def test_token_signed_with_another_key_is_rejected():
    token = create_access_token("7", "some-other-secret-0123456789-abcdefghij", expires_minutes=5)
    with pytest.raises(AuthenticationError):
        read_access_token(token, SECRET)
