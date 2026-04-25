from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import Auth


@runtime_checkable
class TokenStorage(Protocol):
    """Pluggable persistence for cached :class:`Auth` tokens.

    The SDK is storage-agnostic: the Home Assistant integration plugs in a
    ``Store``-backed implementation, while standalone scripts can pass ``None``
    (in-memory only) or a small file/Redis adapter.
    """

    async def load(self) -> Auth | None: ...

    async def save(self, auth: Auth) -> None: ...

    async def clear(self) -> None: ...


class InMemoryTokenStorage:
    """Default storage — process-local, lost on restart."""

    def __init__(self) -> None:
        self._auth: Auth | None = None

    async def load(self) -> Auth | None:
        return self._auth

    async def save(self, auth: Auth) -> None:
        self._auth = auth

    async def clear(self) -> None:
        self._auth = None
