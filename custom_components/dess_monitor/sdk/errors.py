from __future__ import annotations


class DessmonitorError(Exception):
    """Base class for all SDK errors."""

    def __init__(self, message: str, *, code: int | None = None, action: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.action = action

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, action={self.action!r}, message={str(self)!r})"


class TransportError(DessmonitorError):
    """Network-level failure (timeout, connection reset, non-JSON body)."""


class ApiError(DessmonitorError):
    """API responded with a non-zero ``err`` envelope code."""


class AuthError(ApiError):
    """API ``err == 10`` — token rejected. Caller should re-authenticate."""


class RateLimitError(ApiError):
    """API rate-limit codes (observed: 3, 9)."""


_RATE_LIMIT_CODES = frozenset({3, 9})


def from_envelope(code: int, desc: str, action: str | None) -> ApiError:
    """Map an envelope ``err`` value to the most specific exception class."""
    message = f"{desc} (err={code}, action={action})"
    if code == 10:
        return AuthError(message, code=code, action=action)
    if code in _RATE_LIMIT_CODES:
        return RateLimitError(message, code=code, action=action)
    return ApiError(message, code=code, action=action)
