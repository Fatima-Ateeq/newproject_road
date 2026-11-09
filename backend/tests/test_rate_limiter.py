from app.core.rate_limiter import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_requests_up_to_the_limit_then_blocks():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60, clock=FakeClock())
    assert limiter.try_acquire("a") is None
    assert limiter.try_acquire("a") is None
    assert limiter.try_acquire("a") is not None


def test_blocked_request_reports_how_long_to_wait():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60, clock=clock)
    limiter.try_acquire("a")
    clock.now = 20
    assert limiter.try_acquire("a") == 40


def test_requests_are_allowed_again_after_the_window_passes():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60, clock=clock)
    limiter.try_acquire("a")
    clock.now = 61
    assert limiter.try_acquire("a") is None


def test_each_key_has_its_own_allowance():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60, clock=FakeClock())
    assert limiter.try_acquire("a") is None
    assert limiter.try_acquire("b") is None
