import httpx
import pytest

from tests.conftest import IsolatedSettings


def test_settings_in_tests_ignore_the_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "a-key-from-the-environment")
    monkeypatch.setenv("TRIAGE_TIMEOUT_SECONDS", "999")
    isolated = IsolatedSettings(secret_key="x" * 32)
    assert isolated.gemini_api_key is None
    assert isolated.triage_timeout_seconds == 20


def test_real_network_calls_are_blocked_during_tests():
    with pytest.raises(AssertionError, match="must not use the network"):
        httpx.Client().get("https://example.com")
