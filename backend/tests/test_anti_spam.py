from app.api.anti_spam import get_submission_limiter
from app.core.rate_limiter import SlidingWindowRateLimiter


def test_eleventh_submission_in_an_hour_is_blocked(client, submit):
    limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=3600)
    client.app.dependency_overrides[get_submission_limiter] = lambda: limiter

    assert all(submit().status_code == 201 for _ in range(10))
    blocked = submit()
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert "Too many" in blocked.json()["detail"]


def test_rate_limit_does_not_affect_tracking(client, submit):
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=3600)
    client.app.dependency_overrides[get_submission_limiter] = lambda: limiter

    code = submit().json()["complaint_id"]
    submit()  # blocked
    assert client.get(f"/api/complaints/{code}").status_code == 200


def test_honeypot_submission_is_ignored_but_looks_successful(client, submit, admin_headers):
    response = submit(website="http://spam.example")
    assert response.status_code == 201

    fake_code = response.json()["complaint_id"]
    assert client.get(f"/api/complaints/{fake_code}").status_code == 404
    assert client.get("/api/admin/complaints", headers=admin_headers).json()["total"] == 0


def test_empty_honeypot_is_a_normal_submission(client, submit, admin_headers):
    assert submit(website="").status_code == 201
    assert client.get("/api/admin/complaints", headers=admin_headers).json()["total"] == 1
