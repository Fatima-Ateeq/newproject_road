"""Cheap protection for the public submit endpoint: a rate limit per IP address and a honeypot."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitExceededError
from app.core.rate_limiter import SlidingWindowRateLimiter

_ONE_HOUR = 3600


@lru_cache
def get_submission_limiter() -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(get_settings().submissions_per_hour, _ONE_HOUR)


def limit_submissions(
    request: Request,
    limiter: Annotated[SlidingWindowRateLimiter, Depends(get_submission_limiter)],
) -> None:
    """Reject the request with 429 when this IP address has submitted too often."""
    client_ip = request.client.host if request.client else "unknown"
    retry_after = limiter.try_acquire(client_ip)
    if retry_after is not None:
        raise RateLimitExceededError(
            "Too many complaints from this address. Please try again later.", retry_after
        )
