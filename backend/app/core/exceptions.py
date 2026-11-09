"""Domain errors raised by services. The API layer maps them to HTTP responses."""


class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    @property
    def headers(self) -> dict[str, str]:
        """Extra HTTP headers the response should carry. None by default."""
        return {}


class NotFoundError(DomainError):
    pass


class InvalidPhotoError(DomainError):
    pass


class AuthenticationError(DomainError):
    @property
    def headers(self) -> dict[str, str]:
        return {"WWW-Authenticate": "Bearer"}


class RateLimitExceededError(DomainError):
    def __init__(self, message: str, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds

    @property
    def headers(self) -> dict[str, str]:
        return {"Retry-After": str(self.retry_after_seconds)}
